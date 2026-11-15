#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sinh (hoặc kiểm tra) hai bản Creator từ hai bản Final — Final là NGUỒN DUY NHẤT.

    editor_workspace/editor_portfolio.html  <-  index.html
    editor_workspace/editor_cv.html         <-  index_portfolio_clean.html

Creator khác Final đúng hai điểm, nên i18n (vi/en/es/zh), sanitizer, lưu dữ liệu có schema, modal và toolbar
không thể lệch nhau (AGENTS.md §2, §9; báo cáo audit F04/F05/F06/F08):
  1. <html data-w17-mode="creator">  -> thanh công cụ hiện sẵn khi mở trang.
  2. Liên kết điều hướng tĩnh trỏ sang Creator tương ứng thay vì Final.

Dùng:
    python tools/sync_creators.py          # ghi lại hai Creator
    python tools/sync_creators.py --check  # thoát mã 1 nếu Creator lệch khỏi Final (dùng trong kiểm thử)
"""

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HTML_OPEN = '<html lang="vi" class="dark scroll-smooth"'
MODE_ATTR = ' data-w17-mode="creator"'

# (nguồn Final, đích Creator, [(chuỗi cũ, chuỗi mới, số lần xuất hiện bắt buộc)])
JOBS = [
    (
        "index.html",
        "editor_workspace/editor_portfolio.html",
        [('href="./index_portfolio_clean.html"', 'href="./editor_cv.html"', 3)],
    ),
    (
        "index_portfolio_clean.html",
        "editor_workspace/editor_cv.html",
        [('href="./index.html"', 'href="./editor_portfolio.html"', 1)],
    ),
]


def read(path):
    with io.open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def build(src_rel, replacements):
    text = read(ROOT / src_rel)
    if text.count(HTML_OPEN) != 1:
        raise SystemExit(f"{src_rel}: không tìm thấy thẻ <html> chuẩn để gắn data-w17-mode")
    text = text.replace(HTML_OPEN, HTML_OPEN + MODE_ATTR, 1)
    for old, new, expected in replacements:
        found = text.count(old)
        if found != expected:
            raise SystemExit(f"{src_rel}: cần {expected} lần '{old}', thực tế {found}")
        text = text.replace(old, new)
    return text


def main(argv):
    check = "--check" in argv
    drift = []
    for src_rel, dst_rel, replacements in JOBS:
        expected = build(src_rel, replacements)
        dst = ROOT / dst_rel
        current = read(dst) if dst.exists() else None
        if current == expected:
            print(f"OK       {dst_rel}")
            continue
        if check:
            drift.append(dst_rel)
            print(f"LỆCH     {dst_rel}")
        else:
            with io.open(dst, "w", encoding="utf-8", newline="") as fh:
                fh.write(expected)
            print(f"ĐÃ GHI   {dst_rel}")
    if drift:
        print("Creator lệch khỏi Final. Chạy: python tools/sync_creators.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
