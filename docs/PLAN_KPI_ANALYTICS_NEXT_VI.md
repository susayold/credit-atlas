# CreditAtlas — plan phát triển phân tích dữ liệu và KPI tiếp theo

ABS-EE definition checkpoint: acquired official GovInfo2025CFR PDF/XML2files403351bytes. P5 field dictionary covers62observed mirror columns with proposed Item3correspondence,coverage and private export. Independent62PDF/XML definitions/coverage PASS,backend8PASS,browser5groups/coverage regression4groupsPASS. SEC specification ZIPHTTP403; XSD/original-filing XML/EX103/current-rule/labels/fidelity/model gates remain false. Counts unchanged. See ABS_EE_FIELD_DEFINITIONS_VI.md.

Native Excel checkpoint: six workbooks9264cells/746formula cells baseline PASS;18representative input cases/59checks PASS. SEC missing-numerator blank-to-zero bug fixed in new exports; UI3groups/backend7PASS. Original source files and frozen holdout ledger unchanged. Native visual/full-feature qualification remains open. See NATIVE_EXCEL_VALIDATION_VI.md.

P4 acceptance checkpoint 11/10/2026: fixed exact XLSX significant-digit validation and allowlisted Excel POST error messages. Backend62PASS; independent import66checks/bridge500checksPASS; browser5groupsPASS including source/bucket→draft, exports, invalid numeric rejection, valid EXAMPLE intake/mobile. Full scope/ownership/native Excel/governance qualification remains open. See P4_ACCEPTANCE_AUDIT_VI.md.


ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. See ABS_EE_MIRROR_COVERAGE_VI.md.


Checkpoint Managed Pool11/10/2026: tab/API/JSON có7kỳ,30chỉ tiêu/kỳ,210giá trị nguồn,105đối soát và14raw ratios; units nghìnUSD/signedrecoveries/source duration giữ riêng. Backend21PASS, independent source auditPASS, browser4groupsPASS. P5.02/P5.10 vẫn Một phần; xem MANAGED_POOL_ANALYTICS_VI.md.


Checkpoint staticpool11/10/2026: new issuer index +StaticPool-WOART/ManagedPool-Retail workbooks,3files606781bytes. P5 Static pool tab/API/JSON has21cohorts2021–2026 ×3metrics,1998populated and1362blank positions, source cells andage12/24 support. Backend26PASS, independent63group source auditPASS, browser4groupsPASS pool-history-qa-5930436fbc94. No loan-level target/LGD/forecast claim; Managed/6legacy sheets pending normalization. P5.02/P5.10partial unchanged. See STATIC_POOL_HISTORY_VI.md.


Checkpoint SOFR11/10/2026: acquired443New York Fed SOFRAI observations andSIFMA2025/2026US calendar,5files925844bytes. P5 ABS SOFR nguồn tab/API/privateJSON compares20periods;20/20at declared source binary precision,20/20interest cents. Raw exact19/20SOFR,15/20coupon preserved; historical15:00vintage/conforming changes/unscheduled notices remain unverified. Backend40PASS, independent20-period auditPASS, browser6groupsPASS. P5.05conditional/P5.10partial unchanged. See ABS_SOFR_BENCHMARK_VI.md.


Checkpoint retail source quality11/10/2026: UCI acquisition profile được hash-pin vào suite view; whole-source30000clients ×23predictors =690000cells,0parser-missing. P1 monitor có23feature rows vàlineage; review/Excel capture có source_quality cùng suite scope. Backend27PASS; browser6PASS retail-source-quality-qa-594921ea7ac8; inspector9PASS kpi-inspector-qa-0b9964df5e79; Excel110-row regressionPASS. B1 tiến bộ, semantic validity/OOT vàprofiles khác chưa complete. Không thay50capability statuses. Xem RETAIL_SOURCE_QUALITY_VI.md.


Checkpoint payment rules11/10/2026: Apple public issuer SECfeed used for
programmatic discovery/acquisition of S-3ASR01/11/2024 bundle92pages with base
indenture. Source feed metadata/hash links to exact PDF. Payment rules inSECapp
has5clauses/section/page/source evidence/privateJSON; cutoff and issuer guards.
Backend rules+notes34testsPASS; source/browser6groupsPASS
note-rules-qa-f5dd8158e6b9. Contract following/no-delay-interest clauses acquired;
series payment-place/overrides and banking calendar stillunqualified.
P3.08/C4 stillpartial; see ISSUER_API_AND_PAYMENT_RULES_VI.md.


Checkpoint note cashflows11/10/2026: Apple8-K90pages acquired/identity/extracted,
filing12/05/2025 distinct from earliest event05/05/2025. Four source note series,
original full-issue/no-redemption/no-default nominal schedule, calendar-year
partitions, series/end filters, clause evidence and privateJSON now inSECapp.
Backend notes+facilities36testsPASS; independent PDF/source/browser6groupsPASS
note-schedule-qa-9827487edb65. Full lifetime path50rows; cutoff11/10/2026
remaining42rows. Current outstanding/actual payments/business-day dates/full
issuer DSCR remain unsupported; P3.08/C4 stillpartial. Baseindenture identified
via primarySEC research; not acquired into catalog yet.
See SOURCE_NOTE_CASHFLOWS_VI.md.


Checkpoint facilities11/10/2026: Ford2026amendments333pages acquired/extracted,
four PDFs780pages total. Facilities & covenant in SEC app has10versions/5tranches,
filing/effective cutoff, prior boundary comparisons, source pages and privateJSON.
Corporate covenant definition/clausePDFpages39/132 visual-reviewed. Backend
facilities+events34PASS; browser5groupsPASS facilities-qa-18dedf9f1512.
Actual headroom/DSCR/full amendment-chain qualification remain unavailable;
P3.07 Cần dữ liệu, P3.08 Một phần. See FACILITY_CALENDAR_AND_COVENANT_VI.md.


Checkpoint11/10/2026 — KPI input traces và issuer filings:
88 KPI đã map source/input references:61derived,26saved aggregates,1required-input
EL; không record-level recompute cho saved model metrics. QA
`kpi-trace-qa-6806b6dbe015`:6groupsPASS; browser inspector
`kpi-inspector-qa-9479d922c579`:9groupsPASS; Excel110-row regression PASS.
JSON export giữ trace sources riêng khỏi selected36-month display slice.
SEC14API files18.105.032bytes download+canonical verified;
`sec-audit-a0df37e6ae3b`:105441facts/13374filing occurrences,0differing rows,
201exact supported ratio checks. SHA của14files đều giống snapshot cũ: đây là
re-acquisition/verification, không thêm issuer observations.
New view `sec-view-913c93906c18` selectable; Issuer filings date/form/item/paging
và private JSON đã tích hợp. Backend29PASS; browser
`sec-events-qa-a355fade2b6e`:8groupsPASS/raw4issuers/reload/mobile/outage.
[Hướng dẫn](SEC_ISSUER_FILINGS_VI.md). Full-text Ford credit agreement PDF64pages
đã tải, identity/page checks và draft term evidence; actual liquidity/headroom,
amendment chain và DSCR chưa qualified. Đã tải thêm credit-amendments171pages
và annual report212pages; cả3PDF tổng447pages, identity checked/extracted. P3.06/07/08 vẫn chưa complete scope.
[50 completion requirements](COMPLETION_REQUIREMENTS_50.json) giữ acceptance
riêng từng capability; không tự chuyển label hoặc tính completion từ UI.


Checkpoint KPI data inspector 10/10/2026: catalogue tìm kiếm/lọc actual,
missing và comparable-baseline; bấm KPI mở hồ sơ; bảng hỗ trợ tìm mọi cột,
25-row paging và CSV toàn bộ filtered rows. 16 SEC ratio input traces và
3 mortgage ratio traces có actual numerator/denominator; metric schema cho
reviews/Excel giữ nguyên. QA `kpi-inspector-qa-f43c77e05a6b`: 10 nhóm PASS,
5 domain/source-table CSV parity, issuer/mortgage input parity, mobile và
frozen ledger unchanged. Excel regression đối chiếu110 KPI/control rows PASS;
13 supported SEC ratios reconcile Decimal60. [Cách sử dụng](KPI_DATA_INSPECTOR_VI.md).
88 KPI /22 controls giữ counts hiện có; chưa phải full record-level input
trace cho mọi KPI hoặc hoàn tất C1–C6 qualification gates.


Checkpoint 10/10/2026. Mục tiêu là giúp analyst đi từ dữ liệu → phép tính → biến động → bằng chứng → hành động/review. Kế hoạch này bổ sung [50 capabilities](PLAN_WORKBENCH_DETAIL.md), không thay các data/model/legal gates trong kế hoạch gốc.

## 1. Nền tảng đã có và việc vừa triển khai

Checkpoint B6: Maturities/Facts Excel xuất theo source filters từ Debt maturities,
server-derived report và23 linked/calculation formulas. Missing/zero/negative
dependencies checked, source restored trước export. Backend43PASS; browser
`sec-debt-xlsx-qa-de64508d62d6`:5groupsPASS cho complete/real zero/missing-family
raw SEC/saved XLSX parity, mobile/error recovery và frozen ledger unchanged.
[Hướng dẫn](SEC_MATURITY_EXCEL_VI.md). Chưa native Excel execution; full C4
debt-service/facility/legal-term qualification vẫn cần inputs.

Checkpoint P3.08: principal maturity profile theo selected SEC filing chạy trong
app/private JSON và new memo capture.6 fiscal-year buckets, explicit debt-only
hoặc debt/capital-lease family, exact subtotal/total/shares và missing/negative
guards. Backend38PASS; maturity browser4groupsPASS `sec-debt-qa-662fad1cb983`;
memo browser4groupsPASS `corporate-memo-qa-2cf35018c3e3`.
[Cách đọc](SEC_DEBT_MATURITIES_VI.md). C4 vẫn một phần: principal disclosures
chưa có facility dates/coupons/debt-service cashflows/legal covenant terms.

Checkpoint B5: Excel doanh nghiệp xuất từ Annual trends/Interest coverage theo verified scope, hai sheets Analysis/Facts, source links/exact text và actual/baseline/delta/driver formulas. Backend44PASS; browser `sec-workbook-qa-03d578d3b62d`:3groupsPASS. MSFT5-period audit30rows,44numericresults,20bridges,328formulas. [Hướng dẫn](SEC_ANALYSIS_EXCEL_VI.md). Native Excel execution chưa kiểm tra; C1–C6 giữ input/qualification gates.

Checkpoint P3.03 driver bridge: annual ratios có numerator-first decomposition,
source USD inputs, counterfactual ratio, two effects, total/residual và support
gates. Không extrapolate baseline qua missing/ambiguous/concept/duration gaps.
Backend **46 tests PASS**, `sec-bridge-tests-20261010.xml`.
Browser `sec-trends-qa-3cf29a711bdc`: **6 groups PASS**, 67 supported ratios
và65 bridges checked; desktop/mobile/export/reload/outage verified.
[Công thức và cách đọc](SEC_ANNUAL_TRENDS_VI.md). Đây là arithmetic analysis,
không causal attribution hoặc hoàn thành C4 DSCR/covenant.

Checkpoint bổ sung P3.03: Interest coverage theo3/5/10 report periods, chọn
explicit expense tag, giữ missing/ambiguous và ratios âm. App có latest-period
reading, raw candidate evidence và private JSON; memo mới capture coverage
với cutoff selected filing date. Backend **33 tests PASS**; memo browser
`corporate-memo-qa-0eaa9fd5829e`: **4 groups PASS**. Đây là operating-income /
reported-OCF proxies, chưa qualified EBIT ICR/DSCR/covenant; C4 vẫn một phần.
[Chi tiết nguồn, công thức và scope](SEC_INTEREST_COVERAGE_VI.md).
Coverage browser `sec-coverage-qa-1c32f79854e0`: **4 groups PASS**;
four issuers/raw-source reconciliation, concept/period selectors/reload/mobile,
outage recovery và frozen holdout ledger unchanged.

P3.06/P3.10 update: Corporate financial memo nối selected filing và annual
trend với nine narrative sections, owner/status và revision history. Evidence
server derive/capture khi tạo; sửa narrative không recapture. Browser4 groups
PASS, `corporate-memo-qa-1deb923c721e`; backend25 tests PASS. Scope financial
memo đã có; issuer-event/debt/covenant sources tiếp tục cần inputs, C4 chưa đóng.
[Hướng dẫn memo](CORPORATE_FINANCIAL_MEMO_VI.md).

P3.03 supplemental update: Annual trends dùng saved SEC statements, cùng issuer,
3/5/10 report periods, original-10-K selection và conservative comparability
screens. Exact actual/baseline/delta, full source/baseline fields và private
JSON đã vào app. Browser6 groups PASS, 67 source-ratio checks,
`sec-trends-qa-cc887f418aa3`; SEC backend41 distinct tests PASS.
Đây là deeper financial analysis trên data đã có; không đóng C4 DSCR/covenant.
[Spec/cách sử dụng](SEC_ANNUAL_TRENDS_VI.md).

Checkpoint B4: KPI report xuất trực tiếp theo monitor filters, bốn sheets,
source captures và original review captures/history. 110 typed KPI/control rows,
tám comparable deltas kiểm tra Excel formulas/cached results với JSON;
baseline zero/unavailable không thành numeric zero. Actuals vẫn browser-derived,
server verify sources tại export; chưa native Microsoft Excel execution.
Browser `kpi-workbook-qa-08a849344ada`: 4 groups PASS, backend 31 PASS,
KPI regression `kpi-analysis-qa-95251bc16b81`: 19 PASS. App đã đưa KPI lên đầu,
thêm individual dossiers và domain investigation playbooks.
[Hướng dẫn app/Excel](KPI_APP_AND_EXCEL_VI.md). C1–C6 vẫn giữ input gates.

Checkpoint B3: review từ KPI đã tích hợp cả năm domain, có immutable snapshot,
verified source digests, owner/judgement/hypothesis/next action, revision/history
và private export. Browser `monitor-review-qa-f0bc7bae609e`: **7 PASS**; backend
**21 distinct tests PASS**. KPI context do browser tính, nguồn server verify lúc
capture; không nhầm với independent KPI recalculation hoặc credit approval.
Tiếp B4: Excel KPI report, gồm actual/baseline/quality/review evidence.

Checkpoint B2: baseline selectors P2/P4/P5 chạy trên native periods, giữ exact
requested/resolved/status và không fallback. Manual baseline thay delta/movement
decomposition tương ứng; actuals/lifetime/quality/cash replay giữ scope riêng.
Receipt `kpi-analysis-qa-6cc4b4dff828`: **19 PASS**. Tiếp B3 source-bound analyst
review, B4 Excel KPI report. Các checkpoints dưới là lịch sử trước B2.

Checkpoint B1: **88 KPI nghiệp vụ + 22 data-quality controls** cùng source/grain/
formula/interpretation và quality tables. Missing profile chưa có giữ unavailable,
không infer từ imputation/zero amount. Receipt `kpi-analysis-qa-90b929dc7eae`:
**18 PASS**; independent population, missingness, retained duplicate share và
partition/ledger support. Tiếp B2: kiểm soát các kỳ có thể so sánh; B3/B4 review
và Excel reporting. C1–C6 vẫn cần additional inputs/qualification.

Checkpoint A5: **88 KPI**. Latest ABS period đã có interest paid, certificate
distribution, closing cash, reserve deposit, unpaid interest/reviewer fees và
cash/reserve residuals. Hai bảng ledger/bridge giữ exact amounts; từng bước,
sequence và tổng được đối soát. Receipt `kpi-analysis-qa-092358439eb1`: **17 PASS**,
bao gồm selected-ledger API outage. Các checkpoints phía dưới là lịch sử.
Ưu tiên tiếp B1: hệ thống KPI chất lượng dữ liệu; tiếp đó B2–B4 controls/review/
Excel reporting. C1–C6 vẫn phụ thuộc inputs/qualification mới, không gọi hoàn tất.

Checkpoint A4: **80 KPI**. SEC đọc riêng bốn issuer theo CIK và latest supported
annual filing trước cutoff 2026-10-10; có 16 ratios và hai bảng facts/concepts.
Unsupported/ambiguous giữ null; receipt `kpi-analysis-qa-96cfabe47d97`: **15 PASS**,
gồm source arithmetic, period/unit/cutoff và một issuer API outage. Các mục A3/A2
bên dưới mô tả checkpoint trước. Bước A5 tiếp theo là ABS reported cash bridge.

Checkpoint A3: monitor hiện có **64 KPI**; các con số 55 phía dưới mô tả checkpoint
trước policy integration. P1 đã đọc pinned saved policy cùng freeze, thêm chín
KPI và ba bảng assumptions/cases/actions. Case đầu `lower_thresholds` có 2.277
review / capacity 600, overflow 1.677; expected cost 4.808,640601 declared units,
retrospective proxy 4.643. Cả ba declared threshold cases vượt assumed capacity.
Không tối ưu bằng final, không chứng nhận reviewer efficacy hay realized profit.
Receipt `private evidence omitted from public release`: **13 PASS**.
Hạng mục tiếp theo A4 là issuer financial ratios với filing-specific evidence.

Monitor đã có 55 KPI readouts, formulas/support, interpretation, source tables, JSON export và các chỉ số cần dữ liệu bổ sung. P2 có phân rã thay đổi tỷ lệ D3 giữa hai kỳ theo tử số/mẫu số, chọn count hoặc UPB. P4 có hai snapshot cùng USD/region.

Đợt tiếp theo triển khai **bridge biến động P4 theo toàn bộ vùng**: union buckets giữa hai kỳ, prior/current amounts, delta USD, record counts và contribution tính trên tổng kỳ trước. Phép tính USD dùng integer cents, đối soát từng partition và tổng. Nhận xét chỉ ra các vùng tăng/giảm lớn nhất. Đây là phân rã số học, chưa phải giải thích nguyên nhân kinh tế.

## 2. Thứ tự triển khai và điều kiện nghiệm thu

Không cam kết ngày hoàn thành cho những bước thiếu quyền truy cập hoặc input. Mỗi bước phải ghi receipt, cập nhật trạng thái và giữ evidence phiên bản cũ.

| Ưu tiên | Hạng mục | Inputs/phạm vi | Đầu ra và phép tính | Nghiệm thu | Trạng thái tại checkpoint |
| --- | --- | --- | --- | --- | --- |
| A1 | P4 regional movement | Hai imports Feb/Mar 2026, USD/region | Region delta và contribution Δregion/prior total; top increases/decreases | Exact-cent partitions/total; source/export/browser parity; missing prior không tạo bridge | Đã triển khai; receipt ghi trong status sau kiểm tra |
| A2 | P2 migration readout | Transition/cure/lifecycle marts đã có, episode conventions | Ma trận adjacent-state, row supports, cure/relapse, competing exits | Row totals reconcile; không coi exit là cure; count/UPB có mẫu số riêng | Đã thêm 10 KPI lifetime/follow-up vào monitor; row supports và count/UPB verified |
| A3 | P1 policy economics readout | Saved validation predictions; declared costs/capacity từ policy workflow | Accept/review/reject distributions, action×outcome costs, cutoff sensitivity | Cùng validation cohort; không tune bằng final test; costs là assumptions | Đã tích hợp pinned case + all-case/action support tables; receipt tại status |
| A4 | P3 issuer ratio readout | SEC filing-specific annual facts/units | Current ratio, liabilities/assets, net margin và OCF/revenue; fields/concepts evidence | Cùng issuer/period/filing; unavailable/conflicting facts không thành zero | Đã tích hợp 16 KPI cho bốn issuer, annual trends, numerator/denominator driver bridge và explicit interest coverage; DSCR/debt/covenant vẫn cần inputs |
| A5 | P5 reported cash bridge | Reported funds, interest/principal allocations, reserve movement | Sources/uses bridge, tranche support, payment dates | Exact values/reconciliations; không chứng nhận full legal waterfall | Đã tích hợp latest period cash/reserve bridge và tám replay KPIs; receipt tại status |
| B1 | Quality KPI theo domain | Canonical quality marts, schema và source manifests | Missingness, unknown state, amount coverage, duplicates, join support | Grain/date/source rõ; không gán completeness bằng UI status | Đã thêm 22 controls + source tables vào monitor/export; missing profiles vẫn unavailable |
| B2 | Comparable-period controls | Native snapshot IDs/date ranges/definitions | Chọn baseline và hiện metric unavailable khi mismatch | Cùng currency/grain/convention; không chọn nearest date ngầm | Đã thêm auto exact-calendar/manual/disable controls P2/P4/P5; requested/resolved/status lưu URL/export |
| B3 | Analyst review từ KPI | Metric evidence ID + filters + baseline + author input | Draft finding, hypothesis, next validation, owner/status | Lưu actuals riêng khỏi judgement; revision/history/export | Đã nối all-domain review từ readout; immutable snapshot + verified source digests + revisions |
| B4 | Excel KPI report | Actual snapshot, formulas và source evidence | Workbook current/prior/bridge/definitions/data issues | Values reconcile JSON; assumptions tách actuals; formula recalculation kiểm chứng | Đã tích hợp filter-scoped XLSX, 110 KPI/control rows, source captures và review history; cached delta formulas verified, native Excel baseline/representative cases PASS; full qualification còn mở |
| B5 | Corporate analysis Excel | Verified SEC trend/coverage cùng CIK/cutoff/concept | Filing inputs, annual ratios, driver formulas, coverage và source controls trong workbook riêng | Reconcile với private JSON; formula/cache checks; giữ exact source text cạnh Excel numeric precision; missing không thành zero | Đã tích hợp export Analysis/Facts, server-derived capture, Excel formulas + saved-cache audit; native Excel baseline/representative cases PASS; full qualification còn mở |
| B6 | Principal maturity Excel | Selected SEC filing, explicit debt family và6 fiscal-year bucket facts | Typed principal amounts, subtotal/complete-total/share formulas, exact source/definitions | Source/JSON/XLSX parity; zero/missing/negative guards; debt/lease overlap không cộng | Đã tích hợp Maturities/Facts,23formulas và source/cache parity; native Excel baseline/representative cases PASS; full qualification còn mở |
| C1 | P1 temporal validation | Later booked cohort, event horizon, application chronology | OOT metrics/uncertainty/drift/stability | Freeze trước final access; mature labels; population và intended-use phù hợp | Cần data mới |
| C2 | P2 horizon PD | Multi-vintage qualified annual samples, longitudinal labels | PD12 benchmark, calibration, competing exits/support | Temporal/entity-safe splits, adequate horizon support và benchmark | Chưa đủ vintages; Clarity cần login |
| C3 | P2 qualified LGD | Supported recoveries/loss components, definitions | Loss severity theo rõ denominator/cost/discount convention | Support và coverage gates; raw/weighted ratios phân biệt | Existing observed-loss gate blocked |
| C4 | P3 DSCR/covenants | Actual borrower cashflows/debt service/legal terms | DSCR/ICR/leverage/headroom | Terms/units/period align; không join SBA/SEC/UCI tùy tiện | Một phần: explicit source principal maturity profiles/coverage proxies đã có; full debt-service/legal terms vẫn cần bổ sung |
| C5 | P4 decision-grade EL/ECL | Positions + qualified PD/LGD/EAD; staging/discount/scenario contracts | EL/ECL và sensitivity | Versioned parameters, economic/staging validation, governance review | Engines có điều kiện; source EL unavailable |
| C6 | P5 forward valuation | Collateral forecasts, verified full waterfall, security curves | Expected cashflows, price, duration/DV01/spread sensitivities | Independent valuation benchmark/legal verification | Historical replay và assumption-only bond study chưa đủ |

## 3. Data contracts tối thiểu cho từng nhóm KPI

### Snapshot và bridge

Mỗi input ghi import ID, observation date, currency, amount definition, grain, source digest và bucket partition. Region bridge cần hai partitions đầy đủ; absent bucket có subtotal 0 chỉ trong phạm vi partition được đối soát. Missing amount ở một observation phải được xử lý theo data contract, không thay bằng 0 trong bridge.

`Σ current_region = current_total`, `Σ prior_region = prior_total`, `Σ delta_region = current_total − prior_total`. Contribution dùng `delta_region/prior_total` để các vùng cộng ra relative total change; không chia cho net delta vì offsetting flows hoặc net delta bằng 0 dễ gây hiểu nhầm. Nếu prior total bằng 0, contribution là Unavailable.

### Tỷ lệ trạng thái và migrations

Stock share cần usable active denominator; migration rate cần origin-state population và observed adjacent-period destination theo convention. Ghi cả censored/unknown/exits. Count-weighted và UPB-weighted metrics không được thay lẫn nhau. Để diễn giải cure, cần episode rules và support của từng bước, không chỉ giảm stock delinquency.

### Model và policy

Metric phải ghi validation/final partition, event horizon, prevalence và support. Calibration bins có sample counts; AP benchmark cần cùng prevalence. Policy economics ghi action costs, capacity và intended use. Không gọi expected cost theo assumptions là realized profit; không thêm application approval rate từ booked-only cohort.

### Corporate và structured

Financial ratios phải có numerator/denominator facts, units, periods, filings, tags và convention. DSCR không có debt-service denominator thì unavailable; operating-income/interest-expense và reported-OCF/interest-expense chỉ là proxies được ghi rõ. ABS dùng collection/payment dates riêng, nguồn actual payments và verified contract rules; descriptive pool-minus-notes không tự là contractual trigger test.

## 4. Bố cục phân tích trong app

1. **Nguồn và phạm vi:** data date, source/run/import IDs, currency, grain và availability.
2. **Kết quả:** actual, baseline, absolute/relative delta, formula/support.
3. **Phân rã:** region/segment/state/tranche contributors có reconciliation và cách tính.
4. **Dữ liệu chi tiết:** bảng nguồn, missing/unknown, supports và confidence/qualification khi có.
5. **Hành động:** mở workflow đúng scope, review có evidence và export riêng tư.
6. **Dependencies:** metric chưa tính được phải nêu missing inputs hoặc contract chưa qualified.

## 5. Phạm vi hoàn thành và phần còn lại

Đợt A1 hoàn thành khi plan được lưu, bridge chạy trong app/export, phép tính độc lập khớp từng vùng và tổng, giao diện/table/mobile được kiểm tra và status trỏ receipt thật. Completion A1 không đồng nghĩa A2–C6 hoàn thành. Các bước tiếp theo ưu tiên tận dụng marts/workflows đã có trước khi tạo study mới; refit/rescore frozen final không được dùng để làm đẹp monitor.

Tài liệu actual và definitions: [KPI handbook](KPI_ANALYSIS_GUIDE_VI.md). Tình trạng implementation và receipts: [Five-workspace status](FIVE_WORKSPACES_STATUS.md).

## Checkpoint A2 — migration/cure readout

Đã tích hợp lifetime transitions (segment all) và 12-month confirmed-event follow-up vào monitor/export. Có 10 KPI mới và hai bảng support. Monthly history window không lọc các lifetime KPIs; basis count/UPB thay trọng số transition. Cure counts là forward-only events; chưa có probability estimand cho sustained cure/redefault từ risk set phù hợp. Receipt `private evidence omitted from public release`: 11 checks PASS, gồm mỗi origin row reconcile, count/UPB cell rates và follow-up event denominators. Tiếp theo A3: saved validation policy economics.
