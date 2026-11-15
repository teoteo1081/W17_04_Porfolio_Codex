#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Portfolio Visual Editor Server (/api/save)

Phục vụ trang web và ghi file Final sạch vào thư mục Git khi bấm [Lưu file sạch (Final)].

Bảo vệ endpoint ghi file (F10):
  * Chỉ bind loopback; kiểm tra header Host (chặn DNS rebinding).
  * Không còn CORS "*": trang ngoài origin không đọc được token và không gọi được /api/save.
  * Token phiên ngẫu nhiên (secrets.token_urlsafe) cấp qua GET /api/session cho đúng same-origin
    (Sec-Fetch-Site / Origin / Referer phải khớp dev origin); POST bắt buộc header X-W17-Token.
  * Bắt buộc Content-Type: application/json, giới hạn kích thước body, chỉ ghi allowlist tên file.
  * Kiểm tra cấu trúc HTML trước khi ghi; ghi nguyên tử (tệp tạm + os.replace) và backup bản cũ.
  * Trả đúng trạng thái: 200 chỉ khi mọi target đã ghi; 4xx/5xx kèm lý do nếu không.
"""

import hmac
import json
import os
import secrets
import tempfile
import threading
import time
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE_DIR = Path(os.environ.get("W17_BASE_DIR") or Path(__file__).resolve().parent).resolve()
BACKUP_DIR_NAME = ".w17_backups"
BACKUP_KEEP = 5
MAX_BODY_BYTES = 12 * 1024 * 1024  # file Final ~0.3MB; chừa chỗ cho ảnh đại diện base64

# filename -> {id: thẻ} các phần tử BẮT BUỘC phải tồn tại trong CÂY HTML đã parse (comment/chuỗi trong script không được tính),
# mỗi id đúng một lần; cùng kích thước tối thiểu. Bản ghi quá nhỏ so với file hiện có cũng bị từ chối.
ALLOWED_FILES = {
    "index.html": {
        "main-navbar": "header", "ga4-ecosystem": "section", "pbi-ga4-dashboard": "div", "core-portfolio-script": "script",
        "visual-editor-script": "script", "w17-baked-edits": "script", "ga4-drilldown-modal": "div",
    },
    "index_portfolio_clean.html": {
        "portfolio-root": "main", "reorderable-sections": "div", "interactive-editor-script": "script",
        "w17-baked-edits": "script", "solutions-grid": "div", "education-grid": "div",
    },
}
MIN_SCRIPT_CHARS = 20000   # tổng độ dài các <script> thực thi (không tính JSON nhúng)
MIN_ELEMENTS = 300         # số phần tử thật trong cây HTML
MIN_HTML_BYTES = 100 * 1024
MIN_RATIO_OF_CURRENT = 0.5

# Chỉ phục vụ các loại file tĩnh cần cho trang; không phục vụ mã nguồn server, dữ liệu nhạy cảm, thư mục ẩn
# hay danh sách thư mục. Kiểm tra trên ĐƯỜNG DẪN ĐÃ GIẢI MÃ/CHUẨN HÓA (percent-encoding không vượt được).
SERVED_SUFFIXES = {".html", ".htm", ".json", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".woff", ".woff2", ".txt"}
BLOCKED_PREFIXES = ("service_account", "credentials")

SESSION_TOKEN = secrets.token_urlsafe(32)
WRITE_LOCK = threading.Lock()
MAX_DRAIN_BYTES = 64 * 1024 * 1024  # body lớn hơn mức này: đóng kết nối thay vì đọc bỏ


def allowed_hosts(port):
    return {f"127.0.0.1:{port}", f"localhost:{port}"}


def allowed_origins(port):
    return {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}


class SaveError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class _PageProbe(HTMLParser):
    """Dựng bản tóm tắt cây HTML thật: comment và nội dung trong <script>/<style> không bao giờ được tính là phần tử."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.elements = 0
        self.ids = {}            # id -> [tag, ...]
        self.html_tags = 0
        self.body_tags = 0
        self.editor_attrs = []   # contenteditable / toolbar / is-editing
        self.script_chars = 0
        self.baked_json = []
        self._cur_script = None

    def handle_starttag(self, tag, attrs):
        self.elements += 1
        a = dict(attrs)
        if tag == "html":
            self.html_tags += 1
        if tag == "body":
            self.body_tags += 1
            if "is-editing" in (a.get("class") or "").split():
                self.editor_attrs.append("body.is-editing")
        if "contenteditable" in a:
            self.editor_attrs.append(f"{tag}[contenteditable]")
        if a.get("id"):
            self.ids.setdefault(a["id"], []).append(tag)
            if a["id"] in ("visual-toolbar", "floating-toolbar"):
                self.editor_attrs.append("#" + a["id"])
        if tag == "script":
            self._cur_script = {"id": a.get("id"), "type": (a.get("type") or "").lower(), "chars": 0, "data": []}

    def handle_data(self, data):
        if self._cur_script is not None:
            self._cur_script["chars"] += len(data)
            self._cur_script["data"].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._cur_script is not None:
            s = self._cur_script
            if s["type"] == "application/json":
                self.baked_json.append((s["id"], "".join(s["data"])))
            else:
                self.script_chars += s["chars"]
            self._cur_script = None


def validate_html(filename, html):
    if not isinstance(html, str) or not html.strip():
        raise SaveError(400, "Nội dung HTML rỗng hoặc không phải chuỗi.")
    head = html.lstrip()[:200].lower()
    if not (head.startswith("<!doctype html") or head.startswith("<html")):
        raise SaveError(422, "Nội dung không bắt đầu bằng <!DOCTYPE html> hoặc <html>.")
    if "</html>" not in html[-400:].lower():
        raise SaveError(422, "Nội dung HTML không kết thúc bằng </html> (có thể bị cắt cụt).")
    probe = _PageProbe()
    try:
        probe.feed(html)
        probe.close()
    except Exception:
        raise SaveError(422, "Không parse được HTML.")
    if probe.html_tags != 1 or probe.body_tags != 1:
        raise SaveError(422, "HTML phải có đúng một thẻ <html> và một thẻ <body>.")
    problems = []
    for rid, tag in ALLOWED_FILES[filename].items():
        found = probe.ids.get(rid, [])
        if found != [tag]:
            problems.append(f"{rid} (cần đúng 1 <{tag}>, tìm thấy {found or 'không có'})")
    if problems:
        raise SaveError(422, f"HTML không phải bản đầy đủ của {filename}: " + "; ".join(problems))
    if probe.elements < MIN_ELEMENTS:
        raise SaveError(422, f"HTML chỉ có {probe.elements} phần tử (< {MIN_ELEMENTS}); không phải trang đầy đủ.")
    if probe.script_chars < MIN_SCRIPT_CHARS:
        raise SaveError(422, f"Mã script quá ít ({probe.script_chars} ký tự < {MIN_SCRIPT_CHARS}); không phải trang đầy đủ.")
    for sid, data in probe.baked_json:
        if sid == "w17-baked-edits":
            try:
                parsed = json.loads(data or "null")
            except json.JSONDecodeError:
                raise SaveError(422, "Khối w17-baked-edits không phải JSON hợp lệ.")
            if not isinstance(parsed, dict):
                raise SaveError(422, "Khối w17-baked-edits phải là object JSON.")
    if probe.editor_attrs:
        raise SaveError(422, "Bản Final còn trạng thái editor (" + ", ".join(sorted(set(probe.editor_attrs))) + "); từ chối ghi.")
    size = len(html.encode("utf-8"))
    current = BASE_DIR / filename
    floor = MIN_HTML_BYTES
    if current.exists():
        floor = max(floor, int(current.stat().st_size * MIN_RATIO_OF_CURRENT))
    if size < floor:
        raise SaveError(422, f"HTML quá nhỏ ({size} byte < {floor}); có thể bị cắt cụt hoặc không phải trang đầy đủ.")


def backup_existing(target):
    if not target.exists():
        return None
    backup_dir = BASE_DIR / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{target.name}.{stamp}.bak"
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / f"{target.name}.{stamp}-{counter}.bak"
        counter += 1
    backup_path.write_bytes(target.read_bytes())
    old = sorted(backup_dir.glob(f"{target.name}.*.bak"), key=lambda p: p.stat().st_mtime)
    for stale in old[:-BACKUP_KEEP]:
        try:
            stale.unlink()
        except OSError:
            pass
    return backup_path


def atomic_write(target, text):
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # Trên Windows os.replace có thể tạm thời bị từ chối khi có tiến trình đang đọc file: thử lại ngắn.
        for attempt in range(40):
            try:
                os.replace(tmp_name, target)
                return
            except PermissionError:
                if attempt == 39:
                    raise
                time.sleep(0.025)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def save_with_backup(name, html):
    """Backup + ghi nguyên tử, tuần tự hóa toàn bộ chuỗi để các request đồng thời không giẫm lên nhau."""
    target = BASE_DIR / name
    with WRITE_LOCK:
        backup = backup_existing(target)
        atomic_write(target, html)
    return backup


class PortfolioEditorHandler(SimpleHTTPRequestHandler):
    server_version = "W17Editor/1.0"
    sys_version = ""
    timeout = 20  # chống kết nối treo (slowloris) giữ luồng xử lý

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    # ---- helpers -------------------------------------------------------------
    @property
    def _port(self):
        return self.server.server_address[1]

    def _host_ok(self):
        return (self.headers.get("Host") or "") in allowed_hosts(self._port)

    def _same_origin_ok(self):
        origin = self.headers.get("Origin")
        if origin is not None:
            return origin in allowed_origins(self._port)
        site = self.headers.get("Sec-Fetch-Site")
        if site is not None:
            return site in ("same-origin", "none")
        referer = self.headers.get("Referer")
        if referer:
            parts = urlsplit(referer)
            return f"{parts.scheme}://{parts.netloc}" in allowed_origins(self._port)
        return False

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()

    # ---- static --------------------------------------------------------------
    def _path_blocked(self):
        """Chặn dựa trên đường dẫn thật sau khi giải mã percent-encoding và chuẩn hóa (cùng hàm mà server dùng để mở file)."""
        try:
            raw = urlsplit(self.path).path
            if "\x00" in raw or "\\" in raw:
                return True
            fs_path = Path(self.translate_path(self.path)).resolve()
            rel = fs_path.relative_to(BASE_DIR)
        except (ValueError, OSError):
            return True
        if any(part.startswith(".") for part in rel.parts):
            return True
        if rel.parts and rel.parts[-1].lower().startswith(BLOCKED_PREFIXES):
            return True
        if fs_path.is_dir():
            # không liệt kê thư mục; chỉ cho phép khi có index.html
            return not (fs_path / "index.html").is_file()
        return fs_path.suffix.lower() not in SERVED_SUFFIXES

    def _serve_final_file(self, head_only):
        """Hai file Final đang được ghi đè bởi /api/save: đọc dưới cùng khóa với ghi để không bao giờ thấy trạng thái nửa chừng
        (trên Windows, mở file đúng lúc os.replace có thể lỗi thoáng qua và bị trả 404 giả)."""
        try:
            fs_path = Path(self.translate_path(self.path)).resolve()
            name = fs_path.relative_to(BASE_DIR).as_posix()
        except (ValueError, OSError):
            return False
        if name not in ALLOWED_FILES:
            return False
        try:
            with WRITE_LOCK:
                data = fs_path.read_bytes()
        except OSError:
            self._send_json(503, {"status": "error", "message": "File đang được ghi, thử lại."})
            return True
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not head_only:
            self.wfile.write(data)
        return True

    def do_GET(self):
        if not self._host_ok():
            self._send_json(403, {"status": "error", "message": "Host không được phép."})
            return
        path = urlsplit(self.path).path
        if path == "/api/session":
            if not self._same_origin_ok():
                self._send_json(403, {"status": "error", "message": "Chỉ trang cùng origin mới lấy được token."})
                return
            self._send_json(200, {"status": "ok", "token": SESSION_TOKEN, "files": sorted(ALLOWED_FILES)})
            return
        if self._path_blocked():
            self._send_json(404, {"status": "error", "message": "Không tìm thấy."})
            return
        if self._serve_final_file(head_only=False):
            return
        super().do_GET()

    def do_HEAD(self):
        if not self._host_ok() or self._path_blocked():
            self.send_response(404)
            self.end_headers()
            return
        if self._serve_final_file(head_only=True):
            return
        super().do_HEAD()

    def do_OPTIONS(self):
        # Không cấp CORS: preflight từ origin khác không nhận Access-Control-Allow-*.
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD, POST")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---- save ----------------------------------------------------------------
    def _discard_unread_body(self):
        """Từ chối sớm mà không đọc body dễ làm TCP gửi RST, client không nhận được mã lỗi: đọc bỏ body nhỏ, đóng kết nối nếu lớn."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if getattr(self, "_body_consumed", False) or length <= 0:
            return
        if length > MAX_DRAIN_BYTES:
            self.close_connection = True
            return
        # Client thật đang gửi body: đọc bỏ (không giữ trong bộ nhớ) rồi mới trả mã lỗi để client nhận được 4xx thay vì bị ngắt kết nối.
        remaining = length
        try:
            while remaining > 0:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        except OSError:
            self.close_connection = True

    def do_POST(self):
        self._body_consumed = False
        if urlsplit(self.path).path != "/api/save":
            self._discard_unread_body()
            self._send_json(404, {"status": "error", "message": "Không tìm thấy endpoint."})
            return
        try:
            if not self._host_ok():
                raise SaveError(403, "Host không được phép.")
            if not self._same_origin_ok():
                raise SaveError(403, "Origin không được phép.")
            supplied = self.headers.get("X-W17-Token") or ""
            if not hmac.compare_digest(supplied.encode("utf-8"), SESSION_TOKEN.encode("utf-8")):
                raise SaveError(401, "Thiếu hoặc sai token phiên. Tải lại trang editor rồi lưu lại.")
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json":
                raise SaveError(415, "Content-Type phải là application/json.")
            try:
                length = int(self.headers.get("Content-Length") or "")
            except ValueError:
                raise SaveError(411, "Thiếu Content-Length hợp lệ.")
            if length <= 0:
                raise SaveError(400, "Body rỗng.")
            if length > MAX_BODY_BYTES:
                raise SaveError(413, f"Body vượt giới hạn {MAX_BODY_BYTES // (1024 * 1024)}MB.")
            raw = self.rfile.read(length)
            self._body_consumed = True
            if len(raw) != length:
                raise SaveError(400, "Body bị cắt cụt.")
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise SaveError(400, "Body không phải JSON UTF-8 hợp lệ.")
            if not isinstance(data, dict):
                raise SaveError(400, "Body JSON phải là object.")

            html = data.get("html")
            targets = data.get("targets")
            if targets is None:
                targets = [data.get("filename")]
            if not isinstance(targets, list) or not targets or len(targets) > len(ALLOWED_FILES):
                raise SaveError(400, "Danh sách targets không hợp lệ.")
            if any(not isinstance(t, str) or t not in ALLOWED_FILES for t in targets):
                raise SaveError(400, "Tên file không nằm trong allowlist: " + ", ".join(sorted(ALLOWED_FILES)))
            targets = list(dict.fromkeys(targets))
            for name in targets:
                validate_html(name, html)

            saved, backups = [], []
            for name in targets:
                backup = save_with_backup(name, html)
                saved.append(name)
                if backup is not None:
                    backups.append(backup.name)
            self._send_json(200, {"status": "ok", "saved": saved, "backups": backups, "bytes": len(html.encode("utf-8"))})
        except SaveError as err:
            self._discard_unread_body()
            self._send_json(err.status, {"status": "error", "saved": [], "message": err.message})
        except OSError as err:
            self._send_json(500, {"status": "error", "saved": [], "message": f"Không ghi được file: {err.strerror or err}"})
        except Exception:
            self._send_json(500, {"status": "error", "saved": [], "message": "Lỗi nội bộ khi lưu file."})

    def log_message(self, fmt, *args):
        super().log_message(fmt, *args)


def make_server(port):
    return ThreadingHTTPServer(("127.0.0.1", port), PortfolioEditorHandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = make_server(port)
    print(f"Portfolio Editor Server running at http://127.0.0.1:{port}  (token phiên được cấp tự động cho trang cùng origin)")
    server.serve_forever()
