#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ kiểm thử hồi quy W17_04_Porfolio_Codex (Playwright + Chromium).

  python -X utf8 tests/regression/run_all.py [--shots DIR] [--only F03,F10] [--quick]

An toàn dữ liệu: toàn bộ kiểm thử chạy trên BẢN SAO TẠM của repo, với server.py thật trỏ vào thư mục tạm
(W17_BASE_DIR). File làm việc thật không bao giờ bị ghi; cuối cùng kiểm tra lại hash để chứng minh điều đó.
Trạng thái chỉ là PASS khi có kiểm tra thực tế; không có kiểm tra nào được coi là PASS mặc định.
"""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

import extra_cases as X  # noqa: E402
X.R = sys.modules[__name__]
import extra_cases_r3 as X3  # noqa: E402
X3.R = sys.modules[__name__]

REPO = Path(__file__).resolve().parents[2]
LOCALES = ["vi", "en", "es", "zh"]
VIEWPORTS = [(320, 568), (375, 812), (390, 844), (768, 1024), (1024, 768), (1440, 900)]
FINAL_PORTFOLIO = "index.html"
FINAL_CV = "index_portfolio_clean.html"
CREATOR_PORTFOLIO = "editor_workspace/editor_portfolio.html"
CREATOR_CV = "editor_workspace/editor_cv.html"
ALL_PAGES = [FINAL_PORTFOLIO, FINAL_CV, CREATOR_PORTFOLIO, CREATOR_CV]
TRACKED = ["index.html", "index_portfolio_clean.html", "editor_workspace/editor_portfolio.html",
           "editor_workspace/editor_cv.html", "server.py", "dev_server.py", "ga4_metrics_live.json"]

RESULTS = []


def record(fid, name, ok, detail=""):
    RESULTS.append((fid, name, "PASS" if ok else "FAIL", detail))
    print(("PASS " if ok else "FAIL ") + f"[{fid}] {name}" + (f" -- {detail}" if detail and not ok else ""))
    sys.stdout.flush()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


class Env:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="w17_04_test_"))
        self.work = self.tmp / "work"
        self.port = free_port()
        self.proc = None

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def prepare(self):
        shutil.copytree(REPO, self.work, ignore=shutil.ignore_patterns(".git", "__pycache__", ".w17_backups", "docs", "tests"))
        # sao lưu bản "sạch" để khôi phục giữa các ca ghi file
        self.pristine = self.tmp / "pristine"
        shutil.copytree(self.work, self.pristine)

    def reset_work(self):
        for rel in ["index.html", "index_portfolio_clean.html"]:
            shutil.copyfile(self.pristine / rel, self.work / rel)

    def start(self):
        env = dict(os.environ, PORT=str(self.port), W17_BASE_DIR=str(self.work), PYTHONUTF8="1")
        self.proc = subprocess.Popen([sys.executable, str(REPO / "server.py")], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(self.base + "/index.html", timeout=1).read(10)
                return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("test server không khởi động được")

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except Exception:
                self.proc.kill()
        shutil.rmtree(self.tmp, ignore_errors=True)


# ----------------------------------------------------------------- JS helpers
ORPHAN_JS = r"""
() => {
  const sel = 'h1, h2, [data-tail]';
  const bad = [], seen = [];
  const tokenRe = /[\u3400-\u9fff]|[^\s\u3400-\u9fff]+/g;
  document.querySelectorAll(sel).forEach((el) => {
    const r0 = el.getBoundingClientRect();
    if (!r0.width || !r0.height || el.closest('.hidden')) return;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const toks = [];
    let n;
    while ((n = walker.nextNode())) {
      const t = n.nodeValue; let m;
      tokenRe.lastIndex = 0;
      while ((m = tokenRe.exec(t))) {
        const rg = document.createRange();
        rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
        const rs = rg.getClientRects();
        if (rs.length) { const rr = rs[rs.length - 1]; toks.push({w: m[0], y: rr.top + rr.height / 2, h: rr.height}); }
      }
    }
    if (toks.length < 2) return;
    const lastY = toks[toks.length - 1].y, tol = Math.max(4, toks[0].h * 0.45);
    const lineYs = []; toks.forEach((k) => { if (!lineYs.some((y) => Math.abs(y - k.y) <= tol)) lineYs.push(k.y); });
    const onLast = toks.filter((k) => Math.abs(k.y - lastY) <= tol).length;
    const bal = getComputedStyle(el).getPropertyValue('text-wrap') || getComputedStyle(el).getPropertyValue('text-wrap-style');
    seen.push(el.getAttribute('data-i18n') || el.tagName);
    if (lineYs.length > 1 && onLast < 2) bad.push({key: el.getAttribute('data-i18n') || el.tagName, last: toks[toks.length - 1].w, lines: lineYs.length});
    if (!/balance/.test(bal)) bad.push({key: el.getAttribute('data-i18n') || el.tagName, noBalance: bal});
  });
  return {bad, count: seen.length};
}
"""

BALANCE_JS = r"""
() => {
  const miss = [];
  document.querySelectorAll('h1, h2, [data-tail]').forEach((el) => {
    const bal = getComputedStyle(el).getPropertyValue('text-wrap') || getComputedStyle(el).getPropertyValue('text-wrap-style');
    if (!/balance/.test(bal)) miss.push(el.tagName + ':' + (el.getAttribute('data-i18n') || ''));
  });
  return miss;
}
"""

SELECT_LANG_JS = """
(l) => { const s = document.querySelector('#langSelect, #langSelectCV'); s.value = l; s.dispatchEvent(new Event('change', {bubbles: true})); }
"""

LANG_SELECTOR = "#langSelect, #langSelectCV"

CLEAN_DOM_JS = r"""
() => ({
  contenteditable: document.querySelectorAll('[contenteditable]').length,
  spellcheck: document.querySelectorAll('[spellcheck]').length,
  toolbar: document.querySelectorAll('#visual-toolbar, #floating-toolbar').length,
  controls: document.querySelectorAll('.reorder-controls, .reorder-btn, .delete-btn, .add-tag-btn').length,
  creatorFlag: document.documentElement.hasAttribute('data-w17-mode'),
  editing: document.body.classList.contains('is-editing'),
  editLinks: [...document.querySelectorAll('a[href*="editor_"]')].map((a) => a.getAttribute('href'))
})
"""


# Cache genuine HTTPS CDN responses for repeatable browser checks. No library,
# stylesheet or font is stubbed. Missing/unreadable responses fail the test.
CDN_HOSTS = {"cdn.tailwindcss.com", "unpkg.com", "cdn.jsdelivr.net",
             "fonts.googleapis.com", "fonts.gstatic.com"}
CDN_MEMORY = {}
CDN_CACHE = Path(tempfile.gettempdir()) / "w17_04_verified_cdn_cache"


def serve_cdn(route):
    import gzip
    from urllib.parse import urlsplit
    url = route.request.url
    if urlsplit(url).hostname not in CDN_HOSTS:
        route.continue_()
        return
    ua = route.request.headers.get("user-agent", "")
    key = hashlib.sha256((url + "\\n" + ua).encode()).hexdigest()
    if key not in CDN_MEMORY:
        CDN_CACHE.mkdir(exist_ok=True)
        cache = CDN_CACHE / (key + ".json")
        try:
            import base64
            item = json.loads(cache.read_text(encoding="utf-8"))
            body = base64.b64decode(item["body"])
            if hashlib.sha256(body).hexdigest() != item["sha256"]:
                raise ValueError("CDN cache integrity mismatch")
            CDN_MEMORY[key] = (body, item["type"])
        except (OSError, ValueError, KeyError):
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"CDN returned {response.status}: {url}")
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                content_type = response.headers.get("Content-Type", "application/octet-stream")
            if not body:
                raise RuntimeError("Empty CDN response: " + url)
            import base64
            item = {"url": url, "type": content_type, "sha256": hashlib.sha256(body).hexdigest(),
                    "body": base64.b64encode(body).decode("ascii")}
            fd, tmp = tempfile.mkstemp(dir=CDN_CACHE, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(item, handle)
            os.replace(tmp, cache)
            CDN_MEMORY[key] = (body, content_type)
    body, content_type = CDN_MEMORY[key]
    route.fulfill(status=200, body=body, content_type=content_type)


def new_page(ctx, errors=None):
    pg = ctx.new_page()
    pg.route("https://**/*", serve_cdn)
    if errors is not None:
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append("console:" + m.text)
              if m.type == "error" and "net::" not in m.text and "Failed to load resource" not in m.text else None)
    return pg


def open_page(pg, env, rel, wait=650):
    pg.goto(f"{env.base}/{rel}", wait_until="load")
    pg.wait_for_timeout(wait)


def set_lang(pg, lang):
    pg.evaluate(SELECT_LANG_JS, lang)
    pg.wait_for_timeout(250)


def want(only, fid):
    return not only or fid in only


# ======================================================================= F01
def t_f01(b, env):
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = new_page(ctx)
    # Giả lập ứng dụng W17 khác cùng origin đang để ngôn ngữ/theme riêng
    open_page(pg, env, FINAL_PORTFOLIO)
    pg.evaluate("() => { localStorage.setItem('portfolio_lang','zh'); localStorage.setItem('portfolio_theme','light'); }")
    ok_all = True
    detail = []
    for rel in ALL_PAGES:
        pg.evaluate("() => { localStorage.removeItem('w17_04_lang'); localStorage.removeItem('w17_04_theme'); }")
        open_page(pg, env, rel)
        lang_now = pg.evaluate("document.documentElement.lang")
        if lang_now != "vi":
            ok_all = False; detail.append(f"{rel}: bị ảnh hưởng bởi portfolio_lang (lang={lang_now})")
        set_lang(pg, "es")
        pg.evaluate("() => { const t = document.getElementById('themeBtn') || document.getElementById('themeBtnCV'); if (t) t.click(); }")
        keys = pg.evaluate("() => Object.keys(localStorage).sort()")
        if "w17_04_lang" not in keys:
            ok_all = False; detail.append(f"{rel}: thiếu w17_04_lang")
        vals = pg.evaluate("() => ({pl: localStorage.getItem('portfolio_lang'), pt: localStorage.getItem('portfolio_theme')})")
        if vals["pl"] != "zh" or vals["pt"] != "light":
            ok_all = False; detail.append(f"{rel}: đã ghi đè khóa chung portfolio_*: {vals}")
        open_page(pg, env, rel)
        if pg.evaluate("document.documentElement.lang") != "es":
            ok_all = False; detail.append(f"{rel}: không nhớ w17_04_lang")
    record("F01", "language/theme dùng w17_04_*, không đọc/ghi portfolio_lang|theme (4 trang)", ok_all, "; ".join(detail))
    # theme key
    pg.evaluate("localStorage.clear()")
    open_page(pg, env, FINAL_PORTFOLIO)
    pg.click("#themeBtn"); pg.wait_for_timeout(150)
    th = pg.evaluate("localStorage.getItem('w17_04_theme')")
    open_page(pg, env, FINAL_PORTFOLIO)
    dark_after = pg.evaluate("document.documentElement.classList.contains('dark')")
    record("F01", "theme lưu ở w17_04_theme và được khôi phục khi tải lại", th == "light" and not dark_after, f"theme={th}, dark={dark_after}")
    ctx.close()


# ======================================================================= F02
def t_f02(b, env):
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = new_page(ctx)
    sentinel = {
        "w17_04_portfolio_edited_html_v1": "AUDIT_SENTINEL",
        "w17_04_portfolio_edited_header_v1": "AUDIT_SENTINEL",
        "tj_capability_w17_04_saved_html": "AUDIT_SENTINEL",
        "tj_capability_w17_04_saved_brand": "AUDIT_SENTINEL",
        "w17_portfolio_edited_html_v3": "W17_OTHER_APP",
        "tj_capability_v10_saved_html": "W17_OTHER_APP",
        "OTHER_APP_KEY": "KEEP",
        "w17_02_lang": "zh",
        "w17_02_theme": "light",
        "w17_02_portfolio_edits_v1": '{"schema":1,"editsByLang":{"vi":{"hero_positioning":"OLD_PROJECT_SENTINEL"}}}',
        "tj_capability_w17_02_state_v1": '{"schema":1,"textEditsByLang":{"vi":{"hero_bio":"OLD_PROJECT_SENTINEL"}}}', 
    }
    open_page(pg, env, FINAL_PORTFOLIO)
    pg.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", sentinel)
    lost = []
    for rel in ALL_PAGES + ALL_PAGES:
        open_page(pg, env, rel, 500)
        if pg.evaluate("document.documentElement.lang") != "vi" or "OLD_PROJECT_SENTINEL" in pg.locator("body").inner_text():
            lost.append(f"{rel}: imported W17_02 preferences or edits")
        now = pg.evaluate("(ks) => Object.fromEntries(ks.map((k) => [k, localStorage.getItem(k)]))", list(sentinel))
        for k, v in sentinel.items():
            if now[k] != v:
                lost.append(f"{rel}:{k}")
    record("F02", "mở cả 4 trang (2 lượt) không xóa/ghi đè bất kỳ key W17/W17_02 hay key ứng dụng khác", not lost, ", ".join(sorted(set(lost))))
    ctx.close()


# ======================================================================= F03
def modal_probe(pg, svc):
    return pg.evaluate("""(svc) => {
      const dlg = document.getElementById('ga4-modal-dialog');
      const body = document.getElementById('ga4-modal-body');
      const cs = (e) => getComputedStyle(e).overflowY;
      const scroller = (cs(body) !== 'visible' && body.scrollHeight > body.clientHeight + 1) ? body : dlg;
      const sr = scroller.getBoundingClientRect();
      const t = document.getElementById('modal-pkg-' + svc).getBoundingClientRect();
      const items = [...document.querySelectorAll('#modal-service-packages li')];
      return {tTop: t.top, tBot: t.bottom, sTop: sr.top, sBot: sr.bottom, vh: innerHeight, items: items.length,
              inScroll: !!scroller.contains(document.getElementById('modal-service-packages')),
              scrollerId: scroller.id, canScroll: scroller.scrollHeight > scroller.clientHeight + 1,
              dlgBottom: dlg.getBoundingClientRect().bottom};
    }""", svc)


def t_f03(b, env, quick, shots):
    pages = [FINAL_PORTFOLIO, CREATOR_PORTFOLIO]
    vps = VIEWPORTS + [(720, 450)]
    if quick:
        vps = [(320, 568), (375, 812), (720, 450), (1440, 900)]
    cards = [("p1", 0), ("p2", 1), ("p3", 2), ("p4", 3)]
    fails = []
    checks = 0
    for rel in pages:
        for (w, h) in vps:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = new_page(ctx)
            open_page(pg, env, rel)
            for lang in LOCALES:
                set_lang(pg, lang)
                for svc, idx in cards:
                    # bấm đúng thẻ dịch vụ (người dùng thật), không gọi hàm trực tiếp
                    pg.evaluate("window.scrollTo(0,0)")
                    card_btn = pg.locator("#ga4-ecosystem button[aria-controls='ga4-drilldown-modal']").nth(idx)
                    card_btn.scroll_into_view_if_needed()
                    card_btn.click()
                    pg.wait_for_timeout(750)
                    r = modal_probe(pg, svc)
                    checks += 1
                    inside = r["tTop"] >= r["sTop"] - 1 and r["tTop"] < min(r["sBot"], r["vh"])
                    if not (r["inScroll"] and inside):
                        fails.append(f"{rel}@{w}x{h}/{lang}/{svc}: nhóm không vào vùng nhìn thấy {r}")
                    # mọi đầu việc phải đọc được bằng cuộn: kiểm tra từng đầu việc bằng cách cuộn tới và đo
                    reach = pg.evaluate("""async () => {
                      const dlg = document.getElementById('ga4-modal-dialog');
                      const body = document.getElementById('ga4-modal-body');
                      const scroller = (getComputedStyle(body).overflowY !== 'visible' && body.scrollHeight > body.clientHeight + 1) ? body : dlg;
                      const items = [...document.querySelectorAll('#modal-service-packages li')];
                      let ok = 0;
                      for (const li of items) {
                        const sr0 = scroller.getBoundingClientRect();
                        const d = li.getBoundingClientRect().top - sr0.top - 40;
                        scroller.scrollTop += d;
                        await new Promise((r) => setTimeout(r, 30));
                        const sr = scroller.getBoundingClientRect(), r = li.getBoundingClientRect();
                        if (r.top >= Math.max(sr.top, 0) - 1 && r.bottom <= Math.min(sr.bottom, innerHeight) + 1) ok++;
                      }
                      return {ok, total: items.length};
                    }""")
                    if reach["total"] != 12 or reach["ok"] != 12:
                        fails.append(f"{rel}@{w}x{h}/{lang}/{svc}: chỉ {reach['ok']}/{reach['total']} đầu việc tiếp cận được")
                    if shots and lang == "vi" and svc == "p4" and (w, h) in [(375, 812), (720, 450)] and rel == FINAL_PORTFOLIO:
                        pg.screenshot(path=str(Path(shots) / f"F03-modal-{w}x{h}.png"))
                    pg.keyboard.press("Escape")
                    pg.wait_for_timeout(120)
            ctx.close()
    record("F03", f"mọi nhóm đầu việc (12 đầu việc) đọc/cuộn được; bấm thẻ dịch vụ đưa đúng nhóm vào vùng nhìn thấy ({checks} tổ hợp: 2 trang x {len(vps)} viewport x 4 ngôn ngữ x 4 thẻ)", not fails, " | ".join(fails[:6]))


def t_f03_keyboard(b, env):
    ctx = b.new_context(viewport={"width": 375, "height": 600})
    pg = new_page(ctx)
    open_page(pg, env, FINAL_PORTFOLIO)
    btn = pg.locator("#ga4-ecosystem button[aria-controls='ga4-drilldown-modal']").nth(3)
    btn.scroll_into_view_if_needed()
    btn.focus()
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(800)
    focused = pg.evaluate("document.activeElement && document.activeElement.id")
    # focus trap: Tab nhiều lần không thoát khỏi modal
    escaped = False
    for _ in range(30):
        pg.keyboard.press("Tab")
        inside = pg.evaluate("!!document.activeElement.closest('#ga4-drilldown-modal')")
        if not inside:
            escaped = True
            break
    # vùng cuộn thân modal nhận focus bàn phím và cuộn bằng phím
    pg.evaluate("document.getElementById('ga4-modal-body').focus()")
    before = pg.evaluate("document.getElementById('ga4-modal-dialog').scrollTop")
    pg.keyboard.press("PageUp"); pg.keyboard.press("PageUp"); pg.keyboard.press("PageUp")
    pg.wait_for_timeout(300)
    after_up = pg.evaluate("document.getElementById('ga4-modal-dialog').scrollTop")
    pg.keyboard.press("PageDown"); pg.wait_for_timeout(300)
    after_down = pg.evaluate("document.getElementById('ga4-modal-dialog').scrollTop")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    back = pg.evaluate("document.activeElement === document.querySelectorAll('#ga4-ecosystem button[aria-controls=\"ga4-drilldown-modal\"]')[3]")
    ok = focused == "ga4-modal-close-btn" and not escaped and after_up < before and after_down > after_up and back
    record("F03", "bàn phím: Enter mở modal, focus vào nút đóng, bẫy focus, PageUp/PageDown cuộn được, Escape trả focus về thẻ",
           ok, f"focused={focused} escaped={escaped} before={before} up={after_up} down={after_down} back={back}")
    ctx.close()


# ======================================================================= F04 / F06 / F08
def t_i18n(b, env):
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = new_page(ctx)
    dicts, miss = {}, []
    for rel in ALL_PAGES:
        open_page(pg, env, rel)
        data = pg.evaluate("""() => {
          const d = (typeof translations !== 'undefined') ? translations : translationsCV;
          const keys = new Set();
          document.querySelectorAll('[data-i18n]').forEach((e) => keys.add(e.getAttribute('data-i18n')));
          const aria = new Set(); document.querySelectorAll('[data-i18n-aria]').forEach((e) => aria.add(e.getAttribute('data-i18n-aria')));
          const ph = new Set(); document.querySelectorAll('[data-i18n-placeholder]').forEach((e) => ph.add(e.getAttribute('data-i18n-placeholder')));
          return {d, used: [...keys], aria: [...aria], ph: [...ph]};
        }""")
        dicts[rel] = data["d"]
        sets = {l: set(data["d"][l]) for l in LOCALES}
        for l in LOCALES:
            absent = [k for k in data["used"] + data["aria"] + data["ph"] if k not in sets[l]]
            # các khóa tên/điện thoại động có thể không nằm trong từ điển — chỉ tính khóa thật sự dùng bởi data-i18n
            if absent:
                miss.append(f"{rel}/{l}: thiếu {absent[:5]}")
        base = sets["vi"]
        for l in LOCALES[1:]:
            if sets[l] != base:
                miss.append(f"{rel}: bộ khóa {l} lệch vi ({len(sets[l] ^ base)} khóa)")
    record("F04", "mọi data-i18n/-aria/-placeholder có đủ khóa ở vi/en/es/zh và bốn locale cùng bộ khóa (4 trang)", not miss, " | ".join(miss[:6]))
    same_p = json.dumps(dicts[FINAL_PORTFOLIO], sort_keys=True) == json.dumps(dicts[CREATOR_PORTFOLIO], sort_keys=True)
    same_c = json.dumps(dicts[FINAL_CV], sort_keys=True) == json.dumps(dicts[CREATOR_CV], sort_keys=True)
    record("F04", "từ điển bản dịch Creator = Final (portfolio và CV, cả bốn locale)", same_p and same_c, f"portfolio={same_p} cv={same_c}")
    ctx.close()


def t_f04_cta(b, env):
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = new_page(ctx)
    bad = []
    for rel in (FINAL_PORTFOLIO, CREATOR_PORTFOLIO):
        open_page(pg, env, rel)
        texts = {}
        for l in LOCALES:
            set_lang(pg, l)
            texts[l] = pg.evaluate("[...document.querySelectorAll('[data-i18n=eco_btn_detail]')].map((e) => e.textContent.trim())")
        if len({tuple(v) for v in texts.values()}) != 4 or any(len(v) != 4 for v in texts.values()):
            bad.append(f"{rel}: CTA không đổi theo locale {texts}")
        for l in LOCALES:
            set_lang(pg, l)
            hero_ok = pg.evaluate("""() => { const h = document.querySelector('h1[data-i18n=hero_title]'); return h.querySelectorAll('br').length >= 1 && h.querySelectorAll('span.inline-block').length >= 1; }""")
            if not hero_ok:
                bad.append(f"{rel}/{l}: Hero mất br/span")
    record("F04", "4 CTA 'Xem bảng chi tiết' dịch theo locale ở Final và Creator; Hero giữ <br> và span.inline-block sau khi đổi ngôn ngữ", not bad, " | ".join(bad))
    ctx.close()


def t_f06_cv(b, env):
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = new_page(ctx)
    bad = []
    for rel in (FINAL_CV, CREATOR_CV):
        open_page(pg, env, rel)
        for l in LOCALES:
            set_lang(pg, l)
            counts = pg.evaluate("() => ['hero_bio', 'footer_desc'].map((k) => document.querySelector('[data-i18n=' + k + ']').querySelectorAll('span.inline-block').length)")
            if counts != [1, 1]:
                bad.append(f"{rel}/{l}: span.inline-block={counts}")
    record("F06", "hero_bio và footer_desc của CV còn span bảo vệ đuôi câu sau mỗi lần đổi ngôn ngữ (4 locale x 2 trang)", not bad, " | ".join(bad[:6]))
    ctx.close()


def t_f08(b, env, quick, shots):
    vps = VIEWPORTS if not quick else [(320, 568), (375, 812), (390, 844), (1440, 900)]
    bad, n = [], 0
    for rel in ALL_PAGES:
        for (w, h) in vps:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = new_page(ctx)
            open_page(pg, env, rel)
            for l in LOCALES:
                set_lang(pg, l)
                res = pg.evaluate(ORPHAN_JS)
                n += res["count"]
                for item in res["bad"]:
                    bad.append(f"{rel}@{w}/{l}: {item}")
                if shots and rel == CREATOR_PORTFOLIO and l == "en" and w == 375:
                    pg.evaluate("window.scrollTo(0,0)"); pg.screenshot(path=str(Path(shots) / "F08-creator-portfolio-en-375.png"))
            ctx.close()
    record("F08", f"không có dòng cuối chỉ 1 từ (orphan) và H1/H2/đoạn Hero có text-wrap: balance — đo theo vị trí từng từ ({n} phần tử, 4 trang x {len(vps)} viewport x 4 locale)", not bad, " | ".join(bad[:8]))


# ======================================================================= F05 safe rendering
def t_f05(b, env):
    evil = ('<img src=x onerror="window.__pwned=1">EVIL<script>window.__pwned=2</script><span class="inline-block" '
            'onclick="window.__pwned=3" style="x">tail ok</span><a href="javascript:window.__pwned=4">L</a>')
    bad = []
    # 1) cache có schema chứa HTML độc hại
    for rel, key, shape in [
        (FINAL_PORTFOLIO, "w17_04_portfolio_edits_v1", lambda: {"schema": 1, "editsByLang": {"vi": {"hero_badge": evil, "__proto__": {"x": "1"}}}}),
        (CREATOR_PORTFOLIO, "w17_04_portfolio_edits_v1", lambda: {"schema": 1, "editsByLang": {"vi": {"hero_badge": evil}}}),
        (FINAL_CV, "tj_capability_w17_04_state_v1", lambda: {"schema": 1, "textEditsByLang": {"vi": {"hero_bio": evil}}, "fieldEdits": {"hero_name": evil}, "avatarDataUrl": "javascript:window.__pwned=5"}),
        (CREATOR_CV, "tj_capability_w17_04_state_v1", lambda: {"schema": 1, "textEditsByLang": {"vi": {"hero_bio": evil}}, "fieldEdits": {"hero_name": evil}, "avatarDataUrl": "javascript:window.__pwned=5"}),
    ]:
        ctx = b.new_context(viewport={"width": 1280, "height": 800})
        pg = new_page(ctx)
        open_page(pg, env, rel)
        pg.evaluate("([k, v]) => localStorage.setItem(k, v)", [key, json.dumps(shape())])
        open_page(pg, env, rel)
        r = pg.evaluate("""() => ({pwned: window.__pwned || 0,
            injected: document.querySelectorAll('img[src="x"], a[href^="javascript"], [onerror], [onclick*="__pwned"]').length,
            text: (document.querySelector('[data-i18n=hero_badge], [data-i18n=hero_bio]') || {}).textContent || '',
            avatar: (document.getElementById('avatar-img') || {src: ''}).src.slice(0, 11)})""")
        if r["pwned"] or r["injected"] or "EVIL" not in r["text"] or r["avatar"].startswith("javascript"):
            bad.append(f"{rel}: cache độc hại {r}")
        ctx.close()
    # 2) snapshot innerHTML cũ (legacy) độc hại: được parse trơ, không chạy script, không giữ thuộc tính
    legacy_main = ('<section><h1 data-i18n="hero_title" contenteditable="true">X<img src=x onerror="window.__pwned=6"><script>window.__pwned=7</script></h1>'
                   '<span data-i18n="hero_badge" contenteditable="true" onclick="window.__pwned=8">Legacy edited badge</span></section>')
    for rel, keys in [(FINAL_PORTFOLIO, {"w17_04_portfolio_edited_html_v1": legacy_main}),
                      (CREATOR_PORTFOLIO, {"w17_04_portfolio_edited_html_v1": legacy_main})]:
        ctx = b.new_context(viewport={"width": 1280, "height": 800})
        pg = new_page(ctx)
        open_page(pg, env, rel)
        pg.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", keys)
        open_page(pg, env, rel)
        r = pg.evaluate("""() => ({pwned: window.__pwned || 0, imgs: document.querySelectorAll('img[src="x"]').length,
            ce: document.querySelectorAll('[contenteditable]').length - (document.body.classList.contains('is-editing') ? 1e6 : 0),
            badge: document.querySelector('[data-i18n=hero_badge]').textContent.trim(),
            legacyKept: !!localStorage.getItem('w17_04_portfolio_edited_html_v1')})""")
        if r["pwned"] or r["imgs"] or r["ce"] > 0 or r["badge"] != "Legacy edited badge" or not r["legacyKept"]:
            bad.append(f"{rel}: legacy snapshot {r}")
        ctx.close()
    record("F05", "cache/snapshot độc hại (img onerror, script, onclick, javascript:, __proto__) không thực thi, không chèn node, không giữ thuộc tính; bản legacy không bị xóa", not bad, " | ".join(bad))

    # 3) Không còn đường gán nguyên khối cache vào innerHTML
    pat_bad = []
    for rel in ALL_PAGES:
        src = (REPO / rel).read_text(encoding="utf-8")
        for needle in ["root.innerHTML = savedHTML", "mainEl.innerHTML = savedMain", "headerEl.innerHTML = savedHeader", "brandEl.innerHTML = savedBrand"]:
            if needle in src:
                pat_bad.append(f"{rel}: còn '{needle}'")
    record("F05", "mã nguồn không còn gán snapshot HTML cache vào innerHTML (4 trang)", not pat_bad, " | ".join(pat_bad))


def t_f05_migration(b, env):
    """Bảo toàn snapshot HTML bằng fixture độc lập; không yêu cầu lịch sử Git của dự án nguồn."""
    import gzip
    data = json.loads(gzip.decompress((REPO / "tests/fixtures/legacy_creators.json.gz").read_bytes()))
    old = {rel: data[rel].encode("utf-8") for rel in (CREATOR_PORTFOLIO, CREATOR_CV)}
    legacy_dir = Path(env.work) / "editor_workspace"
    for rel, data in old.items():
        (legacy_dir / ("legacy_" + Path(rel).name)).write_bytes(data)
    bad = []
    try:
        # Creator portfolio cũ
        ctx = b.new_context(viewport={"width": 1280, "height": 800})
        pg = new_page(ctx)
        pg.goto(f"{env.base}/editor_workspace/legacy_editor_portfolio.html"); pg.wait_for_timeout(900)
        pg.evaluate("toggleEditMode()")
        pg.evaluate("""() => { const e = document.querySelector('[data-i18n=hero_badge]'); e.textContent = 'MIGRATE-ME portfolio badge'; e.dispatchEvent(new Event('input', {bubbles: true})); }""")
        pg.wait_for_timeout(300)
        legacy_vals = pg.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
        ctx.close()
        ctx = b.new_context(viewport={"width": 1280, "height": 800})
        pg = new_page(ctx)
        pg.goto(f"{env.base}/editor_workspace/editor_portfolio.html"); pg.wait_for_timeout(300)
        pg.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", legacy_vals)
        legacy_before = {k: legacy_vals[k] for k in legacy_vals if k.startswith("w17_04_portfolio_edited")}
        open_page(pg, env, CREATOR_PORTFOLIO)
        badge = pg.evaluate("document.querySelector('[data-i18n=hero_badge]').textContent.trim()")
        kept = pg.evaluate("(ks) => Object.fromEntries(ks.map((k) => [k, localStorage.getItem(k)]))", list(legacy_before))
        state = pg.evaluate("JSON.parse(localStorage.getItem('w17_04_portfolio_edits_v1') || 'null')")
        if badge != "MIGRATE-ME portfolio badge":
            bad.append(f"portfolio: chỉnh sửa cũ không được chuyển (badge={badge!r})")
        if kept != legacy_before:
            bad.append("portfolio: bản snapshot cũ bị thay đổi/xóa")
        if not state or not state.get("migratedFrom"):
            bad.append(f"portfolio: thiếu dấu migratedFrom {state}")
        # sang ngôn ngữ khác rồi quay lại vẫn giữ
        set_lang(pg, "en"); set_lang(pg, "vi")
        if pg.evaluate("document.querySelector('[data-i18n=hero_badge]').textContent.trim()") != "MIGRATE-ME portfolio badge":
            bad.append("portfolio: mất chỉnh sửa sau khi đổi ngôn ngữ")
        # Final cùng origin cũng đọc được dữ liệu đã chuyển, không xóa bản cũ
        open_page(pg, env, FINAL_PORTFOLIO)
        if pg.evaluate("document.querySelector('[data-i18n=hero_badge]').textContent.trim()") != "MIGRATE-ME portfolio badge":
            bad.append("portfolio Final: không hiển thị dữ liệu đã chuyển")
        ctx.close()

        # Creator CV cũ
        ctx = b.new_context(viewport={"width": 1280, "height": 800})
        pg = new_page(ctx)
        pg.goto(f"{env.base}/editor_workspace/legacy_editor_cv.html"); pg.wait_for_timeout(900)
        pg.evaluate("""() => {
          const secs = document.querySelectorAll('#reorderable-sections > .reorderable-section');
          const first = secs[0].querySelector('.reorder-btn[onclick*="1)"]'); if (first) first.click();
          const tag = document.querySelector('.skill-tag .tag-text'); if (tag) { tag.textContent = 'MIGRATE-ME-TAG'; tag.dispatchEvent(new Event('input', {bubbles: true})); }
          document.body.dispatchEvent(new Event('input', {bubbles: true}));
        }""")
        pg.wait_for_timeout(300)
        order_before = pg.evaluate("[...document.querySelectorAll('#reorderable-sections > .reorderable-section')].map((s) => s.getAttribute('data-section-id'))")
        legacy_vals = pg.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
        ctx.close()
        ctx = b.new_context(viewport={"width": 1280, "height": 800})
        pg = new_page(ctx)
        pg.goto(f"{env.base}/editor_workspace/editor_cv.html"); pg.wait_for_timeout(300)
        pg.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", legacy_vals)
        legacy_snapshot = legacy_vals.get("tj_capability_w17_04_saved_html")
        open_page(pg, env, CREATOR_CV)
        order_after = pg.evaluate("[...document.querySelectorAll('#reorderable-sections > .reorderable-section')].map((s) => s.getAttribute('data-section-id'))")
        tag_ok = pg.evaluate("[...document.querySelectorAll('.skill-tag')].some((t) => t.textContent.includes('MIGRATE-ME-TAG'))")
        kept = pg.evaluate("localStorage.getItem('tj_capability_w17_04_saved_html')")
        if order_after != order_before:
            bad.append(f"cv: thứ tự section không được giữ {order_before} -> {order_after}")
        if not tag_ok:
            bad.append("cv: tag đã sửa không được giữ")
        if kept != legacy_snapshot:
            bad.append("cv: snapshot cũ bị thay đổi/xóa")
        ctx.close()
    finally:
        for rel in old:
            try:
                (legacy_dir / ("legacy_" + Path(rel).name)).unlink()
            except OSError:
                pass
    record("F05", "migration: chỉnh sửa tạo bởi Creator CŨ (snapshot innerHTML) vẫn hiện ở Creator/Final MỚI; bản cũ không bị xóa", not bad, " | ".join(bad))



def t_f05_nodes(b, env):
    """Chỉnh sửa node KHÔNG có data-i18n (thương hiệu, nhãn, bản quyền...) vẫn còn sau khi tải lại Creator và khi đổi ngôn ngữ."""
    bad = []
    for rel, idx_name in [(CREATOR_PORTFOLIO, "w17NodeIndex"), (CREATOR_CV, "nodeIndexCV"), (FINAL_PORTFOLIO, "w17NodeIndex"), (FINAL_CV, "nodeIndexCV")]:
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = new_page(ctx)
        open_page(pg, env, rel)
        n_nodes = pg.evaluate(f"{idx_name}.length")
        if n_nodes < 3:
            bad.append(f"{rel}: chỉ mục node quá ít ({n_nodes})")
            ctx.close()
            continue
        if not pg.evaluate("document.body.classList.contains('is-editing')"):
            pg.keyboard.press("Alt+e") if rel in (FINAL_PORTFOLIO, FINAL_CV) else pg.click("#btn-toggle-edit")
            pg.wait_for_timeout(250)
        orig = pg.evaluate(f"{idx_name}[2].el.textContent")
        pg.evaluate(f"() => {{ const e = {idx_name}[2].el; e.textContent = 'NODEEDIT-KEEP'; e.dispatchEvent(new Event('input', {{bubbles: true}})); document.body.dispatchEvent(new Event('input', {{bubbles: true}})); }}")
        pg.wait_for_timeout(250)
        open_page(pg, env, rel)
        after = pg.evaluate(f"{idx_name}[2].el.textContent")
        set_lang(pg, "en"); set_lang(pg, "zh")
        after_lang = pg.evaluate(f"{idx_name}[2].el.textContent")
        if after != "NODEEDIT-KEEP" or after_lang != "NODEEDIT-KEEP":
            bad.append(f"{rel}: node không-i18n mất chỉnh sửa (sau reload={after!r}, sau đổi ngôn ngữ={after_lang!r}, gốc={orig!r})")
        # văn bản gốc khác => không áp nhầm: sửa dữ liệu "from" rồi tải lại, node phải giữ văn bản hiện hành
        key = "w17_04_portfolio_edits_v1" if idx_name == "w17NodeIndex" else "tj_capability_w17_04_state_v1"
        pg.evaluate("(k) => { const s = JSON.parse(localStorage.getItem(k)); Object.keys(s.nodeEdits).forEach((i) => { s.nodeEdits[i].from = 'KHÔNG-KHỚP'; }); localStorage.setItem(k, JSON.stringify(s)); }", key)
        open_page(pg, env, rel)
        mism = pg.evaluate(f"{idx_name}[2].el.textContent")
        if mism == "NODEEDIT-KEEP":
            bad.append(f"{rel}: áp nhầm chỉnh sửa khi văn bản gốc không khớp")
        ctx.close()
    record("F05", "chỉnh sửa node không có data-i18n được lưu theo schema (chỉ số + văn bản gốc), còn sau reload/đổi ngôn ngữ, và không áp nhầm khi văn bản gốc không khớp (4 trang)", not bad, " | ".join(bad))

# ======================================================================= F07 round trip
def edit_portfolio(pg):
    pg.keyboard.press("Alt+e") if not pg.evaluate("document.body.classList.contains('is-editing')") else None
    pg.wait_for_timeout(150)
    # Creator đã hiện toolbar sẵn: Alt+E lần đầu bật sửa; Final: Alt+E hiện toolbar + bật sửa
    if not pg.evaluate("document.body.classList.contains('is-editing')"):
        pg.keyboard.press("Alt+e"); pg.wait_for_timeout(150)
    pg.evaluate("""() => { const e = document.querySelector('[data-i18n=hero_badge]'); e.focus(); e.textContent = 'ROUNDTRIP badge EN edit'; e.dispatchEvent(new Event('input', {bubbles: true})); }""")
    pg.wait_for_timeout(150)


def click_save(pg, wait=1200):
    with pg.expect_download(timeout=8000):
        pg.evaluate("document.getElementById('btn-save-final').scrollIntoView({block:'center'})")
        pg.click("#btn-save-final")
    pg.wait_for_timeout(wait)


def t_f07(b, env):
    """chỉnh sửa -> lưu -> xuất Final -> mở lại (cache trống / cache có dữ liệu) -> đổi ngôn ngữ -> bấm link điều hướng."""
    bad = []
    for scenario in ("cache-empty", "cache-with-data"):
        for src_rel, out_rel, other_final in [(CREATOR_PORTFOLIO, FINAL_PORTFOLIO, FINAL_CV), (FINAL_PORTFOLIO, FINAL_PORTFOLIO, FINAL_CV),
                                              (CREATOR_CV, FINAL_CV, FINAL_PORTFOLIO), (FINAL_CV, FINAL_CV, FINAL_PORTFOLIO)]:
            env.reset_work()
            is_cv = out_rel == FINAL_CV
            ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
            pg = new_page(ctx)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            open_page(pg, env, src_rel)
            if scenario == "cache-with-data":
                # đã có dữ liệu chỉnh sửa từ phiên trước (đặt bằng đúng schema)
                if is_cv:
                    pg.evaluate("localStorage.setItem('tj_capability_w17_04_state_v1', JSON.stringify({schema:1, textEditsByLang:{vi:{sol_heading:'PRE-EXISTING heading VI'}}}))")
                else:
                    pg.evaluate("localStorage.setItem('w17_04_portfolio_edits_v1', JSON.stringify({schema:1, editsByLang:{vi:{hero_btn_github:'PRE-EXISTING github VI'}}}))")
                open_page(pg, env, src_rel)
            set_lang(pg, "en")
            # chỉnh sửa trong EN
            if is_cv:
                if not pg.evaluate("document.body.classList.contains('is-editing')"):
                    if pg.evaluate("!document.getElementById('floating-toolbar') || document.getElementById('floating-toolbar').classList.contains('hidden')"):
                        pg.keyboard.press("Alt+e")
                    else:
                        pg.click("#btn-toggle-edit")
                    pg.wait_for_timeout(250)
                pg.evaluate("""() => { const e = document.querySelector('[data-i18n=footer_title]'); e.focus(); e.textContent = 'ROUNDTRIP footer EN edit'; e.dispatchEvent(new Event('input', {bubbles: true})); }""")
                # đổi thứ tự section thật bằng nút trên trang
                pg.evaluate("""() => { const b = document.querySelector('.reorderable-section .reorder-btn[onclick*="1)"]'); if (b) b.click(); }""")
                order_edit = pg.evaluate("[...document.querySelectorAll('#reorderable-sections > .reorderable-section')].map((s) => s.getAttribute('data-section-id'))")
            else:
                edit_portfolio(pg)
                order_edit = None
            pg.wait_for_timeout(200)
            creator_cache_before = pg.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
            mtime_before = (env.work / out_rel).stat().st_mtime_ns
            click_save(pg)
            written = (env.work / out_rel).read_text(encoding="utf-8")
            # Kiểm theo TRẠNG THÁI thật (file đã đổi trên đĩa, có bản sao lưu), không dò chữ trong toast (toast theo locale)
            if (env.work / out_rel).stat().st_mtime_ns == mtime_before or not list((env.work / ".w17_backups").glob(out_rel + ".*.bak")):
                bad.append(f"{scenario}/{src_rel}: file không được ghi/không có backup sau khi bấm Lưu")
            if (env.work / out_rel).stat().st_size < 50000:
                bad.append(f"{scenario}/{src_rel}: file ghi ra quá nhỏ")
            marker = "ROUNDTRIP footer EN edit" if is_cv else "ROUNDTRIP badge EN edit"
            # cache của Creator không bị xóa
            creator_cache_after = pg.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
            for k, v in creator_cache_before.items():
                if k not in creator_cache_after:
                    bad.append(f"{scenario}/{src_rel}: Final/Creator đã xóa key {k}")
            same_origin_cache = creator_cache_after

            def check_reopen(label, ctx2, init_cache):
                pg2 = new_page(ctx2)
                if init_cache is not None:
                    pg2.goto(f"{env.base}/{other_final}"); pg2.wait_for_timeout(250)
                    pg2.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", init_cache)
                open_page(pg2, env, out_rel)
                dom = pg2.evaluate(CLEAN_DOM_JS)
                if dom["contenteditable"] or dom["spellcheck"] or dom["toolbar"] or dom["controls"] or dom["creatorFlag"] or dom["editing"] or dom["editLinks"]:
                    bad.append(f"{scenario}/{src_rel}/{label}: DOM sau khi mở lại chưa sạch {dom}")
                set_lang(pg2, "en")
                txt = pg2.evaluate("document.body.innerText")
                if marker not in txt:
                    bad.append(f"{scenario}/{src_rel}/{label}: mất nội dung đã chỉnh ('{marker}')")
                set_lang(pg2, "vi")
                if marker in pg2.evaluate("document.body.innerText"):
                    bad.append(f"{scenario}/{src_rel}/{label}: chỉnh sửa EN rò sang VI")
                if scenario == "cache-with-data":
                    pre = "PRE-EXISTING heading VI" if is_cv else "PRE-EXISTING github VI"
                    if pre not in pg2.evaluate("document.body.innerText"):
                        bad.append(f"{scenario}/{src_rel}/{label}: mất dữ liệu có sẵn '{pre}'")
                if is_cv and order_edit is not None:
                    order_now = pg2.evaluate("[...document.querySelectorAll('#reorderable-sections > .reorderable-section')].map((s) => s.getAttribute('data-section-id'))")
                    if order_now != order_edit:
                        bad.append(f"{scenario}/{src_rel}/{label}: thứ tự section không giữ ({order_edit} vs {order_now})")
                errors = []
                pg2.on("pageerror", lambda e: errors.append(str(e)))
                # đổi qua đủ 4 ngôn ngữ, không lỗi JS
                for l in LOCALES:
                    set_lang(pg2, l)
                # bấm link điều hướng thật tới Final kia rồi quay lại
                link = pg2.locator(f"a[href='./{other_final}']").first
                link.scroll_into_view_if_needed()
                with pg2.expect_navigation(timeout=8000):
                    link.click()
                pg2.wait_for_timeout(500)
                if not pg2.url.endswith("/" + other_final):
                    bad.append(f"{scenario}/{src_rel}/{label}: bấm link không tới {other_final} (url={pg2.url})")
                back = pg2.locator(f"a[href='./{out_rel}']").first
                back.scroll_into_view_if_needed()
                with pg2.expect_navigation(timeout=8000):
                    back.click()
                pg2.wait_for_timeout(500)
                if not pg2.url.endswith("/" + out_rel):
                    bad.append(f"{scenario}/{src_rel}/{label}: link quay lại sai (url={pg2.url})")
                if errors:
                    bad.append(f"{scenario}/{src_rel}/{label}: lỗi JS {errors[:2]}")
                return pg2

            # (a) cache TRỐNG: ngữ cảnh mới
            ctx_empty = b.new_context(viewport={"width": 1280, "height": 900})
            check_reopen("cache-trống", ctx_empty, None)
            ctx_empty.close()
            # (b) cache CÓ DỮ LIỆU: cùng bộ nhớ của Creator
            ctx_cache = b.new_context(viewport={"width": 1280, "height": 900})
            check_reopen("cache-có-dữ-liệu", ctx_cache, same_origin_cache)
            ctx_cache.close()
            # (c) Creator mở lại vẫn còn dữ liệu của chính nó
            if src_rel.startswith("editor_workspace"):
                pg3 = ctx.new_page()
                open_page(pg3, env, src_rel)
                set_lang(pg3, "en")
                if marker not in pg3.evaluate("document.body.innerText"):
                    bad.append(f"{scenario}/{src_rel}: Creator mất chỉnh sửa của chính nó sau khi xuất Final")
            if errs:
                bad.append(f"{scenario}/{src_rel}: lỗi JS khi chỉnh sửa/lưu {errs[:2]}")
            ctx.close()
    record("F07", "chu trình chỉnh sửa → lưu (server thật) → xuất Final → mở lại (cache trống & cache có dữ liệu) → đổi 4 ngôn ngữ → bấm link hai chiều; DOM sau khi mở lại sạch; dữ liệu cũ/mới không mất", not bad, " | ".join(bad[:8]))
    env.reset_work()


def t_f07_dom_scan(b, env):
    """Xuất Final từ cache có đủ loại trạng thái editor (đang bật sửa, link editor_*) rồi quét DOM sau khi mở lại."""
    bad = []
    for src in (CREATOR_PORTFOLIO, CREATOR_CV):
        env.reset_work()
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        pg = new_page(ctx)
        open_page(pg, env, src)
        pg.keyboard.press("Alt+e"); pg.wait_for_timeout(250)
        # xuất khi đang BẬT sửa chữ (trạng thái xấu nhất)
        editing = pg.evaluate("document.body.classList.contains('is-editing')")
        click_save(pg)
        out = FINAL_PORTFOLIO if src == CREATOR_PORTFOLIO else FINAL_CV
        html = (env.work / out).read_text(encoding="utf-8")
        import re
        static = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
        if re.search(r"""\scontenteditable\s*=|id=["'](?:visual|floating)-toolbar["']|is-editing""", static.replace('class="dark scroll-smooth"', "")):
            if "is-editing" in static.split("<body", 1)[1].split(">", 1)[0] or re.search(r"""\scontenteditable\s*=|id=["'](?:visual|floating)-toolbar["']""", static):
                bad.append(f"{src}: HTML đã serialize còn trạng thái editor")
        for l in ("cache-có-dữ-liệu", "cache-trống"):
            ctx2 = b.new_context(viewport={"width": 1280, "height": 900}) if l == "cache-trống" else ctx
            pg2 = ctx2.new_page()
            open_page(pg2, env, out)
            dom = pg2.evaluate(CLEAN_DOM_JS)
            if dom["contenteditable"] or dom["spellcheck"] or dom["toolbar"] or dom["controls"] or dom["creatorFlag"] or dom["editing"] or dom["editLinks"]:
                bad.append(f"{src}/{l}(editing={editing}): {dom}")
            if l == "cache-trống":
                ctx2.close()
        ctx.close()
    record("F07", "xuất Final khi đang BẬT sửa chữ: HTML và DOM sau khi mở lại (có/không cache) đều 0 contenteditable/spellcheck/toolbar/nút điều khiển/link editor_*", not bad, " | ".join(bad))
    env.reset_work()


# ======================================================================= F09 toolbar
TOOLBAR_JS = r"""
() => {
  const t = document.getElementById('visual-toolbar') || document.getElementById('floating-toolbar');
  if (!t || t.classList.contains('hidden')) return {error: 'toolbar không hiện'};
  const vw = innerWidth, out = [];
  t.querySelectorAll('button, a, select').forEach((el) => {
    if (el.closest('#palette-menu') || el.closest('.hidden')) return;
    const r = el.getBoundingClientRect();
    if (!r.width) return;
    const cx = Math.min(Math.max(r.left + r.width / 2, 0), vw - 1), cy = r.top + r.height / 2;
    const hit = document.elementFromPoint(cx, cy);
    out.push({text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 28), left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width), h: Math.round(r.height),
              clipped: r.left < -0.5 || r.right > vw + 0.5, covered: !(hit && (el === hit || el.contains(hit)))});
  });
  const save = t.querySelector('#btn-save-final');
  return {items: out, hasSave: !!save, scrollW: document.documentElement.scrollWidth, vw};
}
"""


def t_f09(b, env, quick, shots):
    vps = VIEWPORTS if not quick else [(320, 568), (375, 812), (768, 1024), (1440, 900)]
    bad, n = [], 0
    for rel in (CREATOR_CV, CREATOR_PORTFOLIO, FINAL_CV, FINAL_PORTFOLIO):
        for (w, h) in vps:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = new_page(ctx)
            open_page(pg, env, rel)
            if rel in (FINAL_CV, FINAL_PORTFOLIO):
                pg.keyboard.press("Alt+e"); pg.wait_for_timeout(300)
            else:
                pg.wait_for_timeout(200)
            res = pg.evaluate(TOOLBAR_JS)
            n += 1
            if "error" in res:
                bad.append(f"{rel}@{w}: {res['error']}")
            else:
                if not res["hasSave"]:
                    bad.append(f"{rel}@{w}: không có nút Lưu file sạch")
                for it in res["items"]:
                    if it["clipped"] or it["covered"] or it["h"] < 24 or it["w"] < 24:
                        bad.append(f"{rel}@{w}: nút '{it['text']}' bị cắt/che/nhỏ {it}")
                if res["scrollW"] > res["vw"] + 1:
                    bad.append(f"{rel}@{w}: tràn ngang {res['scrollW']}>{res['vw']}")
            if shots and w == 375 and rel in (CREATOR_CV, CREATOR_PORTFOLIO):
                pg.evaluate("window.scrollTo(0,0)"); pg.screenshot(path=str(Path(shots) / f"F09-{Path(rel).stem}-375.png"))
            # nút Lưu thật sự bấm được và kích hoạt xuất
            if w in (375, 320) and rel in (CREATOR_CV, CREATOR_PORTFOLIO):
                env.reset_work()
                ctx2 = b.new_context(viewport={"width": w, "height": h}, accept_downloads=True)
                pg2 = new_page(ctx2)
                open_page(pg2, env, rel)
                try:
                    out = FINAL_CV if rel == CREATOR_CV else FINAL_PORTFOLIO
                    mtime_before = (env.work / out).stat().st_mtime_ns
                    click_save(pg2, 900)
                    # trạng thái thật: file trên đĩa đã đổi và có bản sao lưu (không dò chữ trong toast theo locale)
                    if (env.work / out).stat().st_mtime_ns == mtime_before or not list((env.work / ".w17_backups").glob(out + ".*.bak")):
                        bad.append(f"{rel}@{w}: bấm Lưu bằng chuột nhưng file không được ghi/không có backup")
                except Exception as exc:  # noqa
                    bad.append(f"{rel}@{w}: không bấm được nút Lưu ({exc})")
                ctx2.close()
                env.reset_work()
            ctx.close()
    record("F09", f"mọi nút toolbar (nhất là Lưu file sạch) nằm trong viewport, không bị che/cắt, đủ cỡ chạm, bấm Lưu thật ghi được ({n} tổ hợp trang x viewport)", not bad, " | ".join(bad[:6]))


def t_f09_keyboard(b, env):
    ctx = b.new_context(viewport={"width": 375, "height": 812})
    pg = new_page(ctx)
    open_page(pg, env, CREATOR_CV)
    seen_save = False
    for _ in range(25):
        pg.keyboard.press("Tab")
        info = pg.evaluate("() => { const a = document.activeElement; const r = a.getBoundingClientRect(); return {id: a.id, text: (a.textContent || '').trim().slice(0, 20), inView: r.left >= 0 && r.right <= innerWidth}; }")
        if "Lưu file sạch" in info["text"] and info["inView"]:
            seen_save = True
            focus_visible = pg.evaluate("() => { const c = getComputedStyle(document.activeElement); const o = c.outlineStyle !== 'none' && parseFloat(c.outlineWidth) > 0 && !/rgba\\(.*,\\s*0\\)$/.test(c.outlineColor); const s = c.boxShadow !== 'none' && !/rgba\\(0, 0, 0, 0\\)/.test(c.boxShadow.split(' ')[0]); return o || s; }")
            break
    record("F09", "bàn phím: Tab tới được nút 'Lưu file sạch (Final)' của Creator CV trên mobile 375px và nút có dấu hiệu focus nhìn thấy", seen_save and focus_visible)
    ctx.close()


# ======================================================================= F10 server
def t_f10(env):
    base = env.base
    host = base.replace("http://", "")
    ok_origin = {"Origin": base, "Host": host}
    sess_status, sess_headers, sess_body = http("GET", base + "/api/session", ok_origin)
    token = json.loads(sess_body).get("token") if sess_status == 200 else None
    good_html = (env.pristine / "index.html").read_text(encoding="utf-8")
    cv_html = (env.pristine / "index_portfolio_clean.html").read_text(encoding="utf-8")
    jhdr = {"Content-Type": "application/json", "Origin": base, "X-W17-Token": token or ""}
    bad = []

    def post(body, headers=None, raw=False):
        data = body if raw else json.dumps(body).encode("utf-8")
        h = dict(jhdr)
        h.update(headers or {})
        return http("POST", base + "/api/save", h, data)

    before = {n: sha(env.work / n) for n in ("index.html", "index_portfolio_clean.html", "server.py")}

    def untouched(label):
        for n, h in before.items():
            if sha(env.work / n) != h:
                bad.append(f"{label}: file {n} bị thay đổi")

    if not token:
        bad.append(f"không lấy được token cùng origin ({sess_status})")
    # nguồn gọi
    s, h, _ = http("GET", base + "/api/session", {"Origin": "http://evil.example", "Host": host})
    if s != 403 or any(k.lower().startswith("access-control") for k in h):
        bad.append(f"/api/session cho origin lạ: {s} {h}")
    s, h, _ = http("OPTIONS", base + "/api/save", {"Origin": "http://evil.example", "Access-Control-Request-Method": "POST", "Host": host})
    if any(k.lower().startswith("access-control") for k in h):
        bad.append(f"preflight vẫn trả CORS: {h}")
    s, h, _ = post({"html": "<html>PWN</html>", "targets": ["index.html"]}, {"Origin": "http://evil.example"})
    if s != 403:
        bad.append(f"POST origin lạ phải 403, nhận {s}")
    untouched("origin lạ")
    s, _, _ = post({"html": good_html, "targets": ["index.html"]}, {"X-W17-Token": "sai"})
    if s != 401:
        bad.append(f"POST sai token phải 401, nhận {s}")
    s, _, _ = http("POST", base + "/api/save", {"Content-Type": "application/json", "Origin": base}, json.dumps({"html": good_html, "targets": ["index.html"]}).encode())
    if s != 401:
        bad.append(f"POST thiếu token phải 401, nhận {s}")
    s, _, _ = http("POST", base + "/api/save", {"Content-Type": "text/plain", "Origin": "http://evil.example"}, b'{"html":"<html>x</html>","targets":["index.html"]}')
    if s not in (401, 403):
        bad.append(f"POST text/plain cross-origin phải bị chặn, nhận {s}")
    s, _, _ = post({"html": good_html, "targets": ["index.html"]}, {"Content-Type": "text/plain"})
    if s != 415:
        bad.append(f"Content-Type sai phải 415, nhận {s}")
    s, _, _ = post({"html": good_html, "targets": ["index.html"]}, {"Host": "evil.example"})
    if s != 403:
        bad.append(f"Host lạ phải 403, nhận {s}")
    untouched("xác thực")
    # giới hạn payload
    # Body quá lớn: server phải từ chối ngay từ Content-Length (413) mà không đọc/ghi gì
    with socket.create_connection(("127.0.0.1", env.port), timeout=10) as sock:
        crlf = bytes([13, 10])
        head_lines = [f"POST /api/save HTTP/1.1", f"Host: {host}", f"Origin: {base}", "Content-Type: application/json",
                      f"X-W17-Token: {token}", f"Content-Length: {200 * 1024 * 1024}", "Connection: close"]
        sock.sendall(crlf.join(x.encode() for x in head_lines) + crlf + crlf)
        status_line = sock.recv(4096).split(crlf, 1)[0].decode("latin-1")
    if " 413 " not in status_line:
        bad.append(f"khai báo body 200MB phải 413, nhận {status_line!r}")
    untouched("payload lớn")
    s, _, _ = post(b"not json", raw=True)
    if s != 400:
        bad.append(f"JSON hỏng phải 400, nhận {s}")
    # đích ghi
    for target in ["server.py", "../server.py", "..\\server.py", "editor_workspace/editor_cv.html", "index.html/../server.py", "INDEX.HTML", "", None, 7]:
        s, _, body = post({"html": good_html, "targets": [target]})
        if s != 400:
            bad.append(f"target {target!r} phải 400, nhận {s}")
    s, _, _ = post({"html": good_html, "filename": "server.py"})
    if s != 400:
        bad.append(f"filename=server.py phải 400, nhận {s}")
    untouched("đích ghi")
    # nội dung không hợp lệ
    for label, html in [("rỗng", ""), ("rác", "<html>PWNED</html>"), ("cắt cụt", good_html[: len(good_html) // 2]),
                        ("không phải trang này", "<!DOCTYPE html><html><body>x</body></html>"),
                        ("còn contenteditable", good_html.replace("<main", '<main contenteditable="true"', 1)),
                        ("còn toolbar", good_html.replace("<main", '<div id="visual-toolbar"></div><main', 1))]:
        s, _, _ = post({"html": html, "targets": ["index.html"]})
        if s not in (400, 422):
            bad.append(f"HTML {label} phải bị từ chối (400/422), nhận {s}")
    untouched("nội dung không hợp lệ")
    # đường thành công + trạng thái chính xác
    mod = good_html.replace("</title>", "</title><!-- f10-ok -->", 1)
    s, _, body = post({"html": mod, "targets": ["index.html"], "filename": "index.html"})
    resp = json.loads(body) if body else {}
    if s != 200 or resp.get("saved") != ["index.html"]:
        bad.append(f"ghi hợp lệ phải 200 + saved=['index.html'], nhận {s} {resp}")
    elif (env.work / "index.html").read_text(encoding="utf-8") != mod:
        bad.append("nội dung ghi ra không khớp payload")
    backups = list((env.work / ".w17_backups").glob("index.html.*.bak")) if (env.work / ".w17_backups").exists() else []
    if not backups:
        bad.append("không tạo backup bản cũ trước khi ghi")
    elif backups[0].read_text(encoding="utf-8") != good_html:
        bad.append("backup không phải bản cũ")
    leftovers = [p.name for p in env.work.glob("*.tmp")]
    if leftovers:
        bad.append(f"còn file tạm {leftovers}")
    s, _, body = post({"html": cv_html, "targets": ["index_portfolio_clean.html"]})
    if s != 200:
        bad.append(f"ghi CV phải 200, nhận {s}")
    # static: không phục vụ mã nguồn/thư mục ẩn
    for path in ["/server.py", "/dev_server.py", "/.git/config", "/.w17_backups/", "/fetch_ga4_bigquery.py"]:
        s, _, _ = http("GET", base + path, {"Host": host})
        if s not in (403, 404):
            bad.append(f"GET {path} phải bị chặn, nhận {s}")
    s, _, _ = http("GET", base + "/index.html", {"Host": host})
    if s != 200:
        bad.append("GET /index.html không còn hoạt động")
    record("F10", "server lưu file: chặn origin/Host/token lạ, Content-Type, payload quá lớn, JSON hỏng, đích ngoài allowlist, HTML không hợp lệ/rác/cắt cụt/còn editor; ghi nguyên tử + backup; trạng thái 2xx/4xx đúng; không phục vụ mã nguồn", not bad, " | ".join(bad[:8]))
    env.reset_work()
    shutil.rmtree(env.work / ".w17_backups", ignore_errors=True)


# ======================================================================= static content / overflow / nav
BADGES = {
    "vi": ["Cốt lõi • Trọn gói", "Cốt lõi • Dữ liệu & BI", "Hỗ trợ kỹ thuật • Beta", "MarOps • Không cam kết KPI"],
    "en": ["Core • End-to-End", "Core • Data & BI", "Tech Support • Beta", "MarOps • No KPI Commit"],
    "es": ["Núcleo • Integral", "Núcleo • Datos y BI", "Soporte técnico • Beta", "MarOps • Sin compromiso de KPI"],
    "zh": ["核心 • 全流程", "核心 • 数据与 BI", "技术支持 • Beta", "MarOps • 不承诺 KPI"],
}
SERVICE_TITLES = {
    "vi": [
        "1. Tự động hóa & Hệ thống Vận hành",
        "2. Báo cáo Quản trị & Dashboard BI",
        "3. Website Dịch vụ & Form Liên hệ",
        "4. Cài đặt & Kiểm tra GA4 / GTM"
    ],
    "en": [
        "1. Workflow Automation & Operations Systems",
        "2. Business Reporting & BI Dashboards",
        "3. Service Websites & Lead Capture Setup",
        "4. GA4 & GTM Setup, Audit & QA"
    ],
    "es": [
        "1. Automatización y Sistemas Operativos",
        "2. Informes de Gestión y Paneles BI",
        "3. Sitios de Servicios y Formularios",
        "4. Configuración y Auditoría GA4 / GTM"
    ],
    "zh": [
        "1. 流程自动化与运营系统",
        "2. 管理报告与 BI 看板",
        "3. 服务网站与联系表单",
        "4. GA4 / GTM 配置、审查与测试"
    ]
}
POSITIONING = {"vi": "Chuyên viên Tự động hóa Vận hành & Báo cáo Dữ liệu", "en": "Operations Automation & Data Reporting Specialist", "es": "Especialista en Automatización Operativa e Informes de Datos", "zh": "运营自动化与数据报告专员"}


def t_content(b, env):
    """Nội dung bắt buộc, kiểm theo DICTIONARY của từng locale (không còn ép giữ tiếng Anh ở mọi locale)."""
    bad = []
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    pg = new_page(ctx)
    for rel in (FINAL_PORTFOLIO, CREATOR_PORTFOLIO):
        open_page(pg, env, rel)
        for l in LOCALES:
            set_lang(pg, l)
            info = pg.evaluate("""() => ({
              badges: [...document.querySelectorAll('#ga4-ecosystem [data-i18n^=eco_badge_]')].map((e) => e.textContent.replace(/\\s+/g, ' ').trim()),
              titles: [1, 2, 3, 4].map((i) => document.querySelector('[data-i18n=eco_card' + i + '_title]').textContent.replace(/\\s+/g, ' ').trim()),
              cards: document.querySelectorAll('#ga4-ecosystem div[onclick*="is-editing"][onclick*="openGA4DrilldownModal"]').length,
              pbi: !!document.getElementById('pbi-ga4-dashboard'),
              apps: ['WRP Tax Services', 'Operation 0', 'TJ WordLoop', 'TJ Courses Hub'].map((n) => document.body.innerText.includes(n)),
              pos: document.querySelector('[data-i18n=hero_positioning]').textContent,
              nocommit: document.querySelector('[data-i18n=eco_card4_desc]').textContent.replace(/\\s+/g, ' ').includes(({vi: 'không cam kết doanh thu/lead', en: 'no revenue/lead KPI commitments', es: 'sin compromiso de ingresos/leads', zh: '不承诺获客或营收 KPI'})[document.documentElement.lang]),
              pkgs: document.querySelectorAll('#modal-service-packages [data-service-pkg]').length })""")
            pilot = pg.evaluate("""() => ({
                steps: document.querySelectorAll('#pilot ol > li').length,
                descriptions: [...document.querySelectorAll('#pilot [data-i18n]')].every(e => e.textContent.trim().length > 0),
                target: document.querySelector('#pilot a').getAttribute('href'),
                heroTarget: document.querySelector('[data-i18n=hero_btn_dashboard]').closest('a').getAttribute('href'),
                contact: !!document.getElementById('contact'),
                lineBreak: !!document.querySelector('[data-i18n=hero_title] br')
            })""")
            if pilot != dict(steps=3, descriptions=True, target="#contact", heroTarget="#contact", contact=True, lineBreak=True):
                bad.append(f"{rel}/{l}: pilot/navigation {pilot}")
            if info["badges"] != BADGES[l]:
                bad.append(f"{rel}/{l}: badge {info['badges']}")
            if info["titles"] != SERVICE_TITLES[l]:
                bad.append(f"{rel}/{l}: tên dịch vụ {info['titles']}")
            if POSITIONING[l] not in " ".join(info["pos"].split()):
                bad.append(f"{rel}/{l}: sai định vị {info['pos']!r}")
            if info["cards"] != 4 or not info["pbi"] or not all(info["apps"]) or info["pkgs"] != 4 or not info["nocommit"]:
                bad.append(f"{rel}/{l}: {info}")
    for rel in (FINAL_CV, CREATOR_CV):
        open_page(pg, env, rel)
        for l in LOCALES:
            set_lang(pg, l)
            t = pg.evaluate("document.querySelector('[data-i18n=hero_title]').textContent")
            if POSITIONING[l] not in " ".join(t.split()):
                bad.append(f"{rel}/{l}: sai định vị {t!r}")
    record("CONTENT", "định vị Operations Automation & Data Reporting Specialist (đã dịch theo từng locale), đúng 4 dịch vụ + badge theo dictionary, không cam kết KPI, khối Power BI Telemetry, bốn ứng dụng Proof of Work (Final+Creator, 4 locale)", not bad, " | ".join(bad[:6]))
    ctx.close()


def t_nav(b, env):
    bad = []
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    pg = new_page(ctx)
    for a, b_ in [(FINAL_PORTFOLIO, FINAL_CV), (CREATOR_PORTFOLIO, CREATOR_CV)]:
        for start, tgt in [(a, b_), (b_, a)]:
            open_page(pg, env, start)
            sel = {FINAL_CV: "a[href='./index_portfolio_clean.html']", FINAL_PORTFOLIO: "a[href='./index.html']",
                   CREATOR_CV: "a[href='./editor_cv.html']", CREATOR_PORTFOLIO: "a[href='./editor_portfolio.html']"}[tgt]
            link = pg.locator(sel).first
            link.scroll_into_view_if_needed()
            with pg.expect_navigation(timeout=8000):
                link.click()
            pg.wait_for_timeout(500)
            if not pg.url.endswith("/" + tgt):
                bad.append(f"{start} -> {tgt}: url={pg.url}")
    record("NAV", "điều hướng hai chiều index.html <-> index_portfolio_clean.html và editor_portfolio <-> editor_cv bằng click thật", not bad, " | ".join(bad))
    ctx.close()


def t_overflow(b, env, quick):
    vps = VIEWPORTS if not quick else [(320, 568), (375, 812), (390, 844), (1440, 900)]
    bad, n = [], 0
    for rel in ALL_PAGES:
        for (w, h) in vps:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = new_page(ctx)
            open_page(pg, env, rel, 500)
            for l in LOCALES:
                set_lang(pg, l)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                n += 1
                if sw > w + 1:
                    bad.append(f"{rel}@{w}/{l}: scrollWidth={sw}")
            ctx.close()
    record("RESP", f"không tràn ngang toàn trang ({n} tổ hợp trang x viewport x locale); không dùng overflow-x: hidden để che", not bad, " | ".join(bad[:6]))
    forbid = []
    import re
    for rel in ALL_PAGES:
        src = (REPO / rel).read_text(encoding="utf-8")
        if re.search(r"overflow-x:\s*hidden", src) or "overflow-x-hidden" in src:
            forbid.append(rel)
    record("RESP", "không còn overflow-x: hidden / overflow-x-hidden trong 4 file HTML", not forbid, ", ".join(forbid))


def t_static(env):
    bad = []
    r = subprocess.run([sys.executable, "-X", "utf8", str(REPO / "tools" / "sync_creators.py"), "--check"], capture_output=True, text=True)
    if r.returncode != 0:
        bad.append("Creator lệch Final: " + r.stdout.strip())
    for rel in ALL_PAGES:
        src = (REPO / rel).read_text(encoding="utf-8")
        for needle in ["'portfolio_lang'", "'portfolio_theme'", "\"portfolio_lang\"", "\"portfolio_theme\""]:
            if needle in src:
                bad.append(f"{rel}: còn {needle}")
        import re
        for m in re.finditer(r"localStorage\.removeItem\(([^)]*)\)", src):
            if "PALETTE" not in m.group(1):
                bad.append(f"{rel}: removeItem({m.group(1)})")
        if "forEach((k) => localStorage.removeItem" in src or "forEach((oldKey) => localStorage.removeItem" in src:
            bad.append(f"{rel}: còn vòng lặp xóa key cache")
    record("STATIC", "Creator đồng bộ Final (sync_creators --check); không còn khóa portfolio_*; không còn vòng lặp removeItem xóa cache", not bad, " | ".join(bad))


def snapshot_repo():
    names = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO, capture_output=True, text=True).stdout.splitlines()
    # Evidence output is expected to change during verification; application and test
    # sources are still hashed, including untracked files in a newly initialized repo.
    return {n: sha(REPO / n) for n in names if (REPO / n).is_file()
            and not n.startswith("docs/verification/")
            and n != "tests/regression/last_run.json"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=None)
    ap.add_argument("--only", default="")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    if args.shots:
        Path(args.shots).mkdir(parents=True, exist_ok=True)

    real_before = snapshot_repo()
    env = Env()
    env.prepare()
    env.start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            steps = [
                ("STATIC", lambda: t_static(env)),
                ("F01", lambda: t_f01(b, env)),
                ("F02", lambda: t_f02(b, env)),
                ("F04", lambda: (t_i18n(b, env), t_f04_cta(b, env))),
                ("F06", lambda: t_f06_cv(b, env)),
                ("F05", lambda: (t_f05(b, env), t_f05_migration(b, env), t_f05_nodes(b, env))),
                ("F03", lambda: (t_f03(b, env, args.quick, args.shots), t_f03_keyboard(b, env), X.t_f03_wheel(b, env))),
                ("F08", lambda: t_f08(b, env, args.quick, args.shots)),
                ("F09", lambda: (t_f09(b, env, args.quick, args.shots), t_f09_keyboard(b, env))),
                ("F07", lambda: (t_f07(b, env), t_f07_dom_scan(b, env))),
                ("F10", lambda: t_f10(env)),
                ("N", lambda: (X.t_n01_migration_cards(b, env), X.t_n02_duplicate_keys(b, env), X.t_n03_node_identity(b, env), X.t_n04_brand(b, env), X.t_server_extra(env))),
                ("R3", lambda: (X3.t_i18n_purity(b, env), X3.t_static_equals_vi(b, env), X3.t_ui_locale(b, env), X3.t_aria_meta(b, env), X3.t_n07_comment(env))),
                ("CONTENT", lambda: t_content(b, env)),
                ("NAV", lambda: t_nav(b, env)),
                ("RESP", lambda: t_overflow(b, env, args.quick)),
            ]
            for fid, fn in steps:
                if want(only, fid):
                    try:
                        fn()
                    except Exception as exc:  # một nhóm lỗi không che các nhóm khác
                        import traceback
                        record(fid, "nhóm kiểm thử gặp ngoại lệ", False, repr(exc) + " " + traceback.format_exc().splitlines()[-3].strip())
            b.close()
    finally:
        env.stop()
    real_after = snapshot_repo()
    record("SAFETY", "file làm việc thật không bị bộ kiểm thử ghi (hash trước = sau)", real_before == real_after)
    fails = [r for r in RESULTS if r[2] != "PASS"]
    print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS")
    out = REPO / "tests" / "regression" / "last_run.json"
    if args.shots or os.environ.get("W17_WRITE_LAST_RUN"):
        out.write_text(json.dumps([dict(id=r[0], name=r[1], status=r[2], detail=r[3]) for r in RESULTS], ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
