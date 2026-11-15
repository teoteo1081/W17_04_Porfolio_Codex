# Báo cáo khắc phục vòng 2 (sau kiểm định độc lập của Codex trên commit `591b367`)

Codex kết luận **AUDIT_FAIL** với tám phát hiện mới N01–N08. Báo cáo audit gốc và [REMEDIATION_REPORT.md](REMEDIATION_REPORT.md) giữ nguyên. Báo cáo của Codex nằm ngoài repo (`W17_02_AUDIT_591b367_2026-11-13/REPORT.md`) và được coi là đầu vào, không sao chép.

Cách làm: tự tái hiện lỗi trước khi sửa, viết ca kiểm thử cho từng lỗi (chạy trên mã cũ phải FAIL), rồi sửa. Kiểm thử chạy trên bản sao tạm, server thật trỏ vào thư mục tạm; file làm việc thật không bị ghi (hash toàn bộ file tracked + untracked trước/sau khớp).

## Tái hiện trước khi sửa

| Lỗi | Cách tự tái hiện | Kết quả trên `591b367` |
|---|---|---|
| N01 | Creator CV cũ (git `ad92e4b`): xóa thẻ giải pháp đầu → mở Creator mới cùng localStorage | Sai: thẻ còn lại bị đổi (`sol_card2/3` → `sol_badge_1/2`), 4 locale |
| N05 | `GET /server%2epy` | 200, trả 12 235 byte mã nguồn (trong khi `/server.py` là 404) |
| N06 | 3 luồng × 10 POST đồng thời | 19×200, 11×500 |
| N07 | POST HTML rác chỉ chứa `id="ga4-ecosystem"` | 200, ghi đè `index.html` |
| N08 | POST body 13 MB gửi thật | Client mất kết nối (WinError 10053), không nhận được 413 |
| N02, N03, N04 | Đọc mã + ca kiểm thử mới (xem dưới) | Xác nhận cùng cơ chế mã mà Codex chỉ ra |

## Bảng N01–N08

| # | Mức | Trạng thái | Nguyên nhân | Cách sửa | Bằng chứng | Rủi ro còn lại |
|---|---|---|---|---|---|---|
| N01 | P1 | **Đã sửa** | `alignLegacyIdsCV` gán ID thẻ theo **vị trí** (`free.shift()`), không xác định được thẻ nào đã bị xóa. | Khớp snapshot cũ ↔ thẻ hiện tại theo **danh tính** (tập khóa `data-i18n` bên trong thẻ; điểm trùng cao nhất, không hòa). Thẻ không xác định được danh tính → **không ghi danh sách thứ tự** của lưới đó (loader bỏ qua), tuyệt đối không đoán. | Ca `N01`: Creator cũ xóa thẻ đầu, 4 locale, Creator mới còn đúng hai thẻ `sol_card2/3`. | Thẻ cũ không khớp được thì thứ tự/xóa của lưới đó không được chuyển (giữ mặc định, snapshot cũ vẫn còn nguyên). |
| N02 | P1 | **Đã sửa** | `persistStructuredEdits` duyệt mọi node cùng khóa (menu desktop + mobile); node chưa sửa xóa chỉnh sửa của node đã sửa. | Gộp theo khóa; ưu tiên node người dùng vừa gõ (`event.target`), nếu không thì node đầu tiên khác bản gốc; đồng bộ các node cùng khóa còn lại. Áp cho portfolio và CV (`buildStateCV`). | Ca `N02`: sửa `nav_about` ở 1440px → còn sau reload; xuất Final rồi mở lại cache trống / cache có dữ liệu vẫn còn; cả Creator và Final. | Khi hai node cùng khóa bị sửa khác nhau thì node vừa gõ thắng. |
| N03 | P1 | **Đã sửa** | `nodeEdits` khóa theo **chỉ số** DOM; kéo thẻ + xuất làm chỉ số trỏ sang node `✓` khác có cùng văn bản nên `from === orig` vẫn đúng. | Mỗi node không-i18n nhận `data-node-id` ổn định (gán một lần trên DOM tĩnh, **được giữ trong file Final khi xuất**); `nodeEdits` khóa theo id. Vẫn giữ kiểm tra `from`. | Ca `N03`: sửa `✓` thẻ Planning, kéo thẻ xuống sau BI, xuất; cache trống và cache có dữ liệu: đúng một node chứa `CHECK-CUSTOM`, đúng thẻ. | File Final xuất sẽ mang thêm thuộc tính `data-node-id` (vô hại, không phải trạng thái editor). |
| N04 | P2 | **Đã sửa** | Brand `.brand-title` của toolbar nằm ngoài `#portfolio-root` nên không được lập chỉ mục/lưu. | `brandEdits` theo vị trí node lá trong toolbar (CV và portfolio), áp lại khi tạo toolbar; tách tên và "(Capability V3)" thành hai span lá (giao diện không đổi). | Ca `N04`: sửa brand → reload → còn, cả Creator CV và portfolio. | Brand chỉ nằm ở toolbar dev, không được nhúng vào file Final (đúng ý, toolbar bị gỡ khi xuất). |
| N05 | P1 | **Đã sửa** | Bộ lọc kiểm path **trước** khi giải mã percent-encoding. | Kiểm trên đường dẫn thật `translate_path` (đã giải mã + chuẩn hóa + `resolve`), phải nằm trong thư mục gốc, không có thành phần bắt đầu bằng `.`, **allowlist đuôi file tĩnh** (html/json/css/js/ảnh/font/txt), không liệt kê thư mục. Áp cho cả GET và HEAD. | Ca `F10+`: 11 biến thể (`%2e`, `%2E`, `%73erver.py`, `%2egit`, `%2e%2e`, `..%2f`, `%252e`, backup) đều không trả 200; file hợp lệ vẫn 200. | Không có. |
| N06 | P2 | **Đã sửa** | Backup + ghi không tuần tự hóa; Windows `os.replace` bị từ chối khi có tiến trình đang đọc. | `WRITE_LOCK` bọc backup + ghi; `os.replace` thử lại ngắn khi `PermissionError`; hai file Final được **đọc dưới cùng khóa** (trước đó, mở file đúng lúc thay thế trả 404 giả). | Ca `F10+`: 3 + 2 luồng ghi đồng thời (mỗi luồng 10 lần) kèm luồng đọc liên tục: 0 lần 500, đọc luôn thấy file nguyên vẹn, tên backup không trùng; lặp 3 lần đều đạt. | Chỉ giả định một server dev cục bộ một tiến trình. |
| N07 | P2 | **Đã sửa một phần (cố ý)** | Validator chỉ kiểm một marker. | Yêu cầu **đủ 6–7 thành phần đặc trưng** của từng trang, đúng một `<html>`/`<body>`, kích thước ≥100 KB **và** ≥50% file hiện có, không còn toolbar/contenteditable. | Ca `F10+`: HTML rác có marker, nửa file, thiếu `visual-editor-script`, thiếu `w17-baked-edits` đều bị 4xx; bản hợp lệ 200. | Một tác giả đã xác thực vẫn có thể gửi HTML đủ thành phần nhưng sai nội dung; đây là kiểm tra cấu trúc, không phải sanitizer. |
| N08 | P2 | **Đã sửa** | Từ chối 413 mà không đọc body → RST làm client mất mã lỗi. | Khi từ chối sớm: đọc bỏ (không giữ trong bộ nhớ) body đã khai báo tới 64 MB rồi mới trả lỗi; lớn hơn thì trả 413 và đóng kết nối; thêm `timeout=20` chống kết nối treo. | Ca `F10+`: POST body 13 MB **gửi thật** nhận đúng 413; header khai báo 200 MB nhận 413. | Body >64 MB: client có thể vẫn thấy kết nối bị đóng sau khi nhận 413. |

## Siết bộ test (theo bảng nhận xét của Codex)

| Điểm yếu Codex nêu | Xử lý |
|---|---|
| `t_f03` chỉ gán `scrollTop`; helper "wheel thật" thực ra không cuộn | Xóa helper sai tên; thêm `t_f03_wheel` dùng `mouse.wheel` thật (2 trang × 320/375/390/720×450): đủ 12 đầu việc xuất hiện trọn trong vùng nhìn thấy. |
| `ORPHAN_JS` chỉ chọn H1/H2 có `data-i18n` | Đo **mọi** H1/H2 và `[data-tail]`; 756 phần tử vẫn đạt. |
| CTA/Hero: kết quả locale trước bị ghi đè bằng VI | Kiểm `br` + `span` cho **từng** locale. |
| Migration CV chỉ đổi thứ tự/sửa tag; không xóa thẻ | Thêm N01 (xóa thẻ giải pháp, 4 locale). |
| Node guard không thử văn bản trùng + kéo thẻ + xuất | Thêm N03. |
| Round trip không thử khóa trùng/brand | Thêm N02, N04. |
| Body lớn chỉ kiểm header khai báo | Thêm N08 với body gửi thật; giữ ca header 200 MB. |
| Static endpoint/backup/atomic chưa kiểm mã hóa, đồng thời | Thêm N05, N06 (có reader), N07. |
| Regex "KPI/lead" cho câu không cam kết | Kiểm đúng cụm cho từng locale (`không cam kết doanh thu/lead`, `no revenue/lead KPI commitments`, `sin compromiso de ingresos/leads`, `不承诺获客或营收 KPI`). |
| Focus ring chỉ kiểm `outlineStyle != none` | Yêu cầu độ rộng > 0 và không trong suốt (hoặc box-shadow thật). |
| SAFETY chỉ hash 7 file | Hash toàn bộ file tracked + untracked (`git ls-files -co`). |

## Kết quả chạy cuối (mã đúng như commit)

- `tests/regression/run_all.py` (đầy đủ, 6 viewport × 4 locale): **31/31 PASS**, gồm F01–F10, N01–N08, CONTENT, NAV, RESP, SAFETY.
- `tests/regression/native_zoom.py` (zoom Chromium 200% qua Preferences, `innerWidth=640`, `outerWidth=1280`, `dpr=2`, không emulation): **3/3 PASS**.
- `tools/sync_creators.py --check`: OK.

## Giới hạn còn lại

- Vẫn chỉ Chromium/Playwright; chưa có thiết bị cảm ứng thật, Firefox/Safari, WCAG 2.2 AA đầy đủ, bản in PDF native.
- Toolbar editor vẫn còn nhãn tiếng Việt cố định (Codex ghi nhận, không phải lỗi F01–F10/N01–N08).
- Chưa có audit độc lập lần 3 trên commit này.
