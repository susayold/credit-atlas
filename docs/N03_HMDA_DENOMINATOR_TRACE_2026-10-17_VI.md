# N03 — HMDA: công thức mẫu số quyết định và tỷ lệ denied mô tả

**Cập nhật:** 17/10/2026 · **Method card:** `hmda-denial-share-by-decided` · **Scope:** các LAR source objects đã bind trong registry, dùng riêng theo release/cutoff.

## Kết luận audit

Code HMDA đang tính **denied share** theo `action_taken=3` chia cho các row có `action_taken ∈ {1,2,3}`. Đây là metric do CreditAtlas suy ra để mô tả kết quả xử lý hồ sơ, không phải nhãn repayment/default, tỷ lệ PD, kết luận công bằng, hay compliance statistic do CFPB ban hành. Công thức 1+2+3 lặp nhất quán trong acquisition evidence, annual views, national views, filter groups và cohort code; action group riêng không bị gán một tỷ lệ denied có nghĩa sai.

## Publisher semantics và action code

CFPB mô tả `action_taken` là hành động đối với “covered loan or application”, với các mã sau: 1 originated; 2 approved but not accepted; 3 denied; 4 withdrawn; 5 closed for incompleteness; 6 purchased loan; 7 preapproval request denied; 8 preapproval request approved but not accepted. [Public LAR field definitions](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields/)

CreditAtlas dùng các mã 1–3 làm **decided loan/application rows**. Mã 4–5 là withdrawn/incomplete; mã 6 là loan purchased; mã 7–8 là preapproval outcomes. Chúng vẫn xuất hiện trong action-count breakdown nhưng nằm ngoài denial-share denominator. Vì vậy chỉ số không được đổi tên thành approval rate, default rate, PD hoặc loan performance rate.

| Thành phần | Công thức | Diễn giải / ranh giới |
|---|---|---|
| Source rows | `R = Σ counts(action=1..8)` trong release, năm và filter đã chọn | LAR records, không phải số người vay duy nhất; không gộp nhiều release hoặc snapshot thành unique applications. |
| Decision denominator | `D = n1 + n2 + n3` | Số row originated + approved-not-accepted + denied trong cùng scope. |
| Denied numerator | `N3 = n3` | Chỉ `action_taken=3`. |
| Descriptive denied share | `N3 / D` nếu `D > 0`; nếu `D = 0`, trả unavailable (`null`) | Mẫu số không gồm purchased, withdrawn, incomplete hoặc preapproval actions. Không thay null bằng 0. |
| Grouped share | `n3,g / (n1,g + n2,g + n3,g)` cho từng lender/geography/product/demographic bucket `g` | Tử và mẫu được tính lại trong chính bucket. Khác biệt thô không xác nhận causal effect, risk-adjustment hoặc compliance finding. |
| Denial-reason share | Số lần một reason được ghi / tổng action-3 denied rows trong scope | Một denied record có thể có nhiều reason fields; các reason share không nhất thiết cộng thành 100%. Source blank/NA/Exempt giữ riêng. |

## Mạch từ raw data đến app

| Lớp | Code/behavior đã rà | Kiểm soát |
|---|---|---|
| Acquisition contract | `hmda_sources.verify_source()` xác minh từng source ID/release; 2018 Three-Year giữ 1.961 row `action_taken=-1` trong raw evidence nhưng quarantine khỏi action 1–8 aggregate population. | Không đổi invalid action thành code 1–8; không tính quarantine rows vào denominator. |
| Canonical application row | `hmda_applications.application()` giữ source action code/name và gắn `decision_denominator_eligible = action in ('1','2','3')`. | `ACTIONS` map codes 1–8; code ngoài contract bị từ chối. Không tạo borrower/application ID từ public row. |
| Whole-case evidence | `hmda_applications.evidence()` đếm action counts theo activity year; denominator là tổng codes 1,2,3; numerator code 3. | Mỗi year giữ riêng; duplicate public-row fingerprints được báo cáo, không deduplicate. |
| Filtered/year views | `hmda_views.summarize()` và release-specific `hmda_one_year_*_views.py` / `hmda_national_views.py` dùng count filter 1–3 và 3. Mỗi filter bucket tự tính lại metric. | Khi dimension là `action_taken`, view để denominator/rate `null`; không trình bày “tỷ lệ denied trong action=3” như một KPI. Zero denominator vẫn unavailable. |
| Cohort comparison | `hmda_cohorts.py` tạo native, 2023 fixed-reference và common-support measures từ decided rows 1–3, strata loan type × occupancy × total-unit bins. Reference weights là 2023 decided counts; full standardized rate unavailable nếu thiếu một reference cell dương, không renormalize âm thầm. | Đây là case riêng của method card `hmda-fixed-2023-mix`; không phải `denial share` mặc định và không phải full risk adjustment. |
| UI/API | `/api/hmda-aggregates` và release-specific APIs trả `denominator_contract`; UI ghi rõ “Decided · actions 1–3”, denied numerator/sample size và “not default PD”. | Source release, filter, year, reporting coverage, missing/status fields và limitations được giữ cạnh metric. |

App code: [`hmda_applications.py`](../src/credit_atlas/hmda_applications.py), [`hmda_views.py`](../src/credit_atlas/hmda_views.py), [`hmda_cohorts.py`](../src/credit_atlas/hmda_cohorts.py), [`server.py`](../src/credit_atlas/server.py), [`app.js`](../apps/web/app.js).

## Release/cutoff phải đi cùng KPI

Public HMDA LAR schema xác định `action_taken` là trường numeric một ký tự. Data Browser của CFPB ghi rõ 2025 queries dùng **Snapshot** dataset; Snapshot 2025 có freeze date 02/06/2026. Dynamic national files bao gồm late submissions/resubmissions và được cập nhật hàng tuần. Do đó snapshot 2025 và dynamic 2025 là hai nguồn khác nhau, không thay thế hoặc cộng với nhau; dynamic phải gắn `as-of` timestamp. [Public LAR schema](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/public-lar-schema) · [2025 Data Browser](https://ffiec.cfpb.gov/data-browser/data/2025) · [Dynamic dataset description and update schedule](https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset) · [HMDA Data Browser API](https://ffiec.cfpb.gov/documentation/api/data-browser/)

Annual differences can reflect release vintage/resubmission cutoff, reporting coverage, product/geography mix and category availability. The LAR has no public stable applicant key for deduplicating a person’s applications across releases; do not add row counts across years as unique people or read raw changes as credit-risk deterioration.

## Source mapping and local qualification

The method card is linked to the nine LAR source records: 2018 Three-Year, 2019–2024 One-Year, 2025 Snapshot LAR, and 2025 Dynamic LAR. The paired Transmittal Sheets are validation/context records; the MSA/MD table is a geographic reference, not an application denominator. Each LAR keeps its own source ID, release/cutoff, receipt, profile and consumer trace in the [source register](data/creditatlas-source-release-register-2026-10-17.json).

Local tests validate parser/action contract, quarantined 2018 rows, denominator aggregation, filter-bucket reconciliation, cohort support and API/report behavior. A separate actual-data reconciliation of the 2025 Snapshot and the 2025 Dynamic receipt as of 2026-10-11 confirms that action counts 1–8 sum to each release profile row total, 1+2+3 equals the receipt’s decided count, action 3 equals its denied count, and the stored descriptive share equals action 3 divided by 1+2+3. HTTP smoke on the running app at port 8771 returned all 15 method cards, the new HMDA card with nine source refs, nine LAR source records linked back to it, and the HMDA formula link in `app.js`. This verifies the API/register linkage, not browser visual acceptance. The Data Browser uses the same official action categories, but its live dynamic totals can move with resubmissions; compare only like-for-like source snapshots and timestamps. This trace does not certify browser visual acceptance across all releases or Excel desktop parity.

## Next N03 work

HMDA’s action-outcome denominator is now source-bound and documented. N03 remains open for numerator/denominator and unit traces for the remaining NMDB weighted series, HMDA fixed-composition outputs across vintage support and other app KPIs; every result still needs its exact source release, filter, unit, and missing/imputed provenance.
