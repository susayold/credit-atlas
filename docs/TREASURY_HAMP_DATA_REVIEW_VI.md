# Treasury HAMP Performance Supplemental — data review

**Checkpoint:** 16/10/2026. Đây là một nguồn phụ trợ về servicing/loss mitigation,
được giữ tách khỏi Freddie D01 và không làm thay đổi số vintage Freddie.

## Nguồn và phạm vi

Trang Making Home Affordable của U.S. Treasury mô tả HAMP Performance
Supplemental File là các cập nhật về trạng thái sửa đổi khoản vay và hoạt động
thanh toán hàng tháng cho các sửa đổi hoàn tất thuộc HAMP, Treasury FHA-HAMP và
RD-HAMP. File do servicer báo cáo; Treasury yêu cầu người dùng đọc hướng dẫn về
chất lượng/biến thiên dữ liệu và không xác nhận phân tích bên ngoài.

- [Treasury MHA data files](https://home.treasury.gov/data/troubled-assets-relief-program/reports/mha-public-file)
- [HAMP Performance Supplemental User Guide, March 2018](https://home.treasury.gov/system/files/136/HAMP%20Performance%20Supplemental%20Data%20File%20User%20Guide%20v1.0.pdf)
- Archive đã lấy từ nguồn Treasury: `HMP_Govt_Agency_Perf_Data.zip`
- Kích thước archive: 75,367,977 bytes. SHA-256 prefix: `c3057bee9c94`.
- CSV member: 1,110,749,182 bytes; SHA-256 prefix: `d3817a3ed78a`.
- Bản đầy đủ, receipt và dữ liệu cấp khoản vay chỉ lưu trong thư mục private trên D:.

Hướng dẫn Treasury phân biệt một dòng `Modification Information` cho mỗi sửa
đổi và có thể nhiều dòng `Payment Information` theo từng tháng. Khóa công bố là
`Record Type, Financial Asset ID, Activity Period`. Hoạt động chỉ xuất hiện khi
việc báo cáo hoạt động được yêu cầu trong khoảng ngày tương ứng.

## Audit quan sát được

Audit đọc ZIP theo streaming, so metadata recordCount với CSV, xác nhận đúng 15
cột theo thứ tự nguồn, đếm domain, kiểm tra ID rỗng và nhóm khóa chính trùng.
Query chạy bằng DuckDB với giới hạn bộ nhớ 1 GB; chỉ ghi aggregate vào receipt,
không xuất loan IDs hoặc payment rows.

| Kiểm tra / thống kê | Kết quả |
|---|---:|
| Dòng CSV / Treasury `recordCount` | 9.872.074 / khớp chính xác |
| Modification Information | 1.889.234 |
| Payment Information | 7.982.840 |
| Loan IDs khác nhau, aggregate | 1.830.654 |
| Modification IDs khác nhau | 1.889.234 |
| ID rỗng / nhóm khóa chính trùng | 0 / 0 |
| Record type ngoài danh mục / loan state ngoài danh mục / reporting status ngoài danh mục | 0 / 0 / 0 |
| Modification effective date quan sát được | 2009-07-01 đến 2017-12-01 |
| Payment activity period quan sát được | 2022-01-01 đến 2023-02-01, 14 tháng |

Trên 1.889.234 dòng modification: Disqualified 844.245 (44,7%), Active Payment
550.742 (29,2%), Paid Off 446.669 (23,6%), Withdrawn 47.578 (2,5%). Đây là trạng
thái sửa đổi theo danh mục Treasury, không phải delinquency bucket hoặc default
label.

Trên 7.982.840 dòng payment activity: Reported 4.773.358 (59,8%), Not Reported
3.209.482 (40,2%). `Not Reported` là tình trạng thiếu báo cáo hoạt động theo
guide, không được đổi thành late payment/default. Tỷ lệ trên là phần dòng báo
cáo, không phải phần khoản vay default.

## Khoảng trống cần đóng trước khi phân tích theo thời gian

Trang Treasury liệt kê bản tĩnh 2009–2017 và monthly update 2018–February 2023.
Archive đã tải có member `HMP_Govt_Agency_Perf_Data_20220101_20230201.csv`; audit
thực tế chỉ thấy activity period từ 2022-01 đến 2023-02. Hướng dẫn nói activity
chỉ được đưa vào khi reporting được yêu cầu trong khoảng ngày, nên không thể suy
ra rằng 2018–2021 là zero, không có khoản vay, hoặc không có vỡ nợ. Phải giữ là
**chưa quan sát trong archive đã kiểm tra**.

Trang Treasury chính thức xác nhận file tĩnh 2009–2017 là activity từ program inception đến 2017-12; URL dẫn tới `https://mhadatafile.treasury.gov/Prod/reports/HMP_Govt_Agency_Perf_Data_20090101_20171201.zip`. Lượt kiểm ngày 2026-10-17 timeout cả khi mở link qua browser research và khi gọi `curl` trực tiếp (connection timeout sau 10 giây). Chưa tìm được mirror được xác minh là bản sao byte-identical chính thức, nên không tải từ nguồn thứ cấp. Tiếp tục thử lại endpoint Treasury; sau khi có file, kiểm hash/metadata và profile activity periods trước khi đánh giá khả năng nối các giai đoạn. Nguồn Treasury mô tả monthly update bắt đầu 2018-01; local archive hiện chỉ có 2022-01–2023-02.

## Sử dụng trong CreditAtlas

Nguồn này phù hợp để nghiên cứu lịch sử loss mitigation sau sửa đổi, trạng thái
modification và completeness của payment reporting. Nó **không** đại diện cho
mọi hồ sơ xin vay/origination, không phải sample Freddie bổ sung, và không nên
ghép loan-level với Freddie/Ginnie/Fannie nếu chưa có crosswalk hợp lệ.

Không có biến nào được dự phóng, nội suy, điền thiếu hay biến đổi thành nhãn
default. Không fit model. Hiện chưa lập KPI cure/default/LGD từ `Not Reported`.
Trước khi định nghĩa outcome cần nghiên cứu chi tiết ý nghĩa của `Loan State`,
`Last Paid Installment Date`, các kỳ không báo cáo, competing events và
right-censoring theo guide/servicer convention; sau đó mới thiết kế time origin,
risk set, horizon và backtest trên dữ liệu có coverage phù hợp.

## Excel và reproducibility

Workbook nội bộ tổng hợp audit, dictionary 15 trường, category values, observed
counts và source coverage. CSV gốc có hơn 9,8 triệu dòng, vượt giới hạn 1.048.576
dòng mỗi worksheet Excel nên được giữ CSV/Parquet riêng; workbook không chép
loan-level rows.

- Audit receipt: aggregate-only private receipt dated 2026-10-17; no acquisition timestamp receipt was found, so retrieved-at stays null.
- Downloader: `scripts/download_treasury_hamp_performance.py`
- Aggregate-only auditor: `scripts/audit_treasury_hamp_source.py`
- Focused tests: `tests/test_treasury_hamp_audit.py`

The current N02 register binds the Treasury archive and official guide as two separate source records. The application still has no dedicated HAMP KPI route. This source addition does not change the master 50-capability completion count.
The current **26/50 = 52% complete** and **42/50 = 84% with some implementation or
conditional coverage** remain unchanged; the new Treasury case is supplemental
evidence outside the Freddie D01 vintage/model acceptance gates.
