# Báo cáo xác minh — W17_04_Porfolio_Codex

Ngày 2026-11-14. Người phụ trách chính và người kiểm tra: Codex.

**Code/UI audit verdict: AUDIT_PASS.** Kết quả dưới đây được kiểm tra trên bản mới; báo cáo W17_02 trong docs/audits chỉ là lịch sử bản nguồn.

## Kết quả sản phẩm

- Định vị: Operations Automation & Data Reporting Specialist, đồng bộ portfolio, CV và Creator ở VI / EN / ES / ZH.
- Bốn dịch vụ nêu nhóm khách, vấn đề, phạm vi và bàn giao: automation / đối soát, BI / reporting, website / form, GA4 / GTM.
- Bổ sung quy trình khảo sát → pilot có phí / kiểm thử → bàn giao / hỗ trợ, có CTA đến phần liên hệ đang hoạt động.
- Bỏ lời hứa chung giảm 80–90% thao tác / chi phí và hosting gần như miễn phí; chốt phạm vi và chi phí theo từng dự án.
- Giữ dashboard, bốn ứng dụng minh chứng, editor, lưu / xuất Final và điều hướng hai chiều.
- Có playbook nội bộ về nhóm khách, kênh tìm việc, từ khóa, tin nhắn, proposal và thử nghiệm 30 ngày.

## Các file thay đổi so với bản nguồn

- index.html, index_portfolio_clean.html: dịch vụ, định vị, metadata, nội dung liên hệ và namespace lưu trữ w17_04.
- editor_workspace/editor_portfolio.html, editor_cv.html: sinh lại từ Final bằng sync_creators.py.
- README.md, dev_server.py: tên và quyền phụ trách dự án mới; hướng dẫn chạy và xác minh.
- docs/SALES_PLAYBOOK.md và docs/verification/2026-11-14/: hướng dẫn tìm khách và bằng chứng.
- tests/regression/: kỳ vọng nội dung mới, kiểm tra pilot / CTA, bảo vệ cache W17_02, fixture độc lập, cache tài nguyên CDN thật và hash an toàn loại trừ kết quả được sinh.
- tests/fixtures/: dữ liệu kiểm thử serialization cũ, không yêu cầu lịch sử Git hay folder W17_02 khi chạy lại.

## Kiểm tra tự động

Lệnh: python -X utf8 tests/regression/run_all.py --shots docs/verification/2026-11-14/final-regression

**36/36 PASS**, mã thoát 0. Kết quả đầy đủ: [results.json](final-regression/results.json).

| Hạng mục | Bằng chứng đã quan sát |
|---|---|
| Creator / Final và i18n | Đồng bộ từ điển, HTML tĩnh VI, bốn locale, metadata và accessible names |
| Cache riêng | Không đọc / ghi đè dữ liệu chỉnh sửa và tùy chọn W17_02; namespace w17_04 |
| Pilot / CTA | Ba bước đủ nội dung ở bốn locale, hero / pilot trỏ đúng phần liên hệ |
| Modal dịch vụ | 224 tổ hợp: 2 trang × 7 viewport × 4 locale × 4 dịch vụ; đủ 12 đầu việc đọc / cuộn được |
| Bàn phím / cuộn | Enter, focus trap, PageUp/PageDown, Escape trả focus; mouse.wheel thật |
| Typography | 852 phần tử H1 / H2 / hero, không orphan và có text-wrap: balance |
| Toolbar | 24 tổ hợp trang / viewport; nút Lưu không bị cắt / che và ghi được file thật |
| Lưu / xuất | Chỉnh sửa, server thật, xuất, mở lại với / không cache, đổi locale, điều hướng hai chiều; không còn UI editor trong Final |
| Dữ liệu chỉnh sửa | Snapshot an toàn, thẻ đã xóa không sống lại, node trùng không mất / nhân chỉnh sửa |
| Server | Same-origin / token, allowlist, payload limits, percent encoding, ghi đồng thời, backup và từ chối HTML không hợp lệ |
| Responsive | 96 tổ hợp: 4 trang × 6 viewport × 4 locale; không tràn ngang và không dùng overflow-x:hidden để che |
| Bảo toàn mã nguồn | Hash trước / sau chạy test bằng nhau; manifest chuẩn hóa UTF-8 / LF vẫn khớp |

## Native zoom và kiểm tra trực quan

Native zoom: **3/3 PASS**, thực sự áp dụng 200%: innerWidth=640, outerWidth=1280, devicePixelRatio=2; không dùng emulation viewport / DPR để thay thế.

Đã xem ảnh thực tế tại 320 / 375 / 390 / 768 / 1024 / 1440px, có mẫu VI / EN / ES / ZH, giao diện sáng / tối, hero, dịch vụ, pilot, CV và modal. Không quan sát thấy nội dung bị cắt hoặc tràn ngang trong các ảnh đã duyệt.

- [Contact sheet 320 / 768 / 1024](content/additional-viewport-contact-sheet.png)
- [Hero EN desktop](content/hero-en-1440.png)
- [Dịch vụ EN desktop](content/services-en-1440.png)
- [Pilot mobile](content/pilot-en-375.png)
- [Pilot light](content/pilot-en-1440-light.png)
- [Modal 200% đã chụp lại](zoom/ZOOM200-native-modal-top.png)
- [Creator CV 200%](zoom/ZOOM200-native-creator-cv.png)
- [Kết quả native zoom](native-zoom-results.json)
- [Phạm vi review trực quan](visual-review.json)

Một số lần chụp headless ở native zoom và vị trí trang nền khác 0 cho ảnh trống dù DOM hiện đúng. Đã loại ảnh trống; chụp lại modal với trang nền scrollY=0, giữ nguyên mức zoom 200% và trạng thái modal, rồi xem ảnh thực tế. Không dùng ảnh trống làm bằng chứng PASS.

## Tính độc lập và điều chỉnh bộ test

Git của bản sao đã được bỏ theo yêu cầu của Thảo; git init -b main tạo lịch sử mới. Origin chỉ trỏ https://github.com/teoteo1081/W17_04_Porfolio_Codex.git. W17_02 được kiểm tra lại: sạch, HEAD 9a37799, không sửa file nguồn.

Các lần chạy đầu là chẩn đoán, không phải kết quả cuối: test kế thừa đọc commit nguồn, có timeout tải CDN và có thay đổi harness / ảnh bằng chứng trong lúc kiểm tra hash. Đã thay đọc lịch sử bằng fixture tự chứa, cache đúng nội dung HTTPS của thư viện / font (không mock), loại kết quả sinh ra khỏi hash và chạy lại toàn bộ sau khi đóng băng mã nguồn. Nhánh kiểm tra an toàn vẫn hash cả mã ứng dụng và mã test; không bỏ qua lỗi chức năng.

Checksum tài nguyên thật: [cdn-asset-checksums.json](cdn-asset-checksums.json). Hash mã nguồn đã kiểm: [application-sha256.json](application-sha256.json). File chẩn đoán cũ được đánh dấu trong diagnostics, không dùng để kết luận bản cuối.

## Giới hạn

Kiểm tra trên Chromium / Windows, chưa thử thiết bị cảm ứng thật hoặc audit đầy đủ bằng công nghệ hỗ trợ. Trang dùng CDN nên cần mạng để tải thư viện và font. Form liên hệ mở ứng dụng email; không tự gửi email hoặc lưu lead trên server. Telemetry và các demo giữ dữ liệu / trạng thái kế thừa, không được trình bày ở báo cáo này như kết quả kinh doanh mới.

Phạm vi bàn giao lên GitHub là repository mã nguồn độc lập. Root commit, tip remote và trạng thái sạch được đối chiếu tại bước commit / push cuối.
