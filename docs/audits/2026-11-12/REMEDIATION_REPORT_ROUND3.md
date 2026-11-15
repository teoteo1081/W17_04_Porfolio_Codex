# Báo cáo khắc phục vòng 3 (sau kiểm định độc lập Round 3 của Codex trên commit `563381b`)

Codex kết luận **AUDIT_FAIL** với R3-01…R3-09 (độ thuần nhất ngôn ngữ, N07 chưa đóng triệt để, editor còn tiếng Việt). Các báo cáo trước giữ nguyên. Báo cáo của Codex nằm ngoài repo (`W17_02_AUDIT_ROUND3_2026-11-13/AUDIT_REPORT_ROUND3.md`) và được coi là đầu vào.

## Quyết định sản phẩm (do chủ dự án chốt)

| Câu hỏi | Quyết định |
|---|---|
| Thuật ngữ thương hiệu (chức danh, tên 4 dịch vụ, 4 badge) ở VI/ES/ZH | **Dịch cả tên dịch vụ và chức danh.** Giữ nguyên tên riêng và viết tắt (GA4, GTM, Power BI, BigQuery, Python, SQL, BI, KPI, MarOps, QA, WRP Tax Services, Operation 0, TJ WordLoop, TJ Courses Hub). |
| Toolbar Creator (nút, toast, confirm) | **Bản địa hóa đầy đủ** 4 ngôn ngữ, kể cả khi bấm Alt+E trên Final. |

Hệ quả cần biết: yêu cầu cũ "badge/chức danh giữ tiếng Anh" không còn đúng với VI/ES/ZH; test CONTENT được sửa để so với **từ điển của từng locale** thay vì ép giữ tiếng Anh. Bản EN giữ nguyên.

## Bảng R3-01 … R3-09

| # | Mức | Trạng thái | Cách sửa | Bằng chứng (đã chạy) | Rủi ro còn lại |
|---|---|---|---|---|---|
| R3-01 | P2 | **Đã sửa** | Gắn key cho chữ cứng: brand, nhãn trục biểu đồ, 4 badge dịch vụ, `POWER BI TELEMETRY`, `MULTI-PRODUCT SHOWCASE…`, `All rights reserved`, `GA4 LIVE DRILL-DOWN`, 4 badge gói trong modal, tổng `174 users`; đủ 4 locale. | Test `R3-01..05`: quét từ điển + chữ hiển thị thật. | Một số thuật ngữ mượn phổ biến (Dashboard, Lead, hosting) được giữ vì không nằm trong danh sách từ chặn. |
| R3-02 | P2 | **Đã sửa** | Dịch giá trị VI/ES/ZH của `hero_positioning`, `eco_property`, `eco_title`, tên 4 dịch vụ (cả modal), nhãn chân thẻ, tiêu đề spoke, badge spoke, các tiêu đề/ nhãn GA4 còn tiếng Anh. | Cùng test; so khớp giá trị từng locale. | Bản dịch do mình soạn, chưa có người bản ngữ duyệt (đặc biệt ES/ZH). |
| R3-03 | P2 | **Đã sửa** | Hậu tố `users` sinh động giờ lấy từ khóa `unit_users` (`{n} người dùng`, `{n} usuarios`, `{n} 位用户`); dịch `GA4_REAL_DATA` (category + tiêu đề trang VI/ES); bỏ chú thích tiếng Anh thừa ("Views", "Data Bar", "GA4 Validated Property"…). | DOM của cả 3 tab GA4 ở VI/ES/ZH sạch trong test thuần nhất. | Tên quốc gia dạng "Hoa Kỳ (United States)" vẫn giữ cách trình bày song ngữ có chủ ý. |
| R3-04 | P2 | **Đã sửa** | CV: dịch `hero_title`, badge, nhãn học vấn, `footer_copy`, nhãn phụ, skill group; 2 tag công cụ trước đây không có key (UTM, Git) nay có key. Các câu chứa "Actual vs. Target"/"Self-service BI"/"AI Agents" được viết lại. | Test thuần nhất (4 file). | Tên công cụ (Claude Code, Codex, Pandas…) được giữ. |
| R3-05 | P2 | **Đã sửa** | Nội dung `#demo-modal` (VI/ES) dịch phần diễn giải, giữ Python/SQL/tên công cụ. | Test mở 3 modal demo × 3 locale. | `Field Parameters` được giữ trong ngoặc ở VI/ZH như tên tính năng. |
| R3-06 | P2 | **Đã sửa** | Đồng bộ HTML tĩnh với bản VI cho **mọi** `data-i18n` và `data-i18n-aria` (công cụ tự thay inner HTML theo từ điển). | Test `R3-06`: so DOMParser của file nguồn với từ điển VI, 0 lệch trên 4 file (Codex chỉ ra 10 node, thực tế còn nhiều hơn sau khi đổi bản dịch). | Chưa đo thời lượng nháy chữ trên mạng chậm (không còn lệch nguồn nên không còn lý do nháy). |
| R3-07 | P2/P3 | **Đã sửa** | 4 `aria-label` cứng thành `data-i18n-aria`; `<title>`, `description`, `og:title`, `og:description` đổi theo locale (chỉ `textContent`/`setAttribute`); metadata portfolio đổi sang định vị Operations & Data Analyst. | Test `R3-07`. | Trình thu thập dữ liệu đọc bản tĩnh (VI) vì không chạy JS. |
| R3-08 | P2 | **Đã sửa** | Toolbar, nhãn bật/tắt, toast, `confirm`, nút điều khiển CV (⬆⬇✕, thêm tag, tooltip, menu màu) dùng bảng chuỗi 4 locale (`W17_UI`, `UI_CV`) và được vẽ lại ngay khi đổi ngôn ngữ; nhãn thương hiệu do người dùng sửa **không** bị ghi đè khi đổi ngôn ngữ. Test cũ dò chữ "ghi đè" trong toast được thay bằng kiểm trạng thái thật (file đã đổi + có backup). | Test `R3-08`: đủ khóa 4 locale, EN/ES/ZH không còn chữ Việt trong toolbar/toast, nhãn nút đổi theo locale. | Văn bản `confirm()` do trình duyệt vẽ nên không kiểm bằng pixel. |
| R3-09 | P2 | **Đã sửa** | `validate_html` parse bằng `html.parser` và chỉ tính **phần tử thật**: mỗi id bắt buộc phải xuất hiện đúng một lần và đúng thẻ (`header`, `section`, `script`…), tối thiểu 300 phần tử, đủ lượng mã script, khối `w17-baked-edits` phải là JSON object hợp lệ; comment và chuỗi trong script không còn được tính. | Test `N07`: marker trong comment, trong chuỗi script, sai thẻ, trùng id đều bị từ chối; trang thật vẫn 200. | Tác giả đã xác thực vẫn có thể gửi trang đủ thành phần nhưng sai nội dung (kiểm tra cấu trúc, không phải sanitizer). |

## Kết quả chạy cuối

- `tests/regression/run_all.py` (đầy đủ, 6 viewport × 4 locale): **36/36 PASS**, thêm các ca R3 (thuần nhất, HTML tĩnh = VI, bản địa hóa editor, aria/metadata, N07) trên nền F01–F10, N01–N08, CONTENT, NAV, RESP, SAFETY.
- `tests/regression/native_zoom.py` (zoom Chromium 200% thật, `innerWidth=640`, `outerWidth=1280`, `dpr=2`): xem mục "Zoom" bên dưới.
- `tools/sync_creators.py --check`: OK.
- Ghi chú trung thực: lần chạy zoom đầu của vòng này báo FAIL vì **bài test** tìm nút Lưu theo chữ tiếng Việt `Lưu file sạch` (nút nay được bản địa hóa); đã sửa test sang tìm theo `id` và chạy lại.

## Giới hạn

- Bản dịch ES/ZH chưa được người bản ngữ rà soát; danh sách từ chặn của test thuần nhất là heuristic (từ tiếng Anh thông dụng đã được Codex nêu), không chứng minh mọi câu đều tự nhiên.
- Vẫn chỉ Chromium/Playwright; chưa có thiết bị cảm ứng thật, Firefox/Safari, WCAG 2.2 AA đầy đủ, bản in PDF native.
- Chưa có audit độc lập lần 4 trên commit này.
