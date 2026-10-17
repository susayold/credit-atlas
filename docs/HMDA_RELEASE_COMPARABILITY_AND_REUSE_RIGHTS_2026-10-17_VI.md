# HMDA — đối chiếu release, mốc thời gian và quyền tái sử dụng

**Cập nhật:** 17/10/2026 · **Plan:** N02 / N03 · **Phạm vi:** release 2018–2025, code HMDA hiện có và hai trạng thái 2025 đã được receipt-bind.

## Kết luận thực dụng

HMDA không phải một panel được cập nhật theo cùng cách cho mọi năm. Theo FAQ chính thức, Data Browser chọn **latest available static dataset** cho từng activity year: Three-Year cho 2018–2022, One-Year cho 2023–2024 và Snapshot cho 2025. Dataset 2025 Dynamic là dòng phát hành riêng, được cập nhật hàng tuần, không phải lựa chọn mặc định của Data Browser. Tôi đã truy vấn nationwide aggregation API cho cả tám năm 2018–2025 theo đúng mapping đó; 4/4 release có local receipt cùng vintage khớp hết action counts, còn bốn năm 2019–2022 cho thấy mức nhạy cảm aggregate khi app One-Year archive được đặt cạnh Browser Three-Year.

Ứng dụng có archive One-Year 2019–2024 và giữ chúng riêng trong selector. Các archive 2019–2022 **khác** release mà Data Browser hiện dùng cho cùng activity year: ví dụ panel One-Year 2019 trong app lấy file freeze 05/04/2022, trong khi Data Browser chọn Three-Year freeze 31/12/2022. API comparison cho thấy Browser Three-Year minus local One-Year tổng action rows lần lượt +10.763, +32.298, +42.616 và +26.668 ở 2019–2022. Đây là khác biệt aggregate giữa vintage; không có row matching nên không gọi là hồ sơ unique mới hoặc bản ghi đã chuyển action. UI hiện đã nêu khác biệt release này.

So sánh hai trạng thái 2025 cùng activity year cho thấy Snapshot 02/06/2026 có 13.543.606 LAR rows; Dynamic capture 11/10/2026 có 13.558.306, tăng 14.700 rows. Denied share mô tả giảm từ 22,594841% xuống 22,571801%, tức −0,02304073 điểm phần trăm. Đây là chênh lệch giữa hai phiên bản công bố sau late submissions/resubmissions, không phải hồ sơ người vay chuyển trạng thái, không phải hiệu quả trả nợ và không phải PD.

CFPB công bố HMDA để phân tích và nói rõ dữ liệu công khai đã được sửa đổi nhằm bảo vệ riêng tư người nộp đơn/người vay. Một tài liệu CFPB về nguồn và cách sử dụng dữ liệu còn mô tả public data là nhóm được cung cấp cho mọi thành viên công chúng và dùng cho nhiều loại phân tích. Tuy vậy, các trang sản phẩm/FAQ/schema đã rà không nêu điều khoản riêng cho việc mirror raw LAR trong repository hoặc bundle sản phẩm. Vì vậy trạng thái dự án là: **public for analysis; quyền tái phân phối raw chưa được xác nhận riêng**. CreditAtlas tiếp tục để raw LAR và receipts chi tiết ở D:, chỉ phát hành code, phương pháp và aggregate; không suy ra quyền tái phân phối chỉ từ việc tải được file.

## Data Browser chọn nguồn nào theo năm?

FAQ của FFIEC/CFPB ghi Data Browser dùng sản phẩm static mới nhất có cho năm đó. Bảng dưới là mapping của Data Browser, không phải danh sách mọi archive hiện có trong CreditAtlas.

| Activity year | Static release Data Browser chọn | Freeze chính thức |
|---:|---|---|
| 2018 | Three-Year | 31/12/2021 |
| 2019 | Three-Year | 31/12/2022 |
| 2020 | Three-Year | 31/12/2023 |
| 2021 | Three-Year | 31/12/2024 |
| 2022 | Three-Year | 31/12/2025 |
| 2023 | One-Year | 19/05/2025 |
| 2024 | One-Year | 02/06/2026 |
| 2025 | Snapshot | 02/06/2026 |

Trong app, các archive One-Year 2019–2024 được giữ theo đúng freeze date của từng file. Riêng 2019–2022, archive One-Year khác release Three-Year mà Data Browser hiện chọn; 2023–2024 là One-Year như Browser chọn. Không gọi tất cả archive ấy cùng một release. File One-Year 2019 còn có cảnh báo của publisher rằng do thời điểm tạo file, vintage chứa **hơn 12 tháng cập nhật**; đó không phải cutoff 12 tháng chuẩn. 2025 Snapshot và Dynamic cũng là hai source IDs riêng, mỗi một source có capture date riêng.

## So sánh actual-data năm 2025

Audit script đọc hai receipt-bound aggregate views và đối chiếu action profile trong acquisition receipt. Mọi action count cộng đúng thành tổng LAR rows; mẫu số action 1+2+3 và action-3 numerator được tính lại; các chênh lệch action cộng lại bằng chênh lệch tổng rows. Script không đọc raw rows lần thứ hai và không xuất record-level data. Chi tiết public có tại [JSON so sánh 2025](data/hmda-2025-release-comparison-2026-10-17.json); source hashes và private paths nằm trong receipt riêng trên D:.

| Chỉ số | Snapshot · 02/06/2026 | Dynamic · 11/10/2026 12:00:30Z | Dynamic − Snapshot |
|---|---:|---:|---:|
| LAR rows | 13.543.606 | 13.558.306 | **+14.700** |
| Reporting institutions (distinct LEI) | 4.782 | 4.794 | **+12** |
| Mẫu số quyết định, action 1+2+3 | 9.360.942 | 9.373.448 | **+12.506** |
| Denied numerator, action 3 | 2.115.090 | 2.115.756 | **+666** |
| Denied share mô tả | 22,594841% | 22,571801% | **−0,02304073 pp** |

| Action | Nghĩa | Δ rows |
|---:|---|---:|
| 1 | Originated | +9.620 |
| 2 | Approved, not accepted | +2.220 |
| 3 | Denied | +666 |
| 4 | Withdrawn | +2.359 |
| 5 | Closed for incompleteness | +176 |
| 6 | Purchased | +1 |
| 7 | Preapproval denied | 0 |
| 8 | Preapproval approved, not accepted | −342 |
| **Tổng** |  | **+14.700** |

**Diễn giải:** Dynamic chứa thêm rows ở action 1–6 nhưng ít hơn 342 rows ở action 8. Điều đó phù hợp với khác biệt về late submission/resubmission và release state; không có stable borrower/application key trong audit này để kết luận một record cụ thể đã chuyển action. Định nghĩa chỉ số vẫn là `count(action_taken=3) / count(action_taken in 1,2,3)`, chỉ mô tả disposition của hồ sơ.

## Action counts của release mà Data Browser chọn, 2018–2025

Theo tài liệu API chính thức, nationwide aggregations endpoint là API powering Data Browser và trả JSON aggregate. Tôi gọi riêng từng activity year, chỉ yêu cầu action codes 1–8, rồi đối chiếu với acquisition/audit receipt local cho cùng năm. Mỗi action profile phải đủ 8 code; tổng actions phải khớp profile receipt. Kết quả 8/8 request pass; bốn release có cùng product trong local source (2018 Three-Year, 2023–2024 One-Year, 2025 Snapshot) khớp chính xác toàn bộ action counts. Với 2018, 1.961 raw rows có `action_taken=-1` không nằm trong domain action 1–8 và vẫn bị quarantine.

| Năm hoạt động | Browser chọn / freeze | Actions 1–8 | Mẫu số 1+2+3 | Denied action 3 | Denied share mô tả |
|---:|---|---:|---:|---:|---:|
| 2018 | Three-Year · 31/12/2021 | 15.138.510 | 10.623.751 | 2.552.640 | 24,027672% |
| 2019 | Three-Year · 31/12/2022 | 17.573.963 | 12.283.351 | 2.536.776 | 20,652149% |
| 2020 | Three-Year · 31/12/2023 | 25.699.043 | 18.184.354 | 2.886.263 | 15,872233% |
| 2021 | Three-Year · 31/12/2024 | 26.269.980 | 18.675.314 | 2.950.191 | 15,797277% |
| 2022 | Three-Year · 31/12/2025 | 16.125.975 | 11.361.613 | 2.525.024 | 22,224168% |
| 2023 | One-Year · 19/05/2025 | 11.564.178 | 8.058.391 | 2.037.094 | 25,279166% |
| 2024 | One-Year · 02/06/2026 | 12.259.199 | 8.661.779 | 2.103.462 | 24,284411% |
| 2025 | Snapshot · 02/06/2026 | 13.543.606 | 9.360.942 | 2.115.090 | 22,594841% |

Phần trăm được tính lại từ action 3 chia action 1+2+3; không lấy tỷ lệ làm tròn từ presentation. Đây là **series mô tả theo release mà Browser chọn hiện tại**, không phải panel vintage cố định. Đừng cộng row counts của nhiều năm thành số người/hồ sơ unique. Các năm có thay đổi reporting coverage, product mix, geography mix và release window; chuỗi chưa được chuẩn hóa composition/coverage và không phải causal trend hay risk performance. Từng API response/hash, eight action counts và đối chiếu local source ghi ở [JSON release audit](data/hmda-browser-selected-release-action-audit-2026-10-17.json); chạy lại bằng [audit script](../scripts/audit_hmda_browser_selected_release_comparability.py).

Dùng [workbook Excel release audit](../apps/excel/templates/CreditAtlas-HMDA-Browser-Release-Audit-2018-2025.xlsx) để lọc/đối chiếu các action counts, sáu archive One-Year, bốn cross-vintage deltas, lineage, định nghĩa và giới hạn nguồn. Workbook có năm sheet, 104 công thức; action counts và công thức KPI được đối chiếu với JSON rồi mở lại trong Excel 16.0 read-only, không lỗi công thức hoặc external links. Kết quả kiểm tra: [native Excel QA](data/hmda-browser-release-audit-native-excel-qa-2026-10-17.json). Workbook chỉ chứa aggregate, không có raw LAR.

### Đo trực tiếp sai khác của archive One-Year 2019–2022 so với Browser Three-Year

App đang lưu các archive One-Year 2019–2022, trong khi Browser chọn Three-Year cho cùng activity years. Bảng này trừ action counts của local One-Year khỏi API Three-Year hiện tại. Đây là so sánh hai tổng hợp cùng activity year nhưng khác vintage; không có row-level join, không khẳng định bao nhiêu hồ sơ là bổ sung hay đã sửa.

| Năm | Δ actions 1/2/3/4/5/6/7/8 · Three-Year trừ One-Year | Δ tổng actions | Δ mẫu số 1+2+3 | Δ denied | Δ denied share |
|---:|---|---:|---:|---:|---:|
| 2019 | +4.245 / −2.659 / +1.066 / +550 / +1.930 / +5.622 / +4 / +5 | +10.763 | +2.652 | +1.066 | +0,00422048 pp |
| 2020 | +7.759 / +36.311 / +6.020 / −43.436 / +4.993 / +20.456 / −8 / +203 | +32.298 | +50.090 | +6.020 | −0,01064505 pp |
| 2021 | +28.562 / −1.337 / +27.777 / +28.460 / −47.164 / +8.300 / −733 / −1.249 | +42.616 | +55.002 | +27.777 | +0,10251269 pp |
| 2022 | +9.721 / +3.396 / +24.813 / +8.770 / −44.229 / +13.441 / +2.425 / +8.331 | +26.668 | +37.930 | +24.813 | +0,14468237 pp |

Các chênh lệch action âm và dương cùng tồn tại, ví dụ 2020 có 43.436 fewer action-4 rows nhưng 36.311 more action-2 rows, và 2021/2022 có thay đổi đáng kể ở action 5. Vì vậy không mô tả chênh tổng như “late rows được cộng thêm”; đó là khác biệt giữa release-state totals có thể chứa resubmissions/reclassifications. Denied-share deltas nhỏ về điểm phần trăm nhưng vẫn có thể đổi khi population/decision mix đổi; phải chọn release definition trước khi so trend.

## Những thay đổi có thể làm lệch so sánh theo năm

- **Release window:** Three-Year gộp điều chỉnh nhiều năm sau reporting deadline; One-Year là một freeze sớm hơn; Snapshot là một ngày cut cố định; Dynamic có thể đổi sau từng tuần. Gắn mọi kết quả với product, freeze/as-of, retrieval/capture và source ID.
- **Coverage/reporting rules:** 2019 Filing Instructions Guide nói các data fields bắt buộc không đổi so với 2018. Tuy nhiên, quy định coverage vẫn thay đổi theo thời gian. Quy tắc năm 2020 đưa threshold closed-end lên 100 loans từ 01/07/2020, sau đó lệnh tòa tháng 09/2022 vacate mức tăng này và khôi phục threshold 25. Open-end threshold đổi sang 200 từ 2022; từ 2020, tổ chức có ít nhất 60.000 covered applications/loans năm trước phải nộp quarterly. Không diễn giải biến động số reporter/rows đơn thuần như biến động nhu cầu tín dụng hoặc risk.
- **Disclosure/privacy:** CFPB nói public LAR đã được chỉnh để bảo vệ applicant/borrower. `NA`, `Exempt`, blank, top-code và field availability cần giữ đúng nghĩa theo từng schema; không biến thành zero hay cùng một loại missing.
- **Data Browser parity:** Browser API là endpoint powering Browser UI; nó phục vụ theo static dataset đã chọn cho year, không phải nhất thiết archive mà app đang hiển thị. Mọi parity test phải ghi rõ nguồn so sánh, release, query filters, schema, action population và cutoff.

## Tình trạng quyền tái sử dụng

| Câu hỏi | Bằng chứng tìm được | Trạng thái trong CreditAtlas |
|---|---|---|
| Data có công khai cho phân tích không? | CFPB mô tả HMDA là public data và mời tải về cho phân tích; Data Publication nói dataset có thể dùng cho phân tích. | Có thể dùng cho phân tích theo nguồn và mục đích công bố; luôn gắn nguồn, release/freeze, và privacy caveat. |
| Public LAR còn phải sửa vì riêng tư không? | CFPB/FFIEC nói public data được modified để bảo vệ applicant và borrower. | Không cố reverse/reidentify; chỉ xuất aggregate khi không cần rows. |
| Có giấy phép rõ cho raw redistribution/hosting trong repo không? | CFPB nói public data dành cho public use/analysis; Regulation C yêu cầu công khai modified LAR. Tuy nhiên, nguồn này và các release/FAQ/schema pages đã rà không nêu điều khoản riêng cho việc rehost raw files trong repository hay bundle sản phẩm. | **Chưa xác nhận riêng**. Raw LAR, archive và receipt giữ private; không phát hành raw CSV/ZIP hoặc loan-level workbook. Aggregate đã kiểm duyệt và code/methods có thể phát hành với citation/privacy controls. |
| Có thể dùng tên/logo CFPB/FFIEC để quảng bá không? | Trang nghiên cứu dữ liệu không phải endorsement. | Không dùng logo hoặc gợi ý cơ quan chứng thực CreditAtlas. |

Đây là trạng thái quản trị dữ liệu của dự án, không phải ý kiến pháp lý hay tuyên bố rằng mọi dữ liệu công đều bị cấm tái sử dụng.

## Code hiện tại và bước tiếp theo

`apps/web/app.js` đã ghi rõ 2019–2022 app archives khác Data Browser Three-Year, và 2019 hơn 12 tháng cập nhật. Selector 2020–2022 cũng nêu Browser dùng Three-Year; summary có freeze dates cho từng One-Year archive. `src/credit_atlas/hmda_national_views.py` giữ snapshot/dynamic thành source IDs riêng. `apps/excel/build_hmda_dynamic_review.mjs` đã tính action deltas và tổng hợp hai trạng thái 2025; script audit mới xác nhận các tổng số đó bằng acquisition receipt action profiles.

| Việc N02/N03 còn mở | Điều kiện đóng |
|---|---|
| Release/source parity 2018–2025 | Từng route ghi product + freeze/as-of; mỗi public Browser comparison dùng đúng official selected static release; không trộn archive khác product. |
| Harmonize KPI qua thời gian | So sánh chỉ sau khi khóa population, denominator, field availability, coverage, action definitions và missing/Exempt handling. Mỗi break/change có source evidence. |
| Rights/use gate | Ghi status theo source product: public analysis support, explicit redistribution license (nếu có), privacy controls và public-release approval. Chưa rõ thì giữ private hoặc chỉ publish aggregate đã review. |
| Other KPI lineage | Mỗi KPI còn thiếu có source field → filter → numerator/denominator → unit/period → API/Excel trace. HMDA denial share không được biến thành repayment/default KPI. |

Không thêm forecast, imputation hoặc model result. Các việc nghiên cứu này không nâng ledger **26/50**.

## Nguồn chính thức đã rà

- [HMDA Dataset Filtering FAQ — Data Browser source mapping by year](https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq)
- [2018 Three-Year release — 36 months of updates, freeze 31/12/2021](https://ffiec.cfpb.gov/data-publication/three-year-national-loan-level-dataset/2018)
- [2025 Snapshot release](https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2025) · [2025 Dynamic release](https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset/2025)
- [CFPB HMDA data overview](https://www.consumerfinance.gov/data-research/hmda/) · [Regulation C §1003.5 disclosure](https://www.consumerfinance.gov/rules-policy/regulations/1003/5/) · [CFPB Sources and Uses of Data](https://files.consumerfinance.gov/f/documents/bcfp_sources-uses-of-data.pdf)
- [2019 Filing Instructions Guide](https://files.ffiec.cfpb.gov/documentation/2019-hmda-fig.pdf) · [2020 Filing Instructions Guide](https://files.ffiec.cfpb.gov/documentation/2020-hmda-fig.pdf)
- [CFPB 2020 Regulation C rule](https://www.consumerfinance.gov/rules-policy/final-rules/regulation-c-home-mortgage-disclosure-act/) · [2022 closed-end threshold vacatur](https://www.consumerfinance.gov/rules-policy/final-rules/hmda-reg-c-judicial-vacatur-of-coverage-threshold-for-closed-end-mortgage-loans/)
- [Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/)
