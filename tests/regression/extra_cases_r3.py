# -*- coding: utf-8 -*-
"""Audit vòng 3: độ thuần nhất ngôn ngữ, HTML tĩnh = VI, bản địa hóa editor, aria/metadata, N07 (marker trong comment)."""

import json
import re
import shutil

R = None  # run_all gán chính module đang chạy để dùng chung RESULTS/helper

# chỉ các chữ cái ĐẶC TRƯNG tiếng Việt (không gồm á é í ó ú ñ của tiếng Tây Ban Nha)
VN_LETTERS = "ăắằẳẵặâấầẩẫậđêếềểễệôốồổỗộơớờởỡợưứừửữựạảẹẻẽịỉĩọỏụủỳỷỹỵĂÂĐÊÔƠƯ"
DENY_RE = (r"\b(Users?|Views|Events|Sessions|Core Service|Tech Support|Support|Tracking|Landing|Rights|Showcase|Verified|Specialist|"
           r"Planning|Growth|Advanced|Automation|Master|Degree|Remote|Actual|Target|Self-[Ss]ervice|Workflow|Dispatch|Agents|Data Bar|"
           r"Validated|Property|Drill-down|Retention|Gamification|Engineering|Academy|Executive|Throughput|Multiple)\b|\b(users|views|events|sessions|reserved)\b")

DICT_JS = """() => { const d = (typeof translations !== 'undefined') ? translations : translationsCV; const o = {}; for (const l of ['vi','es','zh']) o[l] = d[l]; return o; }"""

TEXT_JS = r"""() => {
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const t = n.nodeValue.replace(/\s+/g, ' ').trim();
    const p = n.parentElement;
    if (!t || !p || p.closest('script, style, noscript, svg, .brand-title')) continue;
    out.push(t);
  }
  document.querySelectorAll('[aria-label], [title], [placeholder]').forEach((e) => ['aria-label', 'title', 'placeholder'].forEach((a) => { const v = e.getAttribute(a); if (v) out.push(v); }));
  return out;
}"""

STATIC_JS = r"""async (rel) => {
  const html = await (await fetch('/' + rel)).text();
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const norm = (s) => s.replace(/\s+/g, ' ').trim();
  const dict = (typeof translations !== 'undefined' ? translations : translationsCV);
  const probe = document.createElement('div');
  const out = [];
  doc.querySelectorAll('[data-i18n]').forEach((el) => {
    const k = el.getAttribute('data-i18n'); const v = dict.vi[k];
    if (v === undefined) { out.push(k + ': thiếu khóa VI'); return; }
    probe.innerHTML = v;
    if (norm(probe.textContent) !== norm(el.textContent)) out.push(k);
  });
  doc.querySelectorAll('[data-i18n-aria]').forEach((el) => { const k = el.getAttribute('data-i18n-aria'); if (dict.vi[k] !== undefined && dict.vi[k] !== el.getAttribute('aria-label')) out.push('aria:' + k); });
  return out;
}"""


def _deny_hits(strings):
    hits = []
    for s in strings:
        plain = re.sub(r"<[^>]+>", " ", s)
        m = re.search(DENY_RE, plain)
        if m:
            hits.append("%r in %r" % (m.group(0), plain[:70]))
    return hits


def t_i18n_purity(b, env):
    """Giá trị dịch + chữ hiển thị thật (3 tab GA4, 3 modal demo, tooltip/aria) không còn từ tiếng Anh thông dụng ở VI/ES/ZH."""
    bad = []
    for rel in (R.FINAL_PORTFOLIO, R.CREATOR_PORTFOLIO, R.FINAL_CV, R.CREATOR_CV):
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = R.new_page(ctx)
        R.open_page(pg, env, rel)
        d = pg.evaluate(DICT_JS)
        for l in ("vi", "es", "zh"):
            h = _deny_hits(d[l].values())
            if h:
                bad.append("%s dict/%s: %s" % (rel, l, h[:3]))
        is_portfolio = rel in (R.FINAL_PORTFOLIO, R.CREATOR_PORTFOLIO)
        for l in ("vi", "es", "zh"):
            R.set_lang(pg, l)
            texts = list(pg.evaluate(TEXT_JS))
            if is_portfolio:
                for tab in ("countries", "pages", "powerbi"):
                    pg.evaluate("openGA4DrilldownModal('%s')" % tab)
                    pg.wait_for_timeout(450)
                    texts += pg.evaluate(TEXT_JS)
                    pg.evaluate("closeGA4DrilldownModal()")
            else:
                for m in ("planning", "bi", "automation"):
                    pg.evaluate("openSolutionModal('%s')" % m)
                    pg.wait_for_timeout(350)
                    texts += pg.evaluate(TEXT_JS)
                    pg.evaluate("closeSolutionModal()")
            h = _deny_hits(texts)
            if h:
                bad.append("%s DOM/%s: %s" % (rel, l, sorted(set(h))[:4]))
        ctx.close()
    R.record("R3-01..05", "độ thuần nhất ngôn ngữ: không còn từ tiếng Anh thông dụng (Users/Views/Events/Core Service/Verified/Master Degree/Actual vs. Target/Self-service/Auto-Dispatch...) trong từ điển và chữ hiển thị thật ở VI/ES/ZH (4 trang, 3 tab GA4, 3 modal demo, tooltip/aria)", not bad, " | ".join(bad[:6]))


def t_static_equals_vi(b, env):
    """HTML tĩnh (mặc định, trước khi JS chạy) trùng bản VI: không nháy chữ khi tải trang."""
    bad = []
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    pg = R.new_page(ctx)
    for rel in (R.FINAL_PORTFOLIO, R.CREATOR_PORTFOLIO, R.FINAL_CV, R.CREATOR_CV):
        R.open_page(pg, env, rel)
        res = pg.evaluate(STATIC_JS, rel)
        if res:
            bad.append("%s: %s" % (rel, res[:6]))
    R.record("R3-06", "HTML tĩnh khớp từ điển VI cho mọi data-i18n và data-i18n-aria (4 file), không còn lệch nguồn → DOM", not bad, " | ".join(bad[:4]))
    ctx.close()


def t_ui_locale(b, env):
    """Toolbar/toast/confirm của editor theo 4 locale: không còn chữ Việt ở EN/ES/ZH; đổi locale cập nhật toolbar ngay."""
    bad = []
    vn = re.compile("[%s]" % VN_LETTERS)
    for rel, ui_name in [(R.CREATOR_PORTFOLIO, "W17_UI"), (R.CREATOR_CV, "UI_CV")]:
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = R.new_page(ctx)
        R.open_page(pg, env, rel)
        ui = pg.evaluate(ui_name)
        for key, per in ui.items():
            for l in ("vi", "en", "es", "zh"):
                if not per.get(l):
                    bad.append("%s: thiếu %s/%s" % (rel, key, l))
            for l in ("en", "es", "zh"):
                if vn.search(per.get(l, "")):
                    bad.append("%s: %s/%s còn chữ Việt" % (rel, key, l))
        for l in ("en", "es", "zh"):
            R.set_lang(pg, l)
            txt = pg.evaluate("""() => { const t = document.getElementById('visual-toolbar') || document.getElementById('floating-toolbar');
                return [...t.querySelectorAll('button, a, span, div')].filter((e) => !e.children.length && !e.closest('.brand-title')).map((e) => e.textContent.trim()).filter(Boolean)
                  .concat([...t.querySelectorAll('[title],[aria-label]')].map((e) => e.getAttribute('title') || e.getAttribute('aria-label'))); }""")
            hits = [x for x in txt if vn.search(x)]
            if hits:
                bad.append("%s/%s: toolbar còn chữ Việt %s" % (rel, l, hits[:3]))
        R.set_lang(pg, "es")
        pg.click("#btn-toggle-edit")
        pg.wait_for_timeout(250)
        label = pg.evaluate("document.querySelector('#btn-edit-text, #btn-edit-label').textContent.trim()")
        toast = pg.evaluate("document.getElementById('toast-notification').textContent")
        if vn.search(label) or vn.search(toast):
            bad.append("%s/es: nhãn/toast sau khi bật sửa còn chữ Việt (%r, %r)" % (rel, label, toast))
        R.set_lang(pg, "zh")
        label2 = pg.evaluate("document.querySelector('#btn-edit-text, #btn-edit-label').textContent.trim()")
        if label2 == label:
            bad.append("%s: nhãn nút không đổi khi chuyển es→zh (%r)" % (rel, label2))
        ctx.close()
    R.record("R3-08", "Creator/editor bản địa hóa: toolbar, nhãn bật/tắt, toast không còn chữ Việt ở EN/ES/ZH và cập nhật ngay khi đổi ngôn ngữ (đủ khóa ở 4 locale)", not bad, " | ".join(bad[:6]))


def t_aria_meta(b, env):
    """Accessible names và metadata theo locale (R3-07)."""
    bad = []
    vn = re.compile("[%s]" % VN_LETTERS)
    for rel in (R.FINAL_PORTFOLIO, R.FINAL_CV):
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = R.new_page(ctx)
        R.open_page(pg, env, rel)
        titles = {}
        for l in ("vi", "en", "es", "zh"):
            R.set_lang(pg, l)
            titles[l] = pg.evaluate("document.title")
        if len(set(titles.values())) != 4:
            bad.append("%s: <title> không đổi theo locale %s" % (rel, titles))
        if rel == R.FINAL_PORTFOLIO:
            for l in ("vi", "en", "es", "zh"):
                R.set_lang(pg, l)
                desc = pg.evaluate("document.querySelector('meta[name=description]').getAttribute('content')")
                ogt = pg.evaluate("document.querySelector('meta[property=\"og:title\"]').getAttribute('content')")
                if "Performance Marketer" in desc or (l != "vi" and vn.search(desc)) or ogt != titles[l]:
                    bad.append("%s/%s: metadata sai (%r, og:title khớp title=%s)" % (rel, l, desc[:50], ogt == titles[l]))
            for l in ("es", "zh"):
                R.set_lang(pg, l)
                names = pg.evaluate("[...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label'))")
                english = ("Select Date Range", "Country Telemetry Filter", "GA4 Drill-down Views", "Modal Country Filter")
                if any(vn.search(n) for n in names) or any(n in english for n in names):
                    bad.append("%s/%s: aria-label chưa theo locale" % (rel, l))
        ctx.close()
    R.record("R3-07", "accessible names (aria-label) và <title>/description/og:title đổi theo locale; metadata không còn định vị Performance Marketer cũ", not bad, " | ".join(bad[:5]))


def t_n07_comment(env):
    """N07: marker chỉ nằm trong comment / chuỗi script / sai thẻ / trùng id phải bị từ chối; trang thật vẫn ghi được."""
    base = env.base
    host = base.replace("http://", "")
    st, _, body = R.http("GET", base + "/api/session", {"Origin": base, "Host": host})
    token = json.loads(body)["token"]
    hdr = {"Content-Type": "application/json", "Origin": base, "X-W17-Token": token}
    ids = ["main-navbar", "ga4-ecosystem", "pbi-ga4-dashboard", "core-portfolio-script", "visual-editor-script", "w17-baked-edits", "ga4-drilldown-modal"]
    pad = "x" * 200000
    good = (env.pristine / "index.html").read_text(encoding="utf-8")
    cases = {
        "all-ids-in-comment": "<!doctype html><html><body><!-- " + " ".join('id="%s"' % i for i in ids) + " -->" + pad + "</body></html>",
        "ids-in-script-string": "<!doctype html><html><body><script>var s = '" + " ".join('id=%s' % i for i in ids) + "';</script>" + pad + "</body></html>",
        "ids-on-wrong-tags": "<!doctype html><html><body>" + "".join('<p id="%s">x</p>' % i for i in ids) + pad + "</body></html>",
        "duplicate-ids": good.replace("</body>", '<div id="ga4-ecosystem"></div></body>', 1),
    }
    bad = []
    for label, html in cases.items():
        s, _, _ = R.http("POST", base + "/api/save", hdr, json.dumps({"html": html, "targets": ["index.html"]}).encode())
        if s not in (400, 422):
            bad.append("%s: nhận %s, phải bị từ chối" % (label, s))
    s, _, _ = R.http("POST", base + "/api/save", hdr, json.dumps({"html": good, "targets": ["index.html"]}).encode())
    if s != 200:
        bad.append("trang thật phải 200, nhận %s" % s)
    R.record("N07", "validator đọc CÂY HTML đã parse: marker trong comment/chuỗi script, sai thẻ, trùng id đều bị từ chối; trang thật vẫn ghi được", not bad, " | ".join(bad))
    env.reset_work()
    shutil.rmtree(env.work / ".w17_backups", ignore_errors=True)
