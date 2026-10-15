# Freddie Mac — tài liệu đối chiếu loss và acquisition

Đã lưu hai file chính thức tại `data/private/mortgage/freddie-public-reference-747d99d79cf2`, receipt trạng thái `PARTIAL_ACQUIRED`: PDF 528.043 bytes, HTML 88.844 bytes. Endpoint eMBS lỗi DNS; `failed.json` giữ chi tiết. Không thêm annual vintage.

[General User Guide](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf) gồm 23 trang, ghi January 2026. Trang 20–21 mô tả actual-loss components, cập nhật trailing recovery/expense, và modification costs tách riêng. Expense có convention dấu âm; không đổi dấu hoặc fill missing thành zero theo trực giác. Công thức publisher trừ expense đã mang dấu. Phải đối chiếu corpus và dictionary version trước khi áp vào P2.09.

Example 9 có khác biệt UPB giữa bảng và dòng arithmetic; không lấy ví dụ làm expected value tuyệt đối. Audit phải dùng số nguồn cụ thể và giữ residual.

[Thông báo December 2025](https://capitalmarkets.freddiemac.com/clarity/whats-new/december-2025-clarity-updates) nêu từ Release 46, cập nhật SFLLD chỉ qua Clarity. Receipt retrieval time không là publication time của ZIP.

Hai nguồn không xác thực release47 của ZIP đã cung cấp, không chứng minh historical recovery cashflow timing, không tạo qualified LGD/ECL hoặc mở model gate. P2.09 còn cần audit toàn bộ corpus và UI/export.

## Cập nhật kiểm tra Release 47 — 15/10/2026

Tải thêm bộ [Release 47 Sample Files](https://www.freddiemac.com/fmac-resources/research/docs/release-47-sample-files.zip) và [File Layout có hiệu lực tháng 07/2026](https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx) từ link chính thức của Freddie Mac. Các file được giữ nguyên/hash trong `data/private/mortgage/freddie-public-reference-f317b6c98c28/`; downloader giới hạn kích thước, kiểm CRC ZIP/XLSX và ghi receipt. Đây là public format references; số annual vintages mới vẫn là **0**.

So sánh bằng audit có thể tái tạo: layout mô tả 31 field origination và 35 field monthly performance; mọi dòng trong hai example text files lần lượt có đúng 31 và 35 cột. Origination example có 1.000 dòng/1.000 Loan Identifier; performance example có 1.011 dòng/12 Loan Identifier và 320 tháng, từ 199902 đến 202509. **Giao nhau giữa hai tập Loan Identifier là 0**, vì vậy không ghép hai file thành panel. Những file này chỉ giúp kiểm tra parser/cột ở mức mẫu minh họa, không phải 50.000-loan annual sample, không chứng minh release identity của ZIP 2012 đã dùng, và không đủ để rà lại schema availability của toàn bộ sample.

Receipt: [Release 47 reference audit](../artifacts/private/freddie-release47-reference-audit-c3ce87022b8b/audit.json). Tạo lại bằng `scripts/acquire_freddie_public_reference.py` rồi `scripts/audit_freddie_release47_reference_samples.py`. Các annual loan-level samples vẫn yêu cầu đăng ký/đăng nhập Clarity; lượt tải này không bypass authentication, không nhận terms thay người dùng và không chạy model.
