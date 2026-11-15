# W17_04_Porfolio_Codex

Portfolio độc lập của **Thao Nguyen (TJ)**, do **Codex phụ trách chính**.

**Operations Automation & Data Reporting Specialist** — giúp doanh nghiệp dịch vụ nhỏ tự động hóa công việc hậu cần, đối soát dữ liệu và xây báo cáo quản trị đáng tin cậy.

## Dịch vụ

1. **Workflow Automation & Operations Systems:** nhập liệu, đối soát, đồng bộ; công cụ chạy được, danh sách ngoại lệ và SOP.
2. **Business Reporting & BI Dashboards:** chuẩn hóa dữ liệu, định nghĩa KPI, Power BI / Looker Studio và hướng dẫn cập nhật.
3. **Service Websites & Lead Capture Setup:** website dịch vụ, form liên hệ, luồng chuyển dữ liệu và hướng dẫn quản trị.
4. **GA4 & GTM Setup, Audit & QA:** kế hoạch đo lường, cấu hình, kiểm thử và tài liệu bàn giao.

Bắt đầu bằng pilot có phí với đầu vào, đầu ra, ngân sách và tiêu chí nghiệm thu rõ ràng. Thời hạn hỗ trợ, mở rộng và bảo trì được thống nhất theo từng dự án.

## Sở hữu và phân tách

- Sao chép mã nguồn từ W17_02 tại 9a37799 làm điểm xuất phát ngày 2026-11-14.
- Đã bỏ .git của bản sao và khởi tạo Git mới trên main: lịch sử mới, không có commit cha từ W17_02.
- Repository đích: https://github.com/teoteo1081/W17_04_Porfolio_Codex.
- Không sửa hoặc push vào W17_02 hay W17_03_Claude_porfolio.
- Browser storage dùng namespace w17_04 riêng, không đọc dữ liệu chỉnh sửa của W17_02.
- AGENTS.md là quy chuẩn kỹ thuật; CLAUDE.md / GEMINI.md chỉ tham chiếu quy chuẩn, không thay đổi việc Codex phụ trách chính.
- docs/audits/2026-11-12 là báo cáo lịch sử của bản nguồn, **không phải kết quả kiểm thử W17_04**. Kết quả mới ở docs/verification/2026-11-14.

## Cấu trúc

| File / thư mục | Vai trò |
|---|---|
| index.html | Portfolio Final, dịch vụ, pilot, dashboard và liên hệ |
| index_portfolio_clean.html | CV / hồ sơ năng lực Final |
| editor_workspace/ | Hai Creator sinh từ Final |
| tools/sync_creators.py | Sinh và kiểm tra Creator ↔ Final |
| server.py, dev_server.py | Máy chủ editor cục bộ, lưu Final có kiểm soát |
| ga4_metrics_live.json, fetch_ga4_bigquery.py | Telemetry kế thừa và công cụ cập nhật; không phải kết quả kinh doanh khách |
| tests/regression/ | Chức năng, i18n, responsive và native zoom |
| docs/SALES_PLAYBOOK.md | Định vị, tìm khách và mẫu tiếp cận |

## Chạy cục bộ

Yêu cầu Python 3.10 trở lên. Máy chủ chỉ dùng thư viện chuẩn.

    python dev_server.py

Mở http://127.0.0.1:8000/index.html hoặc /index_portfolio_clean.html.
Creator: /editor_workspace/editor_portfolio.html và /editor_workspace/editor_cv.html.

Chỉ máy chủ cục bộ hỗ trợ ghi Final qua /api/save; static hosting và mở trực tiếp file không có endpoint ghi. Server bind loopback, yêu cầu token same-origin, giới hạn payload và đích ghi, ghi nguyên tử và giữ 5 backup trong .w17_backups/.

## Cập nhật nội dung

Final là nguồn chuẩn. Đồng bộ HTML tiếng Việt mặc định và dictionary vi/en/es/zh, giữ ngắt dòng và bảo vệ cụm từ cuối. Sau đó:

    python tools/sync_creators.py
    python tools/sync_creators.py --check

Trang dùng Tailwind, Lucide, Chart.js và Google Fonts qua CDN; cần mạng để tải tài nguyên. Form mở ứng dụng email, không tự gửi email và không lưu lead trên server.

## Kiểm tra

    python -m pip install playwright
    python -m playwright install chromium
    python -X utf8 tests/regression/run_all.py --shots docs/verification/2026-11-14/screenshots
    python -X utf8 tests/regression/native_zoom.py docs/verification/2026-11-14/zoom

Đọc báo cáo xác minh trước khi kết luận về bản mới. Không đưa credentials hoặc dữ liệu khách chưa ẩn thông tin nhạy cảm vào repository.
