# Treasury HAMP Performance Supplemental — data review

**Checkpoint:** 17/10/2026. Đây là một nguồn phụ trợ về servicing/loss mitigation,
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

Đã đọc lại [trang dữ liệu MHA chính thức của Treasury](https://home.treasury.gov/data/troubled-assets-relief-program/reports/mha-public-file): trang mô tả bản tĩnh 2009–2017 và monthly update từ 2018-01 đến tháng công bố mới nhất. Link monthly trên trang là [HMP_Govt_Agency_Perf_Data.zip](https://home.treasury.gov/system/files/256/HMP_Govt_Agency_Perf_Data.zip). Kiểm tra HEAD ngày 2026-10-17 trả HTTP 200, `application/zip`, 75.367.977 bytes, Last-Modified `Wed, 19 Aug 2026 15:33:17 GMT`; các metadata này khớp acquisition receipt trên D: và SHA-256 của ZIP đã được tính lại, khớp `c3057bee9c94…`. ZIP có CSV member `HMP_Govt_Agency_Perf_Data_20220101_20230201.csv` và `.meta`; metadata ghi 9.872.074 records, còn audit trên CSV chỉ thấy 14 activity dates 2022-01–2023-02. Vì vậy đã xác nhận file đúng URL hiện hành, nhưng payload không cung cấp payment activity 2018–2021; giữ đây là phần chưa quan sát trong release, không suy là zero hay forecast.

Bản tĩnh 2009–2017 có link chính thức `https://mhadatafile.treasury.gov/Prod/reports/HMP_Govt_Agency_Perf_Data_20090101_20171201.zip`; lần kiểm HEAD mới hết timeout sau 25 giây. Đường dẫn thử trên `home.treasury.gov/system/files/256/` trả 404. Chưa có mirror byte-identical, nên chưa lấy được archive này. Kết quả hiện được lưu trong receipt private `local-private-id:treasury-hamp-linkage-20261017-070338:receipt`.

Profile bổ sung trực tiếp trên toàn bộ CSV 1,110,749,182-byte bằng DuckDB, chỉ xuất aggregate: 14 kỳ payment liên tiếp từ 2022-01 đến 2023-02, mỗi kỳ có hai trạng thái `Reported`/`Not Reported`:

| Activity period | Reported rows | Not Reported rows |
|---|---:|---:|
| 2022-01 | 392,746 | 203,734 |
| 2022-02 | 387,458 | 203,791 |
| 2022-03 | 375,319 | 211,037 |
| 2022-04 | 369,676 | 211,279 |
| 2022-05 | 363,966 | 212,501 |
| 2022-06 | 364,785 | 207,810 |
| 2022-07 | 326,636 | 241,907 |
| 2022-08 | 323,135 | 242,844 |
| 2022-09 | 321,770 | 241,405 |
| 2022-10 | 312,346 | 247,913 |
| 2022-11 | 314,418 | 243,665 |
| 2022-12 | 311,525 | 244,673 |
| 2023-01 | 305,527 | 248,541 |
| 2023-02 | 304,051 | 248,382 |

Các số trên là số dòng payment activity do Treasury công bố, không phải số borrower, không phải tỷ lệ trả đúng hạn, và không cho biết riêng nguyên nhân `Not Reported`. Cùng payload có modification effective dates từ 2009-07-01 đến 2017-12-01; đây là ngày hiệu lực của sửa đổi, không phải các kỳ payment activity bị thiếu. Coverage trước 2022 vẫn **unresolved**; không tạo zero, projection hay imputation.

## Quarterly cohort summaries bổ sung — không thay thế monthly activity

Trang [MHA Performance Report của Treasury](https://home.treasury.gov/data/troubled-assets-relief-program/reports/making-home-affordable-program-performance-report) nói các quarterly summary hiển thị tổng số HAMP permanent modifications đã bắt đầu và tỷ lệ delinquency theo loại chương trình, tại các mốc mà modification đã đạt hoặc vượt tuổi tháng được báo cáo. Trang hiện liệt kê 20 PDF từ 2018-Q1 đến 2023-Q1; **không có 2021-Q3**. Ngày phát hành trên trang và ngày dữ liệu “updated through” trong từng PDF được lưu riêng, không đồng nhất hai mốc này.

Đã tải 20 PDF từ host chính thức `home.treasury.gov` vào thư mục private trên D:, lưu SHA-256 từng file và kiểm tra mỗi file có đúng một trang, đúng báo cáo HAMP, ngày `Updated through` khớp source index. Parser đọc ba bảng: HAMP Tier 1, HAMP Tier 2, Streamline HAMP; giữ cohort effective-year 2009–2017 (Tier 1), 2012–2017 (Tier 2), 2016–2017 (Streamline) và bảy tuổi 6/12/24/36/48/60/72 tháng. Mỗi tuổi có hai chỉ số 60+ và 90+ delinquency.

Tạo được **2.485** dòng dạng report × program × cohort × tuổi tháng; trong đó **2.142** cặp tỷ lệ hiện diện trong PDF và **343** cặp vẫn trống vì không có giá trị ở bảng xuất bản. Không đổi trống thành 0, không nội suy theo tuổi/vintage, không backfill quý 3/2021. Các số trong bộ này được chép nguyên dạng phần trăm đã làm tròn đến một chữ số thập phân; không tự dựng numerator hay denominator.

Định nghĩa của Treasury có ảnh hưởng trực tiếp tới cách đọc số. Hướng dẫn trong báo cáo nói trạng thái payment không còn được servicer báo sau khi khoản vay bị disqualify ở 90+ ngày delinquent; các khoản đó vẫn được giữ trong 90+ metric của các kỳ tuổi tương lai, kể cả khi sau đó cured hoặc paid off. Ngược lại, khoản được ghi paid-off hoặc withdrawn không còn ở các kỳ tương lai. Vì vậy đây là các **snapshot cohort theo tuổi sửa đổi với mẫu số thay đổi**, không phải cumulative default probability, không phải PD dự báo, không phải transition/cure rate, và không thể ghép thành lịch sử payment loan-month. Report Q1 2023 còn ghi cụ thể các caveat này; Tier 1 “All” ở tháng 72 là 45,5% cho 60+ và 44,6% cho 90+.

Các file đầu ra hiện lưu local/private trên D:, chưa đưa aggregate CSV/XLSX vào public bundle. Workbook analyst gồm `Cohort KPIs`, `Source Index`, `Read Me`; có source URL, source hash, publication quarter, updated-through date, program segment, modification-year, tháng tuổi, hai tỷ lệ, cùng trạng thái blank. Test parser kiểm tra ngày cutoff, cohort set, quan hệ 90+ ≤ 60+ và giữ blank; spot-check các ô của PDF Q1 2018, Q2 2018, Q4 2022 và Q1 2023.

**Kết luận về khoảng trống:** ta đã bổ sung nguồn tổng hợp chính thức để mô tả hiệu quả HAMP theo tuổi cohort, nhưng chưa tìm được monthly loan activity 2018–2021 trong ZIP và chưa lấy được static 2009–2017 ZIP. Khoảng trống monthly vẫn mở; bảng quarterly không được dùng làm đại diện hay giá trị thay thế cho phần bị thiếu.

## Sử dụng trong CreditAtlas

### Dedicated HAMP cohort explorer — 17/10/2026

Đã nối riêng bộ quarterly aggregate đã kiểm tra vào local app qua
`src/credit_atlas/treasury_hamp_quarterly.py` và read-only route
`GET /api/treasury-hamp-quarterly`. Màn `?view=hamp` lọc publication quarter,
program segment, modification effective-year và modification age; hiển thị
snapshot trend khi giữ một segment/vintage/age cố định, bảng cohort, source URL,
updated-through date và SHA-256. Excel export theo đúng filter dùng route
`/api/treasury-hamp-quarterly-excel`, giữ blank trong các rate cell và kèm sheet
source index cùng method/limitations.

Màn hình không gộp rate qua nhiều vintage/chương trình và không tạo rate bình
quân giả. Tỷ lệ headline chỉ hiện khi chọn một segment, một vintage và một mốc
tuổi; nó luôn gắn với snapshot gần nhất trong phạm vi lọc. Missing 2021-Q3 tạo
khoảng trên chart. Nếu bộ dữ liệu private chưa được cài trong một workspace,
API trả trạng thái unavailable thay vì dựng dữ liệu mẫu. CSV cohort, PDFs và
analyst workbook vẫn nằm private trên D:; public checkout chỉ có source index,
code và method documentation.

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
- Monthly file downloader: `scripts/download_treasury_hamp_performance.py`
- Monthly aggregate-only auditor: `scripts/audit_treasury_hamp_source.py`
- Quarterly PDF downloader/parser: `scripts/download_treasury_hamp_quarterly_summaries.py` and `scripts/build_treasury_hamp_quarterly_summary.py`
- Quarterly source index: `docs/data/treasury-hamp-quarterly-summary-sources-2026-10-17.json`
- Focused tests: `tests/test_treasury_hamp_audit.py`, `tests/test_treasury_hamp_performance_audit.py`, `tests/test_treasury_hamp_quarterly_summary.py`

The current N02 register binds the Treasury archive, official guide and 20 quarterly PDFs as separate source records. The 20 quarterly PDFs now feed the separate local HAMP cohort explorer and filtered Excel export described above. The monthly loan-activity archive remains aggregate-audit-only and has no loan-level KPI route. This integration does not change the master 50-capability completion count.
The current **26/50 = 52% complete** and **42/50 = 84% with some implementation or
conditional coverage** remain unchanged; the new Treasury case is supplemental
evidence outside the Freddie D01 vintage/model acceptance gates.
