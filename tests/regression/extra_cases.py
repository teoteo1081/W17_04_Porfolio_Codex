# -*- coding: utf-8 -*-
"""Ca kiểm thử bổ sung sau audit độc lập lần 2 (N01–N08). Được run_all.py gọi, dùng chung helper."""

import json
import gzip
import threading
import urllib.error
import urllib.request

R = None  # run_all gán chính module đang chạy để dùng chung RESULTS/helper

def _legacy(env, rel):
    fixtures = json.loads(gzip.decompress((R.REPO / "tests/fixtures/legacy_creators.json.gz").read_bytes()))
    data = fixtures[rel].encode("utf-8")
    name = "legacy_" + R.Path(rel).name
    (env.work / "editor_workspace" / name).write_bytes(data)
    return name


def _drop_legacy(env, name):
    try:
        (env.work / "editor_workspace" / name).unlink()
    except OSError:
        pass


def t_n01_migration_cards(b, env):
    """Migration CV: thẻ đã xóa trong Creator CŨ không được sống lại, thẻ còn lại không bị loại nhầm (4 locale)."""
    name = _legacy(env, R.CREATOR_CV)
    bad = []
    try:
        for lang in R.LOCALES:
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            pg = R.new_page(ctx)
            pg.goto(f"{env.base}/editor_workspace/{name}"); pg.wait_for_timeout(700)
            pg.evaluate(R.SELECT_LANG_JS, lang); pg.wait_for_timeout(200)
            pg.evaluate("toggleEditMode()"); pg.wait_for_timeout(150)
            pg.evaluate("""() => { const b = document.querySelector('.solution-card-item .delete-btn'); b.click();
                                   document.body.dispatchEvent(new Event('input', {bubbles: true})); }""")
            pg.wait_for_timeout(250)
            keys_legacy = pg.evaluate("[...document.querySelectorAll('.solution-card-item')].map((c) => (c.querySelector('[data-i18n^=sol_card]') || {getAttribute: () => null}).getAttribute('data-i18n'))")
            store = pg.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
            ctx.close()
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            pg = R.new_page(ctx)
            pg.goto(f"{env.base}/{R.FINAL_PORTFOLIO}"); pg.wait_for_timeout(200)
            pg.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", store)
            R.open_page(pg, env, R.CREATOR_CV)
            keys_new = pg.evaluate("[...document.querySelectorAll('.solution-card-item')].map((c) => (c.querySelector('[data-i18n^=sol_card]') || {getAttribute: () => null}).getAttribute('data-i18n'))")
            if keys_new != keys_legacy or len(keys_legacy) != 2:
                bad.append(f"{lang}: cũ={keys_legacy} mới={keys_new}")
            ctx.close()
    finally:
        _drop_legacy(env, name)
    R.record("N01", "migration CV: thẻ giải pháp đã xóa ở Creator cũ không sống lại, thẻ còn lại giữ đúng (4 locale)", not bad, " | ".join(bad))


def t_n02_duplicate_keys(b, env):
    """Hai node cùng khóa i18n (nav desktop/mobile): sửa một node không bị node kia xóa; sống sót qua reload và xuất Final."""
    bad = []
    for src, out in [(R.CREATOR_PORTFOLIO, R.FINAL_PORTFOLIO), (R.FINAL_PORTFOLIO, R.FINAL_PORTFOLIO)]:
        env.reset_work()
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        pg = R.new_page(ctx)
        R.open_page(pg, env, src)
        if not pg.evaluate("document.body.classList.contains('is-editing')"):
            if src == R.FINAL_PORTFOLIO:
                pg.keyboard.press("Alt+e")
            else:
                pg.click("#btn-toggle-edit")
            pg.wait_for_timeout(250)
        n = pg.evaluate("document.querySelectorAll('[data-i18n=nav_about]').length")
        pg.evaluate("""() => { const e = document.querySelector('[data-i18n=nav_about]'); e.textContent = 'CUSTOM-NAV';
                              e.dispatchEvent(new Event('input', {bubbles: true})); }""")
        pg.wait_for_timeout(250)
        cache = pg.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
        pg.reload(); pg.wait_for_timeout(700)
        texts = pg.evaluate("[...document.querySelectorAll('[data-i18n=nav_about]')].map((e) => e.textContent.trim())")
        if n < 2 or "CUSTOM-NAV" not in texts or any(t != "CUSTOM-NAV" for t in texts):
            bad.append(f"{src}: sau reload {texts} (số node {n})")
        if src == R.FINAL_PORTFOLIO:
            pg.keyboard.press("Alt+e"); pg.wait_for_timeout(300)  # Final: toolbar chỉ có sau Alt+E (trang vừa tải lại)
        R.click_save(pg)
        for label, init in (("cache-trống", None), ("cache-có-dữ-liệu", cache)):
            ctx2 = b.new_context(viewport={"width": 1440, "height": 900})
            pg2 = R.new_page(ctx2)
            if init is not None:
                pg2.goto(f"{env.base}/{R.FINAL_CV}"); pg2.wait_for_timeout(200)
                pg2.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", init)
            R.open_page(pg2, env, out)
            texts = pg2.evaluate("[...document.querySelectorAll('[data-i18n=nav_about]')].map((e) => e.textContent.trim())")
            if "CUSTOM-NAV" not in texts:
                bad.append(f"{src}/{label}: bản xuất mất chỉnh sửa {texts}")
            ctx2.close()
        ctx.close()
    env.reset_work()
    R.record("N02", "node trùng khóa i18n (nav desktop/mobile): chỉnh sửa không bị xóa; còn sau reload và khi xuất Final (cache trống/có cache)", not bad, " | ".join(bad))


def t_n03_node_identity(b, env):
    """Node không-i18n có văn bản trùng (dấu ✓) + kéo thẻ + xuất: chỉnh sửa chỉ ở đúng node, không nhân sang thẻ khác."""
    bad = []
    for src in (R.CREATOR_CV, R.FINAL_CV):
        env.reset_work()
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        pg = R.new_page(ctx)
        R.open_page(pg, env, src)
        if not pg.evaluate("document.body.classList.contains('is-editing')"):
            if src == R.FINAL_CV:
                pg.keyboard.press("Alt+e")
            else:
                pg.click("#btn-toggle-edit")
            pg.wait_for_timeout(250)
        marked = pg.evaluate("""() => {
          const card = document.querySelectorAll('.solution-card-item')[0];
          const leaf = [...card.querySelectorAll('span')].filter((s) => !s.children.length && s.textContent.trim() === '✓');
          if (!leaf.length) return 0;
          leaf[0].textContent = 'CHECK-CUSTOM'; leaf[0].dispatchEvent(new Event('input', {bubbles: true}));
          document.body.dispatchEvent(new Event('input', {bubbles: true}));
          return leaf.length;
        }""")
        pg.wait_for_timeout(200)
        pg.evaluate("""() => { const g = document.getElementById('solutions-grid'); g.insertBefore(g.children[1], g.children[0]); saveCurrentState(); }""")
        pg.wait_for_timeout(200)
        cache = pg.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
        R.click_save(pg)
        out = R.FINAL_CV
        # xác định card chứa CHECK-CUSTOM trước/sau theo data-card-id
        def holders(page):
            return page.evaluate("""() => [...document.querySelectorAll('.solution-card-item')].filter((c) => c.textContent.includes('CHECK-CUSTOM')).map((c) => c.getAttribute('data-card-id'))""")
        before = pg.evaluate("[...document.querySelectorAll('.solution-card-item')].filter((c) => c.textContent.includes('CHECK-CUSTOM')).map((c) => c.getAttribute('data-card-id'))")
        count_before = pg.evaluate("[...document.querySelectorAll('span')].filter((s) => s.textContent === 'CHECK-CUSTOM').length")
        for label, init in (("cache-trống", None), ("cache-có-dữ-liệu", cache)):
            ctx2 = b.new_context(viewport={"width": 1280, "height": 900})
            pg2 = R.new_page(ctx2)
            if init is not None:
                pg2.goto(f"{env.base}/{R.FINAL_PORTFOLIO}"); pg2.wait_for_timeout(200)
                pg2.evaluate("(d) => Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v))", init)
            R.open_page(pg2, env, out)
            after = holders(pg2)
            count_after = pg2.evaluate("[...document.querySelectorAll('span')].filter((s) => s.textContent === 'CHECK-CUSTOM').length")
            if marked < 2 or after != before or count_after != count_before or count_after != 1:
                bad.append(f"{src}/{label}: trước={before}/{count_before} sau={after}/{count_after} (node ✓ trong thẻ: {marked})")
            ctx2.close()
        ctx.close()
    env.reset_work()
    R.record("N03", "kéo thẻ + xuất Final khi có nhiều node cùng văn bản '✓': chỉnh sửa chỉ ở đúng node, không nhân sang thẻ khác (cache trống/có cache)", not bad, " | ".join(bad))


def t_n04_brand(b, env):
    """Brand trên toolbar Creator được lưu sau khi sửa và khôi phục khi tải lại (CV và portfolio)."""
    bad = []
    for rel, sel in [(R.CREATOR_CV, "#floating-toolbar .brand-title"), (R.CREATOR_PORTFOLIO, "#visual-toolbar .brand-title")]:
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = R.new_page(ctx)
        R.open_page(pg, env, rel)
        pg.click("#btn-toggle-edit"); pg.wait_for_timeout(250)
        ok = pg.evaluate("""(sel) => { const n = [...document.querySelectorAll(sel)].find((e) => !e.children.length);
            if (!n) return false; n.textContent = 'CUSTOM-BRAND'; n.dispatchEvent(new Event('input', {bubbles: true}));
            document.body.dispatchEvent(new Event('input', {bubbles: true})); return true; }""", sel)
        pg.wait_for_timeout(250)
        R.open_page(pg, env, rel)
        has = pg.evaluate("(sel) => [...document.querySelectorAll(sel)].some((e) => e.textContent.trim() === 'CUSTOM-BRAND')", sel)
        if not ok or not has:
            bad.append(f"{rel}: brand không được lưu (sửa được={ok}, còn sau reload={has})")
        ctx.close()
    R.record("N04", "brand trên toolbar Creator (CV và portfolio) được lưu và còn sau khi tải lại", not bad, " | ".join(bad))


def t_server_extra(env):
    base = env.base
    host = base.replace("http://", "")
    bad = []
    # N05: static bị vượt bằng percent-encoding
    for path in ["/server%2epy", "/server%2Epy", "/%73erver.py", "/%2egit/config", "/%2Ew17_backups/", "/%2e%2e/server.py",
                 "/..%2fserver.py", "/%252e%252egit/config", "/dev_server%2epy", "/fetch_ga4_bigquery%2Epy", "/editor_workspace/%2e%2e/server.py"]:
        s, _, body = R.http("GET", base + path, {"Host": host})
        if s == 200 or b"BASE_DIR" in body:
            bad.append(f"N05 GET {path} -> {s}")
        s2, _, _ = R.http("HEAD", base + path, {"Host": host})
        if s2 == 200:
            bad.append(f"N05 HEAD {path} -> {s2}")
    for path in ["/index.html", "/index_portfolio_clean.html", "/editor_workspace/editor_cv.html"]:
        s, _, _ = R.http("GET", base + path, {"Host": host})
        if s != 200:
            bad.append(f"N05 GET {path} (hợp lệ) -> {s}")
    st, _, body = R.http("GET", base + "/api/session", {"Origin": base, "Host": host})
    token = json.loads(body)["token"]
    hdr = {"Content-Type": "application/json", "Origin": base, "X-W17-Token": token}
    good_p = (env.pristine / "index.html").read_text(encoding="utf-8")
    good_c = (env.pristine / "index_portfolio_clean.html").read_text(encoding="utf-8")
    # N07: HTML rác chỉ chứa marker
    for label, name, html in [("marker-portfolio", "index.html", '<!doctype html><html><body><section id="ga4-ecosystem">JUNK</section></body></html>'),
                              ("marker-cv", "index_portfolio_clean.html", '<!doctype html><html><body><main id="portfolio-root">JUNK</main></body></html>'),
                              ("nửa-file", "index.html", good_p[: int(len(good_p) * 0.6)] + "</html>"),
                              ("thiếu-editor-script", "index.html", good_p.replace('id="visual-editor-script"', 'id="x"')),
                              ("thiếu-baked", "index_portfolio_clean.html", good_c.replace('id="w17-baked-edits"', 'id="x"'))]:
        s, _, _ = R.http("POST", base + "/api/save", hdr, json.dumps({"html": html, "targets": [name]}).encode())
        if s not in (400, 422):
            bad.append(f"N07 {label}: nhận {s}, phải bị từ chối")
    s, _, _ = R.http("POST", base + "/api/save", hdr, json.dumps({"html": good_p, "targets": ["index.html"]}).encode())
    if s != 200:
        bad.append(f"N07 bản hợp lệ phải 200, nhận {s}")
    # N06: ghi đồng thời
    codes, errors = [], []

    def writer(name, html):
        for _ in range(10):
            try:
                s, _, _ = R.http("POST", base + "/api/save", hdr, json.dumps({"html": html, "targets": [name]}).encode())
                codes.append(s)
            except Exception as exc:  # noqa
                errors.append(repr(exc))
    stop = threading.Event()
    reads = {"ok": 0, "bad": 0}

    def reader():
        while not stop.is_set():
            try:
                s, _, body = R.http("GET", base + "/index.html", {"Host": host})
                if s == 200 and body.rstrip().endswith(b"</html>"):
                    reads["ok"] += 1
                else:
                    reads["bad"] += 1
                    reads.setdefault("why", []).append(f"status={s} len={len(body)}")
            except Exception as exc:  # noqa
                reads["bad"] += 1
                reads.setdefault("why", []).append(repr(exc)[:80])
    threads = [threading.Thread(target=writer, args=("index.html", good_p)) for _ in range(3)] + \
              [threading.Thread(target=writer, args=("index_portfolio_clean.html", good_c)) for _ in range(2)]
    rd = threading.Thread(target=reader)
    rd.start(); [t.start() for t in threads]; [t.join() for t in threads]; stop.set(); rd.join()
    if any(c != 200 for c in codes) or errors:
        bad.append(f"N06 ghi đồng thời: {dict((c, codes.count(c)) for c in set(codes))} lỗi={errors[:2]}")
    if reads["bad"]:
        bad.append(f"N06 reader gặp trạng thái hỏng/lỗi {reads}")
    if (env.work / "index.html").read_text(encoding="utf-8") != good_p:
        bad.append("N06 nội dung cuối không khớp payload")
    names = [p.name for p in (env.work / ".w17_backups").glob("*.bak")] if (env.work / ".w17_backups").exists() else []
    if len(names) != len(set(names)):
        bad.append("N06 trùng tên backup")
    # N08: body quá lớn gửi thật (không chỉ khai báo header)
    big = b'{"html":"' + b"A" * (13 * 1024 * 1024) + b'"}'
    try:
        s, _, _ = R.http("POST", base + "/api/save", hdr, big)
        if s != 413:
            bad.append(f"N08 body 13MB thật phải 413, nhận {s}")
    except Exception as exc:  # noqa
        bad.append(f"N08 body 13MB thật: client không nhận được mã trạng thái ({exc!r})")
    R.record("F10+", "server (audit lần 2): static không bị vượt bằng percent-encoding (N05); ghi đồng thời + reader an toàn, không 500, backup không trùng (N06); HTML rác/nửa file/thiếu thành phần bị từ chối (N07); body quá lớn gửi thật nhận 413 (N08)", not bad, " | ".join(bad[:8]))
    env.reset_work()
    import shutil
    shutil.rmtree(env.work / ".w17_backups", ignore_errors=True)


SCROLLER_JS = """() => {
  const dlg = document.getElementById('ga4-modal-dialog'), body = document.getElementById('ga4-modal-body');
  const sc = (getComputedStyle(body).overflowY !== 'visible' && body.scrollHeight > body.clientHeight + 1) ? body : dlg;
  const r = sc.getBoundingClientRect();
  return {x: r.left + r.width / 2, y: Math.max(r.top, 0) + Math.min(r.height, innerHeight) / 2, top: sc.scrollTop};
}"""

VISIBLE_ITEMS_JS = """() => {
  const dlg = document.getElementById('ga4-modal-dialog'), body = document.getElementById('ga4-modal-body');
  const sc = (getComputedStyle(body).overflowY !== 'visible' && body.scrollHeight > body.clientHeight + 1) ? body : dlg;
  const sr = sc.getBoundingClientRect();
  const lo = Math.max(sr.top, 0), hi = Math.min(sr.bottom, innerHeight);
  return [...document.querySelectorAll('#modal-service-packages li')].map((li, i) => { const r = li.getBoundingClientRect(); return (r.top >= lo - 1 && r.bottom <= hi + 1) ? i : -1; }).filter((i) => i >= 0);
}"""


def t_f03_wheel(b, env):
    """Cuộn bằng bánh xe chuột thật (mouse.wheel): mọi đầu việc phải xuất hiện đầy đủ trong vùng nhìn thấy khi người dùng cuộn."""
    bad = []
    for rel in (R.FINAL_PORTFOLIO, R.CREATOR_PORTFOLIO):
        for (w, h) in [(320, 568), (375, 812), (390, 844), (720, 450)]:
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = R.new_page(ctx)
            R.open_page(pg, env, rel)
            btn = pg.locator("#ga4-ecosystem button[aria-controls='ga4-drilldown-modal']").nth(0)
            btn.scroll_into_view_if_needed(); btn.click(); pg.wait_for_timeout(800)
            pos = pg.evaluate(SCROLLER_JS)
            pg.mouse.move(pos["x"], pos["y"])
            pg.mouse.wheel(0, -5000); pg.wait_for_timeout(250)
            seen, moved = set(), False
            last_top = pg.evaluate(SCROLLER_JS)["top"]
            for _ in range(60):
                seen.update(pg.evaluate(VISIBLE_ITEMS_JS))
                pg.mouse.wheel(0, 120); pg.wait_for_timeout(90)
                cur = pg.evaluate(SCROLLER_JS)["top"]
                moved = moved or cur != last_top
                if len(seen) == 12 and cur == last_top:
                    break
                last_top = cur
            seen.update(pg.evaluate(VISIBLE_ITEMS_JS))
            if not moved or len(seen) != 12:
                bad.append(f"{rel}@{w}x{h}: wheel cuộn={moved}, đầu việc từng thấy trọn={len(seen)}/12")
            ctx.close()
    R.record("F03", "cuộn bằng bánh xe chuột thật (mouse.wheel) đưa đủ 12 đầu việc vào vùng nhìn thấy (2 trang × 4 viewport thấp/mobile)", not bad, " | ".join(bad))
