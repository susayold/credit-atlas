# HMDA — đối chiếu release, mốc thời gian và quyền tái sử dụng

**Cập nhật:** 17/10/2026 · **Plan:** N02 / N03 · **Phạm vi:** release 2018–2025, code HMDA hiện có và hai trạng thái 2025 đã được receipt-bind.

## Kết luận thực dụng

HMDA không phải một panel được cập nhật theo cùng cách cho mọi năm. Theo FAQ chính thức, Data Browser chọn **latest available static dataset** cho từng activity year: Three-Year cho 2018–2022, One-Year cho 2023–2024 và Snapshot cho 2025. Dataset 2025 Dynamic là dòng phát hành riêng, được cập nhật hàng tuần, không phải lựa chọn mặc định của Data Browser.

Ứng dụng có một số archive One-Year 2019–2022 và giữ chúng riêng trong selector. Các archive này **khác** release mà Data Browser hiện dùng cho cùng activity year: ví dụ panel One-Year 2019 trong app lấy file freeze 05/04/2022, trong khi Data Browser chọn Three-Year freeze 31/12/2022. UI hiện đã nêu khác biệt này; không đối soát tổng One-Year 2019 với tổng Three-Year hiện tại như thể cùng một file.

So sánh hai trạng thái 2025 cùng activity year cho thấy Snapshot 02/06/2026 có 13.543.606 LAR rows; Dynamic capture 11/10/2026 có 13.558.306, tăng 14.700 rows. Denied share mô tả giảm từ 22,594841% xuống 22,571801%, tức −0,02304073 điểm phần trăm. Đây là chênh lệch giữa hai phiên bản công bố sau late submissions/resubmissions, không phải hồ sơ người vay chuyển trạng thái, không phải hiệu quả trả nợ và không phải PD.

CFPB công bố HMDA để phân tích và nói rõ dữ liệu công khai đã được sửa đổi nhằm bảo vệ riêng tư người nộp đơn/người vay. Các trang release/FAQ đã rà không nêu một giấy phép tái phân phối tổng quát cho raw LAR. Vì vậy trạng thái dự án là: **được nhà phát hành cung cấp công khai để phân tích; điều khoản cấp phép tái phân phối raw chưa được xác nhận**. CreditAtlas tiếp tục để raw LAR và receipts chi tiết ở D:, chỉ phát hành code, phương pháp và aggregate đã khử dữ liệu; không suy ra quyền tái phân phối chỉ từ việc tải được file.

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

Trong app, panel 2019–2022 đang hiển thị archive One-Year riêng với freeze date của chính file. Không thay các archive ấy bằng Data Browser response hoặc gọi chúng cùng một release. File One-Year 2019 còn có cảnh báo của publisher rằng do thời điểm tạo file, vintage chứa **hơn 12 tháng cập nhật**; đó không phải cutoff 12 tháng chuẩn. 2025 Snapshot và Dynamic cũng là hai source IDs riêng, mỗi một source có capture date riêng.

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
| Có giấy phép rõ cho raw redistribution/hosting trong repo không? | Không tìm thấy license grant cụ thể trên các release/FAQ/schema pages đã kiểm tra; Regulation C về public disclosure không tự thay cho license notice của từng artifact trong phần nghiên cứu này. | **Chưa xác nhận**. Raw LAR, archive và receipt giữ private; không phát hành raw CSV/ZIP hoặc loan-level workbook. Nếu cần phân phối raw qua sản phẩm, phải xác nhận với nguồn/điều khoản áp dụng trước. |
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
- [CFPB HMDA data overview](https://www.consumerfinance.gov/data-research/hmda/) · [Regulation C §1003.5 disclosure](https://www.consumerfinance.gov/rules-policy/regulations/1003/5/)
- [2019 Filing Instructions Guide](https://files.ffiec.cfpb.gov/documentation/2019-hmda-fig.pdf) · [2020 Filing Instructions Guide](https://files.ffiec.cfpb.gov/documentation/2020-hmda-fig.pdf)
- [CFPB 2020 Regulation C rule](https://www.consumerfinance.gov/rules-policy/final-rules/regulation-c-home-mortgage-disclosure-act/) · [2022 closed-end threshold vacatur](https://www.consumerfinance.gov/rules-policy/final-rules/hmda-reg-c-judicial-vacatur-of-coverage-threshold-for-closed-end-mortgage-loans/)
- [Data Browser API documentation](https://ffiec.cfpb.gov/documentation/api/data-browser/)
