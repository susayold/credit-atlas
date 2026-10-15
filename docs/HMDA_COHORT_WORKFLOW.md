# HMDA — cohort composition và so sánh cơ cấu cố định, 09/10/2026

Receipt `hmda-cohort-3a65ba4f927c` bind với canonical case
`hmda-case-94ca64da2e30` và source `hmda-source-979e0862af13`.
`joint-mart.json` có **826 rows**, group theo activity year, loan type,
occupancy, exact public total-unit category, lien status, reverse mortgage,
open-end credit và action. Counts/public USD amounts reconcile với toàn bộ
347.056 source rows. `coverage.json` chứa ba cohort, ordered attrition,
field profiles và fixed-weight comparisons. Không drop exact public duplicates.

## Ba cohort cụ thể

| Cohort | Criteria nguồn |
|---|---|
| `all_source` | Toàn Maryland/home-purchase/site-built source; mọi observed actions |
| `principal_1_4_units` | occupancy_type=1 và total_units thuộc 1,2,3,4 |
| `principal_1_4_first_lien_closed_non_reverse` | Nhóm trên, lien_status=1, reverse_mortgage=2, open-end_line_of_credit=2 |

Ý nghĩa codes và public bins đã kiểm tra từ
[official public LAR dictionary](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields).
Raw header dùng `open-end_line_of_credit` có dấu hyphen; không silently alias.
Code1111 ở hai fields này là Exempt, không phải known non-reverse/closed-end.
Total units giữ nguyên các public bins 5-24/25-49/50-99/100-149/>149;
không suy diễn số căn chính xác từ midpoint. Site-built source có multifamily,
second residence và investment records; không relabel toàn bộ thành owner-occupied
single-family hoặc loans có repayment labels.

Ordered attrition áp criteria lần lượt. Mỗi step ghi before/excluded/retained
counts, all eight action counts, exact public amount sums và decision denominator.
Exclusions tại từng step disjoint; không cộng marginal exclusions trùng nhau.

| Cohort | 2023 records / decided | 2024 records / decided | 2025 records / decided |
|---|---:|---:|---:|
| All source | 113.089 / 71.956 | 116.150 / 74.390 | 117.817 / 72.103 |
| Principal 1–4 units | 102.864 / 64.475 | 104.518 / 65.798 | 105.326 / 63.559 |
| Principal 1–4 first lien closed non-reverse | 98.757 / 61.276 | 100.458 / 62.548 | 100.934 / 60.070 |

Decided chỉ gồm originated/approved-not-accepted/denied (actions1+2+3).
Purchases, withdrawals, incomplete và preapproval actions vẫn trong record
totals nhưng không trong decided weights/rates. Records không phải unique
borrowers hoặc identifiable unique loans. Public USD sums là interval midpoints.

## Fixed-weight comparison

Reference year đóng cố định là **2023**. Strata là joint
**loan type × occupancy × exact public total-unit category** trong từng cohort.
Cell weight = decided count năm2023 / toàn reference decided denominator.
Tỷ lệ chuẩn hóa = tổng weight2023 × denied/decided của target-year cell.
Tất cả weights/rates tính bằng `Fraction`, xuất reduced numerator/denominator
và decimal50digits; không dùng floating sums hoặc amount weights.

Full-reference rate unavailable nếu một positive-weight2023cell không có
target decided records. Không fill zero và không renormalize weights còn lại.
Cells mới ở target year nằm ngoài reference được đếm riêng. Reference không
có decisions thì mọi standardized rate unavailable.

Common-support comparison là scope hẹp **riêng**, dùng reference cells có
positive decided counts ở cả ba observed years. Common2023weights được
chuẩn hóa trong common scope, với common reference denominator/weight coverage
và từng target common numerator/denominator/native rate. Đây là descriptive
retrospective intersection; không giả vờ prospective/historical backtest.

Kết quả actual:

- All source có30referencecells,26commoncells. Full2024/2025rates **unavailable**
  do incomplete support. Common-support fixed2023mix rate:2023=10,4160%,
  2024=9,6693%,2025=9,9361%. Không thay full population rate bằng common rate.
- Principal1–4units có13reference/commoncells; full support cả ba năm.
  Observed2025rate=9,3394%; fixed2023mix=9,3352%.
- Principal1–4first-lien/closed/non-reverse có13reference/commoncells;
  observed2025rate=8,6416%; fixed2023mix=8,6183%.

Đây là descriptive application-outcome comparison qua ba attributes, chưa
fully risk-adjusted. Không chứng minh lender quality/performance drift,
fairness/compliance violation, causal changes, national representativeness hoặc
default PD. Chưa điều chỉnh lender mix, geography, credit-score values,
borrower selection và mọi unobserved underwriting criteria.

## Validation và app contracts

Build/verify giữ method SHA, case receipt SHA và output hashes. Primary
verifier đọc lại frozen case, group raw99-field Parquet rồi tái tạo toàn bộ
mart/report; updated digest không khiến forged result được tin. Original
HMDA source/canonical/aggregate/reference methods và receipts giữ nguyên.

Independent audit `hmda-cohort-audit-67bffb0ff486` **PASS70checks**. DuckDB
đọc lại original CSV với all-varchar/force-not-null, so toàn bộ six-field joint
mart; audit code dùng preset rules riêng và công thức fraction riêng để kiểm
tra ordered attrition, eight-action amounts/counts, native denominators,
full/common rates, missing cells và reference coverage. Saved audit có SQL,
script hash và cohort receipt hash. Không chứng nhận causal hoặc PD claims.

**12focusedtests PASS**: composition reversal example, missing support không
renormalize, no-reference denominator, new target cells, purchases excluded,
multifamily/investment/Exempt handling, exact amounts, forged outputs,
independent-auditor fault injection, deep-copy/hot hash guards, cross-case
binding và private export/filter rejection.

Browser đã phát hiện URL reload với independent comparison state vượt giới
hạn16parameters của trang. Đã sửa page/static URLs cho phép tối đa32fields;
API requests vẫn giữ16fields và endpoint-specific allowlists. Regression
test kiểm tra17/32pagefields được nhận,33pagefields và17APIfields bị từ chối.
Focused12tests đã PASS sau sửa. Không có thay đổi source/cohort numerics.

Final regression sau URL fix: **909tests PASS** (375engine +534application),
165,14giây. Actual browser `hmda-browser-qa-190c01d247fb` **PASS17checks**:
strict-cohort counts/rates/ordered attrition, all-source incomplete support,
common scope, exact cohort + application exports, independent top-filter
scope, URL reload, mobile390px0overflow và existing workspace navigation.
Prior failed browser package giữ nguyên làm evidence cho reload bug; không
được relabel PASS. Final screenshots đã được kiểm tra trực tiếp.

Live8770 sau final restart: cohort API trả HTTP200,all_source2025records117.817,
full_reference_status=INCOMPLETE_SUPPORT,full standardized rate=null và
public_release_approved=false. Actual17-field page URL cũng trả200HTML sau
URL-bound fix. Desktop/mobile panel excerpts đã được xem trực tiếp.

API riêng: `/api/hmda-cohorts?case_id=...`,
`/api/hmda-cohort?cohort_id=...&case_id=...&cohort=...`, và attachment
`/api/hmda-cohort-report?...`. Report chỉ nhận ba parameters này; year/lender
hoặc top-panel filters bị từ chối thay vì ngầm áp sai scope. UI có comparison
panel riêng, ba preset và private export; state dùng URL prefix
`hmda_comparison_`. Chỉ dùng receipt verified cho đúng canonical case.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_hmda_cohorts.py --case hmda-case-94ca64da2e30
.\.venv\Scripts\python.exe -X utf8 scripts/build_hmda_cohorts.py --verify hmda-cohort-3a65ba4f927c
.\.venv\Scripts\python.exe -X utf8 scripts/audit_hmda_cohorts.py --cohort hmda-cohort-3a65ba4f927c
```

## Tiếp tục trong full suite

Lender/year coverage investigation, county names acquisition (currentHTTP403),
further coverage/rare-cell analysis và private findings/review còn tiếp tục.
Các full P2D01R0–R4 gates vẫn giữ nguyên; thêm cohort composition không mở khóa
model thiếu Freddie vintages. CRE/DSCR/maturity và những chức năng P1/P3/P4/P5
còn thiếu vẫn thuộc `PLAN_FIVE_WORKSPACES.md`; không đánh dấu full suite complete.
