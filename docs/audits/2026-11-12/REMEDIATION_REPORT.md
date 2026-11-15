# Báo cáo khắc phục W17_02 (sau audit độc lập 12/11/2026)

Báo cáo audit gốc [AUDIT_REPORT.md](AUDIT_REPORT.md) giữ nguyên, không sửa. Commit lưu báo cáo audit: `ad92e4bed71d8b8ccb19c6b1c8868b7bb14de132`.

Mọi kiểm chứng dưới đây chạy thật bằng Chromium (Playwright) trên **bản sao tạm** của repo, với `server.py` thật trỏ vào thư mục tạm. File làm việc thật không bị ghi: kiểm tra hash trước/sau, lượt xác nhận cuối `SAFETY PASS`. Không có mục nào được ghi PASS khi chưa đo.

## 1. Tự xác minh lại lỗi trước khi sửa (baseline trên commit `ad92e4b`)

| Lỗi | Kết quả tái hiện trước khi sửa |
|---|---|
| F01 | Cả bốn trang ghi/đọc `portfolio_lang`; theme dùng `portfolio_theme`. Xác nhận. |
| F02 | Nạp `index.html` làm hai key Creator portfolio thành `null`; nạp `index_portfolio_clean.html` làm hai key Creator CV thành `null`. Xác nhận. |
| F03 | 375×812: `#modal-service-packages` nằm ngoài vùng cuộn, vùng cuộn chỉ cao 32px, packages đáy y≈1296. Xác nhận. |
| F04 | Creator EN vẫn hiện `[📊 Xem bảng chi tiết ↗]`. Xác nhận. |
| F06 | `span.inline-block` của `hero_bio`/`footer_desc` = 0 sau khi đổi ngôn ngữ (Final và Creator). Xác nhận. |
| F07 | Mở lại bản xuất của Creator portfolio với cache: 73 contenteditable + 73 spellcheck; Creator CV: 184 + 133; link `./editor_portfolio.html` bị khôi phục. Xác nhận. |
| F09 | 375px: nút Lưu của Creator CV ở x=684–841, ngoài viewport 375. Xác nhận. |
| F10 | Trên bản sao tạm: POST cross-origin `text/plain` không token ghi đè `index.html` bằng `<html>PWNED</html>` và trả `200 ok`. Xác nhận. |
| Ca cache trống (phát hiện thêm) | Chỉnh sửa trong Final CV mất khi mở lại bản xuất bằng cache trống, vì `switchLanguage` vẽ lại từ từ điển gốc. |
| F05, F08 | F05 xác nhận qua mã (`innerHTML = savedMain/savedHTML`). F08 xác nhận bằng đo vị trí từ (Hero EN Creator cuối dòng chỉ còn `Growth`). |

## 2. Bảng F01–F10

| # | Trạng thái | Cách sửa | Bằng chứng (đã chạy) | Rủi ro còn lại |
|---|---|---|---|---|
| F01 | **Đã sửa** | `w17_02_lang`, `w17_02_theme` ở cả 4 file qua `w17GetPref/w17SetPref`; không còn đọc/ghi `portfolio_*`. | Đặt `portfolio_lang=zh`, `portfolio_theme=light` (giả lập W17): cả 4 trang vẫn mở `vi`, không ghi đè khóa chung, nhớ `w17_02_lang`/`w17_02_theme` khi tải lại. | Ngôn ngữ/theme đã chọn trước đây dưới khóa cũ không được chuyển sang (quay về `vi`/dark một lần) — cố ý, để không rò rỉ giữa hai ứng dụng. |
| F02 | **Đã sửa** | Xóa toàn bộ vòng lặp `removeItem` ở Final và Creator. Không còn mã nào xóa key cache (chỉ nút "Khôi phục" ghi trạng thái rỗng và xóa palette của chính W17_02). | Đặt 7 key sentinel (Creator portfolio/CV, key W17 cũ, key ứng dụng khác), mở cả 4 trang 2 lượt: không key nào đổi. | Không còn. |
| F03 | **Đã sửa** | Packages nằm trong thân modal cuộn được (`#ga4-modal-body`, `min-h-0`, `tabindex=0`, `role=region`); header/tab/footer `shrink-0`; mobile/viewport thấp (`max-width:639px` hoặc `max-height:620px`) cả hộp thoại cuộn. Bấm thẻ dịch vụ gọi `openGA4DrilldownModal(tab, trigger, 'pN')`, cuộn đúng nhóm vào vùng nhìn thấy và đánh dấu (`ring`, `aria-current`). | 224 tổ hợp (Final + Creator × 320/375/390/768/1024/1440 + 720×450 × 4 locale × 4 thẻ): nhóm được bấm nằm trong vùng nhìn thấy và cả 12 đầu việc cuộn tới được. Bàn phím: Enter mở modal, focus vào nút đóng, bẫy focus, PageUp/PageDown cuộn, Escape trả focus. Ảnh: `remediation/F03-modal-*.png`, `after-modal-*.png`. | Kiểm bằng cuộn lập trình + wheel/phím trong Chromium; chưa thử cảm ứng thật trên thiết bị. |
| F04 | **Đã sửa** | Creator được **sinh từ Final** (`tools/sync_creators.py`), nên từ điển, CTA, Hero (`br` + span) giống hệt Final. | Mọi `data-i18n/-aria/-placeholder` có đủ khóa ở 4 locale; bốn locale cùng bộ khóa; từ điển Creator = Final (portfolio và CV); 4 CTA đổi theo locale; Hero giữ `br` + `span.inline-block`. | Creator đổi sang markup của Final (xem mục 5). |
| F05 | **Đã sửa** | Bỏ hoàn toàn gán snapshot `innerHTML`. Lưu theo schema: `editsByLang` (portfolio) / `textEditsByLang`, `fieldEdits`, thứ tự/thẻ/tag/ảnh (CV) và `nodeEdits` (node không có `data-i18n`, khóa theo chỉ số + văn bản gốc, chỉ áp khi văn bản gốc khớp). Mọi giá trị đi qua sanitizer allowlist, chỉ nhận khóa có trong từ điển. **Migration** snapshot cũ → schema, một lần, không xóa bản cũ. | Cache/snapshot độc hại (`img onerror`, `script`, `onclick`, `javascript:`, `__proto__`) không thực thi, không chèn node, không giữ thuộc tính (4 trang). Migration kiểm bằng chính Creator cũ ở git `ad92e4b`: chỉnh sửa badge (portfolio), thứ tự section và tag (CV) xuất hiện ở Creator/Final mới, snapshot cũ còn nguyên. `nodeEdits` còn sau reload/đổi ngôn ngữ và không áp nhầm khi văn bản gốc không khớp. | Với snapshot cũ, chỉnh sửa văn bản tự do ở node không có khóa và ô thương hiệu của toolbar **không** map được; chúng vẫn nằm nguyên trong key cũ chưa bị xóa. Tag của snapshot cũ chỉ khớp theo vị trí/nội dung. |
| F06 | **Đã sửa** | Chuỗi dịch giữ cấu trúc; thêm bảo vệ đuôi câu khi render (`w17ProtectTail`/`protectTailCV`: bọc 2 từ cuối, CJK 3 ký tự; span thủ công chỉ 1 từ được kéo thêm từ liền trước). | `hero_bio`, `footer_desc` của CV có span sau mỗi lần đổi ngôn ngữ (4 locale × 2 trang). | Không còn. |
| F07 | **Đã sửa** | Final không còn loader snapshot nào. Bản xuất: bỏ toolbar, contenteditable, spellcheck, cờ Creator, nút điều khiển, link về Final; chỉnh sửa được **nhúng** vào `#w17-baked-edits` (JSON thuần, đã escape) nên mở lại bằng cache trống vẫn đủ nội dung. Server từ chối HTML còn toolbar/contenteditable. | Chu trình thật chỉnh sửa → bấm Lưu → server ghi → mở lại với **cache trống** và **cache có dữ liệu** → đổi 4 ngôn ngữ → bấm link hai chiều, cho cả 4 nguồn (2 Creator + 2 Final). DOM sau khi mở lại: 0 contenteditable/spellcheck/toolbar/nút điều khiển/link `editor_*`; chỉnh sửa EN không rò sang VI; dữ liệu có sẵn không mất; Creator giữ dữ liệu của chính nó. Xuất khi **đang bật sửa chữ** cũng sạch. | Alt+E vẫn có thể bật lại editor trong Final (thiết kế cũ, không hiện mặc định). |
| F08 | **Đã sửa** | `h1, h2, [data-tail] { text-wrap: balance }`; `data-tail` + `text-balance` cho đoạn Hero và badge Section 4; tự bảo vệ đuôi câu (F06). Đo phát hiện thêm một orphan thật (tiêu đề CV ES `Especializadas`) và đã sửa. | 756 phần tử (4 trang × 6 viewport × 4 locale): không dòng cuối chỉ 1 từ (đo vị trí từng từ), tất cả H1/H2/hero có `balance`. Ảnh: `F08-creator-portfolio-en-375.png`. | Đo bằng Chromium; trình duyệt chưa hỗ trợ `text-wrap: balance` sẽ chỉ dựa vào bảo vệ đuôi câu. |
| F09 | **Đã sửa** | Toolbar Creator CV nằm trong luồng trang, `flex-wrap`, bỏ `h-14`/`overflow-x-hidden`/`shrink-0`; sticky từ `md`; menu màu định vị theo nút. Toolbar portfolio đã wrap, thêm đồng bộ offset với navbar. Nút có focus ring và cỡ ≥24px. | 24 tổ hợp (4 trang × 6 viewport): mọi nút nằm trong viewport, không bị che, không tràn ngang; bấm Lưu bằng chuột ở 320/375 thật sự ghi được; Tab tới nút Lưu và thấy focus. Ảnh: `F09-editor_cv-375.png`, `after-creator-cv-toolbar-375.png`. | Toolbar CV cao ~159px ở 375px (không sticky dưới md để không chiếm màn hình). |
| F10 | **Đã sửa** | `server.py` viết lại: kiểm tra `Host`, `Origin`/`Sec-Fetch-Site`; **không CORS**; token phiên ngẫu nhiên qua `GET /api/session` (chỉ same-origin) + header `X-W17-Token` so sánh hằng thời gian; bắt buộc `application/json`; giới hạn body 12MB; allowlist đúng tên file; kiểm tra cấu trúc HTML; ghi nguyên tử (tệp tạm + `os.replace`) và backup 5 bản vào `.w17_backups/` (đã `.gitignore`); trả mã đúng (200 chỉ khi đã ghi; 4xx/5xx kèm lý do); không phục vụ `*.py`, thư mục ẩn. Client lấy token, báo kết quả thật (không còn toast thành công giả). | Test chạy trên server thật ở thư mục tạm: origin/Host/token lạ bị 403/401, preflight không có CORS, `text/plain` 415, body 13MB → 413, JSON hỏng 400, target `server.py`/`../server.py`/`editor_*`/`INDEX.HTML` 400, HTML rỗng/rác/cắt cụt/khác trang/còn editor → 4xx, ghi hợp lệ 200 + `saved` + backup + không để lại `.tmp`, `GET /server.py`, `/.git/config` bị chặn. Phát hiện và sửa thêm lỗi thật: từ chối sớm mà không đọc body gây RST làm client mất mã lỗi. | Mở bằng `file://` chỉ tải file về, không ghi vào dự án (phải dùng `dev_server.py`). Token đổi mỗi lần khởi động server (tải lại trang). Server chỉ phù hợp phát triển cục bộ. |

## 3. Kết quả kiểm chứng

Lượt đầy đủ (6 viewport × 4 locale) cho 23/25 mục PASS. Hai mục không PASS trong lượt đó là **F10** (lỗi RST ở server khi từ chối sớm — một lỗi thật, đã sửa trong `server.py`) và **SAFETY** (thất bại vì tôi sửa `server.py` giữa lượt nên hash đổi, không phải do test ghi file). Sau khi sửa, lượt xác nhận trên mã đúng như đã commit chạy lại F10, F07, F09 và SAFETY: 6/6 PASS; zoom native chạy lại trên mã cuối: 3/3 PASS. Các nhóm còn lại không đổi mã sau lượt đầy đủ.

- **Bốn file HTML**: `index.html`, `index_portfolio_clean.html`, `editor_workspace/editor_portfolio.html`, `editor_workspace/editor_cv.html` — mọi kiểm thử i18n, orphan, overflow, toolbar, round trip đều chạy trên cả bốn.
- **Bốn ngôn ngữ** `vi/en/es/zh` và **viewport** 320, 375, 390, 768, 1024, 1440 (thêm 720×450 cho modal).
- **Zoom native 200%**: có. Ghi mức zoom mặc định của Chromium vào Preferences của profile tạm (`partition.default_zoom_level = log(2)/log(1.2)`), mở bằng `launch_persistent_context` với `viewport=None`. Bằng chứng không phải emulation: `innerWidth=640`, `outerWidth=1280`, `devicePixelRatio=2` mà không dùng `set_viewport_size`/`device_scale_factor`. Ở 200%: không tràn ngang, không orphan, toolbar không bị cắt/che, modal đưa đúng nhóm vào vùng nhìn thấy (4 trang × 4 locale; 2 trang × 4 locale × 4 thẻ). Ảnh: `ZOOM200-native-creator-cv.png`, `ZOOM200-native-modal.png`. (Lưu ý: chụp màn hình qua API thường của Playwright cho ảnh trống ở chế độ này; ảnh được chụp bằng CDP `Page.captureScreenshot`.)
- **Kiểm tra trực quan**: đã xem ảnh Creator CV 375 (toolbar xuống dòng, nút Lưu thấy được), modal dịch vụ 4 trên 375 và 720×450, Creator portfolio EN 375, Creator CV và modal ở zoom native 200%. Các tổ hợp còn lại được xác nhận bằng đo DOM/vị trí, không bằng mắt.
- **Bàn phím**: mở modal bằng Enter, bẫy focus, cuộn PageUp/PageDown, Escape trả focus; Tab tới nút Lưu của Creator CV ở 375px.
- **Điều hướng**: click thật hai chiều Final↔Final và Creator↔Creator, và sau khi mở lại bản xuất.

## 4. Yêu cầu phải giữ

Đã kiểm lại ở cả 4 locale (Final và Creator): định vị **Operations & Data Analyst**; đúng 4 dịch vụ với badge `Core • End-to-End`, `Core • Data & BI`, `Tech Support • Beta`, `MarOps • No KPI Commit`; thẻ 4 vẫn nói rõ không cam kết doanh thu/lead; khối Power BI Telemetry; bốn ứng dụng WRP Tax Services, Operation 0, TJ WordLoop, TJ Courses Hub; điều hướng hai chiều; chức năng Creator (bật sửa, lưu Final, khôi phục, Alt+E, đổi ảnh, phối màu, sắp xếp/xóa/thêm tag của CV).

## 5. Quyết định và thay đổi cần lưu ý

1. **Creator được sinh từ Final** thay vì sửa tay hai bản cũ (chúng là bản cũ của Final cộng toolbar + snapshot). Hai Creator giờ chỉ khác Final ở `data-w17-mode="creator"` và link điều hướng tĩnh (`tools/sync_creators.py`, có `--check`). Hệ quả: giao diện Creator khớp Final (markup/aria mới của Final); đây là thay đổi lớn nhất ngoài phạm vi từng lỗi nhưng là cách duy nhất bảo đảm đồng bộ i18n.
2. Tiêu đề khung gói trong modal ghi "3 Gói…" trong khi có 4 gói → sửa thành "4 Gói…" ở cả bốn locale (khớp yêu cầu "đúng bốn dịch vụ"). Đây là thay đổi nội dung nhỏ ngoài danh sách F01–F10.
3. Nút "Khôi phục" ghi trạng thái rỗng thay vì xóa key, để snapshot cũ không bị chuyển đổi lại sau khi khôi phục.

## 6. Giới hạn và rủi ro chưa xử lý

- Chỉ kiểm bằng Chromium (Playwright); chưa chạy Firefox/Safari, chưa có thiết bị cảm ứng thật, chưa audit WCAG 2.2 AA đầy đủ (contrast, screen reader, mọi touch target). Các kiểm tra chỉ chứng minh trong phạm vi nêu từng dòng.
- Nút "Khôi phục" (hộp `confirm`) và tải ảnh đại diện chưa có test tự động.
- Kiểm thử cần Internet (Tailwind/Lucide/Chart.js qua CDN).
- Dữ liệu GA4/BigQuery hiển thị không được xác thực lại.
- Chưa push; chưa chạy audit lại độc lập bởi người/agent khác trên commit này.

## 7. File thay đổi

Sửa: `index.html`, `index_portfolio_clean.html`, `editor_workspace/editor_portfolio.html`, `editor_workspace/editor_cv.html` (hai Creator được sinh lại), `server.py`, `dev_server.py`, `.gitignore`, `README.md`.
Thêm: `tools/sync_creators.py`, `tests/regression/run_all.py`, `tests/regression/native_zoom.py`, `docs/audits/2026-11-12/REMEDIATION_REPORT.md`, `docs/audits/2026-11-12/remediation/*.png`.
Không đổi: `AUDIT_REPORT.md` và ảnh audit gốc.

## 8. Chạy lại

```bash
python tools/sync_creators.py --check
python -X utf8 tests/regression/run_all.py            # đầy đủ (~25 phút)
python -X utf8 tests/regression/run_all.py --quick    # nhanh
python -X utf8 tests/regression/native_zoom.py        # zoom native 200%
```
