# P4 — Declared cash-shortfall ECL / snapshot staging research

## Phạm vi và căn cứ thiết kế

Đây là engine nghiên cứu fixed-term, explicit scenario weights, conditional
default hazards, contractual/recovery timing và snapshot staging. Không
chứng nhận accounting compliance hoặc tính actual ECL của mortgage sample.
Số dư thật là cơ sở scale; hợp đồng/cash schedules/EIR/risk assessments đều
là giả định được khai báo, chưa được quan sát hoặc fit/validate từ source.

ECL 12 tháng giới hạn **thời điểm default** có thể xảy ra trong 12 tháng,
không cắt cash shortfalls hoặc recovery tại tháng 12. Căn cứ:
[BIS IFRS9 executive summary](https://www.bis.org/publications/fsi-summary-ifrs-9-and-expected-loss-provisioning-executive-summary).
Khái niệm cash shortfall xem xét contractual và expected cash flows với
chiết khấu theo effective interest rate:
[IFRS Foundation November 2018 agenda decision](https://www.ifrs.org/news-and-events/updates/ifric/2018/ifric-update-november-2018/).
SICR cần các chỉ báo sớm/forward-looking; past-due backstop không đủ làm
chỉ báo chính duy nhất:
[BIS PAP20](https://www.bis.org/committees/bcbs/basel-consolidated-guidelines/module/pap/20).
Full issued IFRS9 PDF redirect tới subscription khi truy cập; không coi
search snippet là bằng chứng đã đọc toàn standard hoặc compliance audit.

## Actual source + illustrative study

Receipt: `exposure-ecl-ba27d7207a44`, version `illustrative-ecl-v1-20261009`.
Source: `exposure-import-57b88e00bedb`, March 2026 Freddie sample. Có
9.602 CURRENT observations eligible / 96 excluded; eligible reported UPB
USD 906.367.109,80. Source risk inputs vẫn thiếu, source EL unavailable.

**Lịch 36 tháng bullet dùng minh họa**, principal trả tại tháng 36,
monthly effective rate khai báo 0,004. Đây không phải remaining maturity,
payment schedule hay original EIR thực tế của các khoản mortgage năm 2012.
Giữ zero-UPB observations trong counts. Excluded source records không tự
được gán stage hoặc thêm loss bằng 0 vào eligible ECL.

| Declared segment assessment | non_relief | relief |
|---|---:|---:|
| Benchmark conditional hazard/month | 0,001 | 0,001 |
| Current assessment hazard/month | 0,001 | 0,004 |
| Declared DPD / credit-impaired flag | 0 / false | 0 / false |
| Research snapshot stage | 1 | 2 |

Benchmark được khai báo cho **cùng remaining horizon**. Không giả vờ đây là
observed origination PD được lấy từ lịch sử năm 2012. Assessment curve cố
định quyết định stage; mỗi loss scenario có curve riêng và không đổi stage.
Actual illustrative study không có stage3; stage3 được kiểm tra bằng fixtures.

| Scenario | Weight | non_relief hazard | relief hazard | Recovery / cost | Lag |
|---|---:|---:|---:|---|---:|
| Base minh họa | 0,7 | 0,001 | 0,004 | 0,75 / 0,03 | 6 months |
| Adverse minh họa | 0,3 | 0,003 | 0,008 | 0,55 / 0,05 | 12 months |

Weighted selected-horizon research cash-shortfall result:
**USD 23.530.061,94** (rounded display), full-lifetime reference
**USD 32.084.695,18**. Các con số thuộc lịch/risk/recovery giả định, không
phải expected loss dự báo của danh mục thật. Exact rational values trong
receipt report/export là authoritative; display không dùng để reconcile.

Independent audit `exposure-ecl-audit-59232552bdd3`: **1.885 checks PASS**.
Re-read source CSV + copied assumptions; dùng Fraction và par cash-flow
identity khác đường tính của primary engine. Audit kiểm tra stage/PD,
repayment schedule, default events, marginal/survival, all future cash/recovery,
selected/lifetime loss và mọi source-scaled currency/group/weighted aggregate.

Verification checkpoint: **28 focused tests PASS**, full suite **1.003 tests
PASS** trong 390,96 giây. Actual inventory/bridge/scenario/ECL browser **14
checks PASS** `exposure-browser-qa-9f5c9c210974`, gồm exact exports, stage1
month13 exclusion/stage2 inclusion, segment/scenario switches, reload và
390px mobile. Live8770 ECL/report JSON parity PASS. Stage3/default-now được
kiểm tra bằng fixtures; actual illustrative source study không có stage3.

## Hợp đồng giả định và chính sách stage

Input JSON qua bounded reader 100.000 bytes, reject duplicate keys. Private,
schema_version 1, basis declared_research_cashflows_and_assessments, name và
version rõ ràng. source_import_id pin immutable typed import; không overwrite
source có risk_contract hiện hữu. Eligible source states chỉ CURRENT hoặc
DECLARED_PERFORMING, direct asset representations; phủ đúng eligible segments.

Mỗi segment bắt buộc:

- remaining_months: integer 1–120.
- monthly_effective_rate: declared monthly effective rate, không annual rate.
- principal_due_factors: đúng remaining months, không âm và tổng **exactly 1**.
- benchmark_hazards / assessment_hazards: conditional fractions, cùng horizon.
- declared_dpd: nonnegative integer; không suy DPD cụ thể từ D1/D2 categories.
- declared_credit_impaired / qualitative_sicr: explicit booleans.
- poci / revolving / cure_under_review: bắt buộc false; chưa có policies cho các scope đó.

Research staging policy cố định, được export:

1. Stage3 nếu declared credit-impaired hoặc declared DPD ≥90.
2. Nếu chưa stage3: stage2 nếu DPD **>30**, qualitative SICR, hoặc cumulative
   assessment PD tăng và thỏa **relative AND absolute** thresholds khai báo.
3. Benchmark PD =0, current PD >0: any-positive-to-stage2 theo explicit policy;
   ratio null và status POSITIVE_FROM_ZERO, không divide-by-zero/fill ratio.
4. Còn lại stage1. Stage1 event horizon min(12,remaining term), stage2 toàn term,
   stage3 default mass1 tại month0.

Các thresholds 2× và +0,02 trong example là policy minh họa, không phải
universal IFRS requirement. Không có DPD rebuttal, low-risk exemption,
previous-stage hysteresis/cure, modification/forbearance hoặc POCI logic.
Unsupported flags bị reject để tránh tự gán stage trong scope thiếu policy.

Scenarios 1–8 có unique IDs, labels, weights fractions **tổng đúng 1**;
không normalize ngầm. Mỗi scenario phủ đầy đủ segments, hazards từng tháng
và 1–12 recovery cash events. Recovery event: lag integer 0–120 months,
gross recovery fraction và collection cost fraction của outstanding principal.
Gross recoveries tổng ≤1, từng cost ≤gross recovery; negative net recovery
scope chưa hỗ trợ. Fractions/rates dùng decimal strings tối đa 6 fractional
digits, [0,1]; reject percent/scientific notation/boolean substitutes.
Exact output numerator/denominator giới hạn 13.000 bits để serialization
không vượt integer string bound; vượt bound báo lỗi, không silently round.

## Cash timing và toán học

Default xảy ra đầu tháng t, contractual payments cuối tháng. Trước default,
cash được trả đúng lịch và không tạo shortfall. Monthly interest factor bằng
opening principal factor × monthly EIR; principal payments theo declared
schedule. Present value toàn contractual schedule phải đúng 1 unit principal.

Conditional hazards h[t] → survival S[t]=S[t−1](1−h[t]); marginal default
mass q[t]=S[t−1]h[t]. Không dùng hazards như marginal PD và không cộng lặp
probabilities khi khoản đã default. Stage3 không dùng future hazard curve;
default tại month0 có mass1 và no-default survival0.

Default cash shortfall PV tại reporting date:

- Contractual tail PV: tổng principal+interest dues từ t đến maturity, chiết khấu tháng due.
- Net recovery PV: remaining principal trước default × (recovery−cost),
  discount theo month t−1 + lag; month0 default dùng start0.
- Event loss PV = contractual tail PV − net recovery PV.
- Selected research ECL = Σ marginal default mass × event loss PV, với default
  event cutoff tương ứng stage. Toàn cash tail/recovery vẫn giữ kể cả ngoài cutoff.
- Weighted result = Σ explicit scenario weight × selected ECL.

No-default paths không tạo loss; primary dùng exact Fraction. Independent
audit kiểm tra contractual-tail identity: outstanding principal/(1+r)^(t−1)
đối với lịch par do engine xây, thay vì cộng lại cùng cash-flow loop.
Negative shortfalls không được clamp; input/model không hỗ trợ bị reject.
Không thêm LGD multiplier vào cash-shortfall engine để tránh double count
recovery đã có trong expected cash flows.

## Commands / app / các phần còn thiếu

Từ `local machine path omitted`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_illustrative_ecl.py
.\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_ecl.py --assumptions private evidence omitted from public release
.\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_ecl.py --verify exposure-ecl-ba27d7207a44
.\.venv\Scripts\python.exe -X utf8 scripts/audit_exposure_ecl.py --ecl-id exposure-ecl-ba27d7207a44
.\.venv\Scripts\python.exe -X utf8 scripts/browser_exposure_qa.py
.\scripts\test.ps1
```

Prepare/build tạo version receipt mới, copied assumptions và hashes của
source/methods/payload. Verify rederive và kiểm tra hashes cả sau calculation.
Không sửa frozen receipts; method revisions cần receipt mới.

App exposure có panel ECL research: version selection, scope/staging,
scenario/weighted comparison, group totals, selected segment/scenario default
timing table và private exact export. Parent currency/dimension dùng confirmed
scope; unsupported source_state/representation grouping chuyển stage với
heading rõ. Stage assessments/curves là whole declared model, không phải
currency-specific fitted risk. Version/detail selectors chưa persist URL.

API: /api/exposure-ecl-studies cần source_import_id;
/api/exposure-ecl và /api/exposure-ecl-report cần ecl_id/source_import_id,
optional currency/dimension(stage,region,segment). Private source binding,
duplicate/unknown filter guards, no-store export; no raw position IDs/paths.
Cached reads kiểm tra toàn source/payload/receipt hashes cả khi timestamp
được giữ nguyên. Intake hiện CLI/JSON, chưa có editing/upload UI.

Tiếp tục: actual contract/payment/EIR/recovery evidence adapters, observed
origination/current risk comparison và calibrated scenario probabilities;
POCI/revolving/cure/forbearance policies; accounting review/validation,
ECL movement bridge, dependence/tail simulation và finance review package.
Toàn bộ 5 workspace/50 capabilities vẫn là scope đang triển khai.
