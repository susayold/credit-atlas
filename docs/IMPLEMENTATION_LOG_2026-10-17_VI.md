# CreditAtlas — nhật ký triển khai theo plan mới

Ngày cập nhật: **17/10/2026**. Plan tổng và thứ tự N01–N24: [PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md](PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md).

## Đợt đang thực hiện: N01–N03

### N01 — tiến độ dùng chung

- Thêm API `GET /api/project-register`; tổng 50 yêu cầu và tỷ lệ hoàn thành được tính từ `COMPLETION_REQUIREMENTS_50.json`, không gõ riêng số tổng vào UI.
- UI có tổng P1–P5 và D01 R0–R4 ở hai khối riêng. Phần trăm hiển thị chỉ là tỷ trọng capability acceptance của toàn CreditAtlas.
- Completion flags của ledger không đổi. API giữ scope note để giải thích điều kiện còn lại của từng capability.

### N02 — danh mục nguồn dữ liệu

- Tạo catalog ban đầu gồm **24 nhóm dữ liệu trọng tâm**, có domain, grain, kỳ, trạng thái acquisition/audit, quyền truy cập, mục đích, giới hạn, bước tiếp và đường dẫn evidence/nhà phát hành.
- Phân biệt Freddie annual samples đang chờ authenticated access, Ginnie production chưa tải, dữ liệu exposure private và nguồn public đã audit.
- Đây chưa phải census mọi raw source trong workspace và chưa map đủ mọi KPI trong app. Việc nối từng receipt/source version và kiểm tra rights theo từng release tiếp tục trong N02.

### N03 — provenance và phương pháp

- Ghi nhận bảy loại giá trị: reported, derived, publisher-imputed, model-preprocessing-imputed, model prediction, declared scenario và forecast.
- Thêm tám method cards gắn dataset, target, cách tính/protocol, validation đã lưu, giới hạn và model/data evidence. Các card bao gồm D01 transitions, UCI350, UCI365, NMDB, HMDA fixed-mix, P4 scenario/ECL và Toyota/Nissan reconciliation.
- Các giả định P4 hiển thị đúng scope illustrative: lịch bullet 36 tháng, monthly EIR 0,004, weights 0,7/0,3; source expected loss vẫn unavailable. Không tạo biến dự phóng mới.
- N03 vẫn đang làm: mọi KPI/output số trên toàn app chưa được liên kết tới method ID và input lineage ngay trong view.

## Giao diện

Trang **Tiến độ & registry** trong điều hướng chung hiển thị capability acceptance, D01 releases, dataset filters, quyền truy cập, method cards và giới hạn. Register JSON có thể tải xuống. Không đưa raw borrower rows hoặc private exposure values vào catalog.

Workbook plan ở `docs/reviews/` đã cập nhật trạng thái N01–N03 thành **Đang làm** và ghi cụ thể phần còn lại; không đổi tỷ lệ acceptance 26/50.

## Trạng thái kiểm tra

JSON và Python/JavaScript cú pháp được parse, `git diff --check` sạch. Thay đổi app/API ở lượt này **chưa chạy test suite, browser acceptance hoặc Excel native check**. Vì vậy các mục N01–N03 chưa được đánh dấu nghiệm thu cuối; cần kiểm tra API/UI trên app đang chạy rồi xử lý lỗi/UX trước khi đóng. Lượt trước có public regression riêng 1.670 passed/196 skipped; kết quả đó có trước các thay đổi này và không kiểm chứng code mới.

## Bước kế tiếp

1. Kiểm tra page/API mới trong app local và sửa lỗi hiển thị/response nếu có.
2. Mở rộng N02 từ 24 nhóm trọng tâm tới nguồn thực sự cấp dữ liệu cho mỗi KPI, bind release/hash receipt khi có.
3. Nối KPI outputs vào method cards, gồm numerator/denominator, data release/as-of, formula và missingness; giữ các score/final holdout đã freeze nguyên trạng.
4. Sau khi registry dùng được, chuyển sang N05/N06: canonical NMDB mart cho origination/outstanding, tích hợp app và workbook parity.
