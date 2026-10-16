# HMDA National Dynamic 2025 — bản chụp cập nhật 11/10/2026

Checkpoint: 16/10/2026. Đây là phần mở rộng D08 cho nguồn đơn đăng ký và quyết
định underwriting. Nó không bổ sung repayment, delinquency, default hay PD cho
D01.

## Nguồn và phạm vi

FFIEC/CFPB công bố Dynamic National Loan-Level Dataset ở dạng pipe-delimited;
nguồn được cập nhật hàng tuần để nhận hồ sơ trễ và sửa đổi. Bản LAR được lưu
ngày 11/10/2026 lúc 12:00:30 UTC; Transmittal Sheet tương ứng có mốc 12:00:20
UTC. Tệp gốc được tải bằng HTTPS từ FFIEC, không dùng phiên hoặc thông tin đăng
nhập.

| Tệp | Nội dung được kiểm tra |
|---|---|
| 2025 LAR Dynamic | 13.558.306 dòng, 99 trường, 4.794 LEI; hoạt động 2025 trên mọi dòng |
| 2025 TS Dynamic | 4.794 tổ chức duy nhất; tổng `lar_count` bằng chính xác 13.558.306 |
| ZIP LAR | 736.787.013 byte; SHA-256 `85917596e5cb6546fab392e786e4366fd5be117d1c6d38dc18029a3f05d0cd1d`; CRC thành viên đạt |
| CSV sau giải nén | 5.120.169.808 byte; SHA-256 `7b5eb182b2eba54a5b5037595acf2cd07d0eca064cd9e6936f895ace3d712818` |
| TS ZIP | 191.918 byte; SHA-256 `e0a74c86bcedd053e5bc394d662d885fe8bb2cd9dd5c780a09b95b46fb19c2e6` |

Kiểm tra dữ liệu: schema 99 trường; activity year, action code 1–8, state code,
loan type 1–4, định dạng LEI và loan amount có **0 ngoại lệ**. Archive, member
size, CRC và hash được xác minh. Mọi giá trị được đọc dạng text để giữ nguyên
mã phân loại nguồn. Tệp TS chứa thông tin tổ chức; các dòng tổ chức và tax ID
không được đưa vào workbook hoặc app.

## Kết quả mô tả

Mẫu số decision rate giữ nguyên hợp đồng `action_taken` 1+2+3. Ở bản Dynamic,
9.373.448 hồ sơ thuộc mẫu số này, trong đó 2.115.756 action 3; denied share là
**22,5718%**. Đây là tỷ trọng quyết định từ chối trong tập hồ sơ đã quyết định,
không phải xác suất vỡ nợ.

| Action | Ý nghĩa | Snapshot 02/06 | Dynamic 11/10 | Chênh lệch |
|---:|---|---:|---:|---:|
| 1 | Originated | 6.827.891 | 6.837.511 | +9.620 |
| 2 | Approved, not accepted | 417.961 | 420.181 | +2.220 |
| 3 | Denied | 2.115.090 | 2.115.756 | +666 |
| 4 | Withdrawn | 1.710.723 | 1.713.082 | +2.359 |
| 5 | Closed for incompleteness | 695.006 | 695.182 | +176 |
| 6 | Purchased loan | 1.578.064 | 1.578.065 | +1 |
| 7 | Preapproval denied | 50.499 | 50.499 | 0 |
| 8 | Preapproval approved, not accepted | 148.372 | 148.030 | −342 |
| **Tổng** | | **13.543.606** | **13.558.306** | **+14.700** |

Denied share của Snapshot là 22,5948%; bản Dynamic là 22,5718%, giảm khoảng
0,0230 điểm phần trăm. Đây là so sánh hai trạng thái phát hành của cùng năm dữ
liệu, không phải phép ghép borrower-level. Thay đổi có thể phản ánh hồ sơ nộp
trễ, resubmission và thiết kế snapshot khác nhau; không thể diễn giải là người
vay chuyển trạng thái hoặc chất lượng tín dụng đã thay đổi.

## Tích hợp CreditAtlas và Excel

`scripts/acquire_hmda_dynamic_2025.py` tải và audit bản chụp được chốt theo
`Last-Modified`; nếu nhà xuất bản thay bản, script dừng thay vì ghi đè hoặc gắn
nhầm ngày. `src/credit_atlas/hmda_national_views.py` xác minh receipt, archive,
schema, TS reconciliation và hash trước khi phục vụ. Dữ liệu LAR giải nén tạm
trong bước aggregate rồi bị xóa; raw ZIP và receipt riêng giữ ở D:.

Trang HMDA national cho phép chuyển giữa Snapshot 02/06 và Dynamic 11/10. Hai
view dùng cùng 14 breakdown dimensions và cùng mẫu số. App chỉ trả aggregate đã
kiểm chứng; không trả các dòng hồ sơ gốc. Excel riêng có năm sheet: Overview,
Action compare, Dynamic detail (đầy đủ **8.156 category buckets**), Field
dictionary (99 trường, định nghĩa và category chính thức), Sources & method.
Workbook chỉ chứa số tổng hợp/codebook và provenance, không có LAR hay dòng TS.
Browser acceptance trên app thật đạt **21/21 checks, 0 browser errors**; bao
gồm chọn Dynamic/Snapshot, JSON/Excel downloads khớp byte, các panel One-Year
2019–2024 và bảng so sánh năm-release, denial-reason mapping, cùng summary ở
viewport 390px. Receipt private:
`D:\data\Codex\credit-atlas\artifacts\private\hmda-national-browser-qa-9fa5ed6e2f65\receipt.json`.

Tệp gốc, receipt và workbook riêng tư được đặt tại
`D:\data\Codex\credit-atlas\data\private\hmda\hmda-national-dynamic-2025-20261011`.
Chúng không được đưa lên GitHub.

## Giới hạn và thứ tự ưu tiên

- HMDA là nguồn application/origination và action; không có lịch sử trả nợ.
- Không ghép HMDA với Freddie/Fannie/Ginnie; không tạo feature hay label PD từ
  denial share.
- Không có forecast, nội suy, imputation hoặc model fit trong phần này.
- D01 vẫn có một vintage Freddie 2012. R2/R3 tiếp tục chờ vintage monthly
  performance bổ sung và protocol nhiều vintage.
- Tiếp tục D08 bằng acceptance/export theo release; song song ưu tiên Freddie
  Clarity, sau đó Ginnie nếu phiên tải được cung cấp.

## Tài liệu chính thức

- [FFIEC Dynamic National Loan-Level Dataset](https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset/2025)
- [HMDA file-serving documentation](https://ffiec.cfpb.gov/documentation/api/file-serving/)
- [Official HMDA frontend dynamic dataset manifest](https://raw.githubusercontent.com/cfpb/hmda-frontend/master/src/data-publication/constants/dynamic-dataset.js)
- [Official HMDA LAR field definitions](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/)
