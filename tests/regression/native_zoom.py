#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiểm tra ở mức zoom TRÌNH DUYỆT 200% (native), không phải emulation viewport/DPR.

Cách làm: ghi mức zoom mặc định của Chromium vào Preferences của một profile tạm
(partition.default_zoom_level = log(2)/log(1.2) ≈ 3.8018, tức 200%), rồi mở bằng launch_persistent_context với
viewport=None (không emulation). Bằng chứng native: window.innerWidth ≈ outerWidth/2 và devicePixelRatio = 2 mà KHÔNG
dùng set_viewport_size / device_scale_factor.

Nếu trình duyệt không áp dụng zoom (innerWidth không giảm một nửa) thì bài kiểm tra báo FAIL/INCONCLUSIVE chứ không PASS.
"""

import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_all as R  # noqa: E402

ZOOM_LEVEL = math.log(2.0) / math.log(1.2)


def launch(p, profile, width=1280, height=900):
    default = Path(profile) / "Default"
    default.mkdir(parents=True, exist_ok=True)
    prefs = {"partition": {"default_zoom_level": {"x": ZOOM_LEVEL}}}
    (default / "Preferences").write_text(json.dumps(prefs), encoding="utf-8")
    return p.chromium.launch_persistent_context(
        str(profile), channel="chromium", headless=True, viewport=None,
        args=[f"--window-size={width},{height}", "--hide-scrollbars"],
    )


def main():
    shots = sys.argv[1] if len(sys.argv) > 1 else None
    if shots:
        Path(shots).mkdir(parents=True, exist_ok=True)
    env = R.Env()
    env.prepare()
    env.start()
    profile = tempfile.mkdtemp(prefix="w17_zoom_profile_")
    try:
        with sync_playwright() as p:
            ctx = launch(p, profile)
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            R.open_page(pg, env, R.FINAL_PORTFOLIO)
            info = pg.evaluate("() => ({iw: innerWidth, ow: outerWidth, ih: innerHeight, dpr: devicePixelRatio})")
            native = info["dpr"] >= 1.99 and info["iw"] <= info["ow"] * 0.55
            R.record("ZOOM", f"zoom native 200% được áp dụng (không emulation): innerWidth={info['iw']} outerWidth={info['ow']} dpr={info['dpr']}", native, json.dumps(info))
            if not native:
                ctx.close()
                print("INCONCLUSIVE: trình duyệt không áp dụng zoom từ Preferences; không đánh giá tiếp ở zoom 200%.")
                sys.exit(2)

            bad = []
            for rel in R.ALL_PAGES:
                for lang in R.LOCALES:
                    pg2 = ctx.new_page()
                    R.open_page(pg2, env, rel)
                    R.set_lang(pg2, lang)
                    sw = pg2.evaluate("() => [document.documentElement.scrollWidth, innerWidth]")
                    if sw[0] > sw[1] + 1:
                        bad.append(f"{rel}/{lang}: tràn ngang {sw}")
                    orphans = pg2.evaluate(R.ORPHAN_JS)
                    for item in orphans["bad"]:
                        bad.append(f"{rel}/{lang}: {item}")
                    if rel in (R.FINAL_CV, R.FINAL_PORTFOLIO):
                        pg2.keyboard.press("Alt+e"); pg2.wait_for_timeout(300)
                    tb = pg2.evaluate(R.TOOLBAR_JS)
                    if "error" in tb or not tb.get("hasSave") or any(i["clipped"] or i["covered"] for i in tb["items"]):
                        bad.append(f"{rel}/{lang}: toolbar {tb if 'error' in tb else [i for i in tb['items'] if i['clipped'] or i['covered']]}")
                    pg2.close()
            R.record("ZOOM", "zoom native 200%: không tràn ngang, không orphan, toolbar (kể cả nút Lưu) không bị cắt/che — 4 trang x 4 locale", not bad, " | ".join(bad[:6]))

            bad = []
            for rel in (R.FINAL_PORTFOLIO, R.CREATOR_PORTFOLIO):
                pg2 = ctx.new_page()
                R.open_page(pg2, env, rel)
                for lang in R.LOCALES:
                    R.set_lang(pg2, lang)
                    for svc, idx in [("p1", 0), ("p2", 1), ("p3", 2), ("p4", 3)]:
                        btn = pg2.locator("#ga4-ecosystem button[aria-controls='ga4-drilldown-modal']").nth(idx)
                        btn.scroll_into_view_if_needed()
                        btn.click()
                        pg2.wait_for_timeout(750)
                        r = R.modal_probe(pg2, svc)
                        inside = r["tTop"] >= r["sTop"] - 1 and r["tTop"] < min(r["sBot"], r["vh"])
                        if not (r["inScroll"] and inside):
                            bad.append(f"{rel}/{lang}/{svc}: {r}")
                        if lang == "vi" and svc == "p4" and shots and rel == R.FINAL_PORTFOLIO:
                            pg2.screenshot(path=str(Path(shots) / "ZOOM200-native-modal.png"))
                        pg2.keyboard.press("Escape"); pg2.wait_for_timeout(120)
                pg2.close()
            R.record("ZOOM", "zoom native 200%: modal đưa đúng nhóm dịch vụ vào vùng nhìn thấy (2 trang x 4 locale x 4 thẻ)", not bad, " | ".join(bad[:4]))
            if shots:
                pg3 = ctx.new_page()
                R.open_page(pg3, env, R.CREATOR_CV)
                pg3.screenshot(path=str(Path(shots) / "ZOOM200-native-creator-cv.png"))
                pg3.close()
            ctx.close()
    finally:
        env.stop()
        shutil.rmtree(profile, ignore_errors=True)
    fails = [r for r in R.RESULTS if r[2] != "PASS"]
    print(f"\n{len(R.RESULTS) - len(fails)}/{len(R.RESULTS)} PASS")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
