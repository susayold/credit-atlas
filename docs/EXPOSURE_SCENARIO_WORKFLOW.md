# P4 — Versioned declared scenario / stress workbench

## Dữ liệu và kết quả minh họa

Scenario set `exposure-scenario-9655e30419ec`, version
`illustrative-v1-20261009`, sử dụng số dư thật của
`exposure-import-57b88e00bedb` (Freddie sample, tháng 03/2026). Các tham số
risk và severity do người xây dựng khai báo để minh họa sensitivity; chưa
fit/validate PD, LGD, EAD hoặc hiệu chỉnh quan hệ với biến macro.
Không dùng các kết quả này làm ước lượng tổn thất thực tế của sample.

| Coverage, USD | Records | Reported amount |
|---|---:|---:|
| Toàn snapshot | 9.698 | 915.208.989,12 |
| Eligible: source state CURRENT | 9.602 | 906.367.109,80 |
| Excluded: D1/D2/D3PLUS | 96 | 8.841.879,32 |

CURRENT là source classification được chọn, không chứng nhận một validated
performing/default classifier. Giữ zero balances; eligible có 140 zero-UPB
observations. Exclusions có counts/amount theo source state và currency.
Source PD/LGD/EAD vẫn thiếu, source EL vẫn **unavailable**. Scenario overlay
không sửa source.csv, metadata, typed positions hoặc source aggregate report.

Baseline assumptions (cumulative PD 12 months, LGD fraction, EAD factor):

| Segment | PD fraction | LGD fraction | EAD / reported amount |
|---|---:|---:|---:|
| non_relief | 0,01 | 0,25 | 1 |
| relief | 0,02 | 0,35 | 1 |

Forward event được khai báo: first 90+ days delinquency trong 12 tháng.
Đây là default-definition assumption của scenario, chưa phải default labels
đã dựng/kiểm định trên nguồn hoặc regulatory default classification.

| Kịch bản minh họa | PD odds × | LGD + | EAD × | Research EL, USD, rounded display | Clipped records |
|---|---:|---:|---:|---:|---:|
| Declared baseline | 1 | 0 | 1 | 3.603.267,03 | 0 |
| Mild | 2 | 0,05 | 1 | 8.280.665,40 | 0 |
| Adverse | 3 | 0,15 | 1,1 | 17.313.511,80 | 0 |
| LGD boundary sensitivity | 3 | 0,9 | 1,1 | 38.568.766,10 | 9.602 |

Không suy diễn mild/adverse severity từ recession/GDP/interest-rate forecasts.
Labels chỉ mô tả bộ shock đã khai báo. LGD boundary scenario cố ý minh họa
clipping; không phải bằng chứng rằng các khoản thực tế có LGD 100%.
Baseline/adverse declared EAD là reported amount nhân factor, không phải
observed/default-time EAD. Không có accounting ECL, IRB hoặc FX total.

## Hợp đồng và công thức

Input JSON bounded 100.000 bytes, reject duplicate JSON keys; schema_version 1.
Exact keys: name,version,basis,source_import_id,horizon_months,default_definition,
eligible_source_states,ead_basis,lgd_boundary_policy,segment_assumptions,scenarios,
visibility,public_release_approved và schema_version. basis bắt buộc
declared_research_assumptions, private/false, horizon integer 1–1.200 months.
Không overwrite source có risk_contract hiện hữu; hỗ trợ direct assets.

Eligible states chỉ CURRENT hoặc DECLARED_PERFORMING và phải có eligible rows.
Segment assumption keys phải phủ đúng mọi eligible segment, không tự fill
missing assumptions. Mỗi segment có đúng pd/lgd/ead_factor, decimal strings
không âm: PD/LGD trong [0,1], EAD factor ≤1.000. reported amount đã normalize
native currency/units từ frozen import.

Tối đa 12 shock scenarios, unique IDs, baseline reserved. Mỗi scenario có
id,label,pd_odds_multiplier,lgd_addition,ead_multiplier. Positive odds multiplier
≤1.000; LGD addition trong [−1,1]; EAD multiplier trong [0,1.000]. LGD policy
bắt buộc clip_and_report, không silent clamp.

Với baseline p,l,e và shocks m,a,q:

- e = reported amount × declared EAD factor.
- p′ = p×m / (1−p+p×m), odds multiplier, khác probability multiplier.
- l′ = clip(l+a,0,1), báo số records bị clip, gồm cả zero-balance records.
- e′ = e×q.
- ELbaseline = p×l×e; ELscenario = p′×l′×e′.

Ordered attribution: PD effect = (p′−p)le; LGD effect = p′(l′−l)e;
EAD effect = p′l′(e′−e). Residual = ELscenario−ELbaseline−ba effects.
Order cố định và được export; không gọi các effects là unique causal effects.
Total theo currency và groups segment/region/source_state, không cộng chéo
dimensions hoặc native currencies. Currency có 0 eligible rows chỉ có scope/
exclusions, không tạo EL row bằng 0 ngầm.

Primary arithmetic dùng Fraction chính xác; mỗi số xuất numerator/denominator
và decimal_50 (display projection). UI làm tròn 2 decimals cho đọc thuận tiện,
không dùng display để audit. Không có rounding-to-cents policy cho actual cash.
Independent audit dùng Decimal precision 90 và inverse-odds form, re-read raw
CSV amounts/units và copied assumptions; compare với rational result ở
relative tolerance 1e−44, absolute floor 1e−44.

Audit `exposure-scenario-audit-4a1b476f5775`: **2.755 checks PASS**, gồm coverage,
exclusions, group keysets/counts/zero balances/clipping, EAD/EL/effects/residual.
Fault-injection test thay PD effect để xác nhận audit độc lập báo fail.
Verification checkpoint: **25 focused tests PASS**, full suite **975 tests
PASS** trong 178,75 giây. Actual inventory/bridge/scenario browser **11 checks
PASS** `exposure-browser-qa-51f387098065`: version/detail filters, source EL
unavailable, clipping counts, exact exports/reload và 390px mobile. Live8770
scenario/report JSON parity PASS. Source mutation trong projection bị reject
bởi post-calculation hash guard; corrupted assumptions giữ timestamp bị reject.

## Reproduce, API và app

Từ `local machine path omitted`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_scenarios.py --assumptions private evidence omitted from public release
.\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_scenarios.py --verify exposure-scenario-9655e30419ec
.\.venv\Scripts\python.exe -X utf8 scripts/audit_exposure_scenarios.py --scenario-id exposure-scenario-9655e30419ec
.\.venv\Scripts\python.exe -X utf8 scripts/browser_exposure_qa.py
.\scripts\test.ps1
```

Build tạo receipt mới, copy assumptions.json, report.json và hashes/pinned
methods/source lineage; không mutate version cũ. Verify rederive all aggregates,
kiểm tra source hashes và methods cả trước/sau bước tính. Method revision tạo
receipt mới; receipt từ methods trước được giữ làm lịch sử, không sửa/reseal
receipt cũ để vượt current verification.
App panel ở `?view=exposure&exposure_import_id=exposure-import-57b88e00bedb`:
version selection, eligibility/exclusions, baseline parameters, all-scenario
comparison, selected scenario attribution/clipping và private exact export.
Version/detail selections hiện không persist URL; mặc định newest receipt/
adverse nếu có. Parent currency/dimension dùng confirmed scope. Representation
grouping chưa hỗ trợ, UI ghi rõ dùng segment trong trường hợp đó.

GET /api/exposure-scenarios cần source_import_id;
/api/exposure-scenario và /api/exposure-scenario-report cần scenario_id,
source_import_id, optional currency/dimension. API rejects incorrect binding,
duplicate/unknown filters, unsupported currency/dimension. Không phục vụ raw
position IDs hoặc private lineage paths. Cached reads kiểm tra source,
payload, receipt hashes, kể cả corruption giữ nguyên timestamp.
Intake phiên bản giả định hiện qua CLI/JSON, chưa có editing/upload UI.

Tiếp tục toàn P4: calibrated source-compatible risk adapters khi có dữ liệu;
macro-conditioned stress relationships nếu đủ panel/vintage evidence;
[declared cash-shortfall ECL/staging workbench](EXPOSURE_ECL_WORKFLOW.md) đã
có term structures, explicit assumed cash schedules/SICR và full recovery
timing; actual contract/EIR/risk evidence và accounting qualification còn thiếu;
dependence,
recovery/tail simulation và review approvals. Snapshot thật/declared scenarios
được giữ riêng; không mở lại các consumed final holdouts để fit lại.
