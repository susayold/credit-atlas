# CreditAtlas — trạng thái 5 workspace, 10/10/2026

Sovereign archive checkpoint11/10/2026: source/API/UI now cover4editions2023–2026/42519entity-year rows. Independent680304positions PASS,59backend/HTTP/WDI tests PASS,archive browser5groups/current browser regression9groups PASS. Missing2023IADB column,2024TOTAL header alias,1341raw markers and68source count conflicts remain explicit; publication-byte availability/PD/LGD/macro stress/review gates remain open. P4.09 partial evidence expanded;50capability counts unchanged. See SOVEREIGN_ARCHIVE_EDITIONS_VI.md. Earlier2edition checkpoint below is historical.

Sovereign checkpoint 11/10/2026: two official BoC–BoE editions, 21877 entity-year rows and16 selected metrics; independent350032values PASS,56backend/HTTP/WDI tests PASS. Country tabs/filters/provisional/source-conflict/revision/timeline/components/peer search/private export now integrated; browser9groups and WDI regression10groups PASS. Source66count conflicts, historical availability, PD/LGD, macro stress and sovereign review qualification remain open. P4.09 partial evidence expanded;50capability statuses unchanged. See SOVEREIGN_DEFAULT_DATA_VI.md.

ABS-EE definition checkpoint: acquired official GovInfo2025CFR PDF/XML2files403351bytes. P5 field dictionary covers62observed mirror columns with proposed Item3correspondence,coverage and private export. Independent62PDF/XML definitions/coverage PASS,backend8PASS,browser5groups/coverage regression4groupsPASS. SEC specification ZIPHTTP403; XSD/original-filing XML/EX103/current-rule/labels/fidelity/model gates remain false. Counts unchanged. See ABS_EE_FIELD_DEFINITIONS_VI.md.

Native Excel checkpoint: six workbooks9264cells/746formula cells baseline PASS;18representative input cases/59checks PASS. SEC missing-numerator blank-to-zero bug fixed in new exports; UI3groups/backend7PASS. Original source files and frozen holdout ledger unchanged. Native visual/full-feature qualification remains open. See NATIVE_EXCEL_VALIDATION_VI.md.

P4 acceptance checkpoint 11/10/2026: fixed exact XLSX significant-digit validation and allowlisted Excel POST error messages. Backend62PASS; independent import66checks/bridge500checksPASS; browser5groupsPASS including source/bucket→draft, exports, invalid numeric rejection, valid EXAMPLE intake/mobile. Full scope/ownership/native Excel/governance qualification remains open. See P4_ACCEPTANCE_AUDIT_VI.md.


ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. See ABS_EE_MIRROR_COVERAGE_VI.md.


Checkpoint Managed Pool11/10/2026: tab/API/JSON có7kỳ,30chỉ tiêu/kỳ,210giá trị nguồn,105đối soát và14raw ratios; units nghìnUSD/signedrecoveries/source duration giữ riêng. Backend21PASS, independent source auditPASS, browser4groupsPASS. P5.02/P5.10 vẫn Một phần; xem MANAGED_POOL_ANALYTICS_VI.md.


Checkpoint staticpool11/10/2026: new issuer index +StaticPool-WOART/ManagedPool-Retail workbooks,3files606781bytes. P5 Static pool tab/API/JSON has21cohorts2021–2026 ×3metrics,1998populated and1362blank positions, source cells andage12/24 support. Backend26PASS, independent63group source auditPASS, browser4groupsPASS pool-history-qa-5930436fbc94. No loan-level target/LGD/forecast claim; Managed/6legacy sheets pending normalization. P5.02/P5.10partial unchanged. See STATIC_POOL_HISTORY_VI.md.


Checkpoint SOFR11/10/2026: acquired443New York Fed SOFRAI observations andSIFMA2025/2026US calendar,5files925844bytes. P5 ABS SOFR nguồn tab/API/privateJSON compares20periods;20/20at declared source binary precision,20/20interest cents. Raw exact19/20SOFR,15/20coupon preserved; historical15:00vintage/conforming changes/unscheduled notices remain unverified. Backend40PASS, independent20-period auditPASS, browser6groupsPASS. P5.05conditional/P5.10partial unchanged. See ABS_SOFR_BENCHMARK_VI.md.


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


**B6 maturity Excel:** Debt maturities xuất Maturities/Facts theo selected
filing/cutoff/explicit family.23 formulas cho6 bucket inputs, subtotal/complete
total/share/status; exact source text/candidates/definitions giữ riêng.
Backend **43 PASS**; browser `sec-debt-xlsx-qa-de64508d62d6`: **5 groups PASS**
cho AAPL/MSFT debt-only và AAPL lease-family missing, raw SEC/XLSX parity,
mobile/export errors và holdout ledger unchanged. Native Excel recalculation
chưa kiểm tra. [Hướng dẫn](SEC_MATURITY_EXCEL_VI.md). C4 vẫn thiếu full inputs.

**P3.08 principal maturity update:** Debt maturities tab có explicit debt-only/
debt-capital-lease family, exact filing/instant facts,6 fiscal-year buckets,
complete/partial/zero/negative gates, subtotal/total/shares và private JSON.
Latest debt-only Apple/MSFT6/6; Ford/GM0/6 (không suy không có nợ).
New corporate memo capture maturity scope/selected accession; old records giữ
immutable evidence. Backend **38 PASS**; maturity browser **4 groups PASS**,
`sec-debt-qa-662fad1cb983`; memo browser **4 groups PASS**,
`corporate-memo-qa-2cf35018c3e3`. [Chi tiết](SEC_DEBT_MATURITIES_VI.md).
Full facility schedules/interest payments/DSCR/covenants vẫn thiếu inputs.

**B5 issuer Excel:** Export trực tiếp từ Annual trends/Interest coverage theo
verified CIK/cutoff/window/expense concept. Analysis/Facts có typed source
inputs, actual/baseline/delta/driver formulas, exact text và source evidence.
Backend **44 PASS**; browser `sec-workbook-qa-03d578d3b62d`: **3 groups PASS**.
MSFT workbook audit30rows/44 numericresults/20bridges/328formulas;
native Microsoft Excel baseline/representative cases PASS; full qualification còn mở.
[Hướng dẫn](SEC_ANALYSIS_EXCEL_VI.md). C1–C6 chưa hoàn thành.

**P3.03 driver bridge:** Annual trends phân rã bốn ratios theo numerator-first
order, có exact inputs/counterfactual/effects/total/residual và comparison gates.
Backend **46 tests PASS**, `sec-bridge-tests-20261010.xml`.
Browser **6 groups PASS**, `sec-trends-qa-3cf29a711bdc`: 67 supported ratios,
65 arithmetic bridges, four issuers UI/export và mobile/outage/reload.
Source facts/model artifacts và historical memo captures giữ nguyên;
new memo annual-trend capture bao gồm bridge và method digest.

**P3.03 update:** Interest coverage có annual source fields, explicit expense
concept, operating-income/reported-OCF ratios, latest-period interpretation,
3/5/10 periods, candidate evidence và private JSON. New corporate memos capture
coverage tại selected filing date; old captures giữ nguyên. Backend **33 PASS**;
memo browser `corporate-memo-qa-0eaa9fd5829e`: **4 groups PASS**.
Coverage browser `sec-coverage-qa-1c32f79854e0`: **4 groups PASS**,
đối chiếu candidates với raw SEC companyfacts và exact Decimal ratios.
[Hướng dẫn](SEC_INTEREST_COVERAGE_VI.md). KPI Monitor vẫn có 88 business KPI +
22 quality controls; coverage là supplemental issuer analysis. C4 DSCR/covenant
vẫn thiếu qualified debt-service/contract inputs.

**P3.06/P3.10 update:** Corporate financial memo tab đã có nine narrative
sections, issuer-scoped private storage, server-derived selected-filing capture
và trend anchored tại filing date; immutable evidence/revisions/history/export.
Browser **4 groups PASS**, `corporate-memo-qa-1deb923c721e/receipt.json`;
backend **25 tests PASS**, `corporate-memo-tests-final-20261010.xml`.
QA records giữ archived, source/model/holdout ledger không đổi. Complete credit
memo vẫn cần issuer events/debt/covenant inputs; owner/reviewed chưa authenticated.
[Memo guide](CORPORATE_FINANCIAL_MEMO_VI.md). Generated app/50-capability plan đồng bộ.

**P3.03 update:** SEC Annual trends đã tích hợp3/5/10 report periods cho cùng
issuer, original-10-K selection, exact ratios/deltas và comparability gates.
Amendments giữ riêng; ambiguous/gap/concept changes không fallback.
Browser **6 groups PASS**, `sec-trends-qa-cc887f418aa3/receipt.json`;
67 supported ratios trên20 issuer-period rows được kiểm tra source arithmetic.
SEC backend **41 distinct tests PASS**. Source artifacts không đổi;
DSCR/covenant/debt schedule và PIT/PD qualification vẫn chưa đủ inputs.
[Annual trends guide](SEC_ANNUAL_TRENDS_VI.md). Generated P3.03 app/plan đã đồng bộ.

**Checkpoint B4 và nội dung app:** phần KPI lên đầu monitor, dossiers cho từng
KPI, bốn bước điều tra/domain và source/gap tables mở sẵn. **Xuất KPI Excel**
theo current filters đã tích hợp: Overview/KPI/Data/Reviews, typed actuals,
baseline, scalar delta formulas, source captures và immutable review history.
Browser workbook **4 groups PASS**, `kpi-workbook-qa-08a849344ada/receipt.json`;
backend **31 tests PASS**; KPI/baseline regression **19 PASS**,
`kpi-analysis-qa-95251bc16b81/receipt.json`. Toàn bộ 110 rows và tám comparisons
đối chiếu JSON; không refit final hoặc thay holdout ledger.
Excel chỉ recalculates comparison deltas; actuals là browser-derived captures
với server-verified sources. Native Microsoft Excel execution chưa kiểm tra.
[App/Excel guide](KPI_APP_AND_EXCEL_VI.md). C1–C6 vẫn cần inputs/qualification.

**Checkpoint B3:** all-domain KPI analyst review, private SQLite persistence,
immutable captured context + independently verified source digests at creation,
atomic revision/history và private JSON export. Browser-derived KPI calculations
được ghi riêng khỏi server source verification; không phê duyệt credit/model.
Actual UI **7 PASS**, `monitor-review-qa-f0bc7bae609e/receipt.json`, năm domain
create/update/archive/reload/export/mobile; QA records giữ archived. Backend
6 review tests + 15 existing HTTP/Excel/suite tests PASS (21 distinct tests),
gồm revision conflict, immutable snapshot, invalid source/context và local-origin
HTTP guards. [Review workflow](KPI_ANALYST_REVIEW_WORKFLOW_VI.md).
Post-integration KPI/baseline regression **19 PASS** tại
`artifacts/private/kpi-analysis-qa-cb670b239571/receipt.json`; handbook dùng export này.

**Checkpoint B2:** baseline controls cho P2/P4/P5: auto đúng previous calendar
month, manual exact prior period hoặc disable main baseline. Request/resolved/
status vào URL/export; không nearest substitution khi gap/current/future/
multiple matches. P4 kiểm tra cùng USD/region/date grain/amount/source contract.
P2 fixed YoY và overview monthly Δ có nhãn riêng; lifetime/quality/replay scopes
không đổi. **19 checks PASS**, `kpi-analysis-qa-6cc4b4dff828/receipt.json`, gồm
manual source differences, disabled comparisons/bridge, missing/current/unknown/
duplicate-month gates, reload baseline retention và toàn bộ regression trước đó.
Handbook cập nhật; còn B3/B4 review/Excel và C1–C6 inputs/qualification.

**Checkpoint B1:** 88 nghiệp vụ KPIs + **22 data-quality controls**, riêng trong
mỗi domain: reliability support, Mortgage field missingness/integrity, SBA
retained duplicates/parse counts, SEC manifest/date checks, Portfolio partition
counts/zero balance, ABS check failure shares/ledger steps. Source/grain/support
và giới hạn rõ; chưa có P1 raw-feature/P4 missing-amount profiles nên unavailable.
**18 checks PASS**, `artifacts/private/kpi-analysis-qa-90b929dc7eae/receipt.json`:
independent source/denominator reconciliation của cả 22 controls, rendered scopes,
export/filter/reload/mobile và previous numerical/source-outage checks.
No composite score/automatic certification. Handbook cập nhật từ export này.

**Checkpoint A5:** **88 KPI**, thêm tám ABS replay/cash metrics và latest-period
cash/reserve bridge, all-priority ledger. Integer-cent per-step + sequence +
total reconciliation; selected collection 2026-08-31/payment 2026-09-15.
**17 checks PASS**, `artifacts/private/kpi-analysis-qa-092358439eb1/receipt.json`:
independent Decimal cash/reserve steps/sequence, source/period payout parity,
ledger outage (source stock KPIs còn, replay unavailable), toàn bộ domain/filter/
export/mobile regressions. Access ledger unchanged. Đây là conditional reported
replay, chưa full contractual waterfall, forward valuation hoặc actual credit loss.
Các bước A1–A5 đã có readouts trong scope nêu rõ; B1–C6 còn trong plan.

**Checkpoint A4:** monitor có **80 KPI**, thêm 16 issuer ratios (AAPL/MSFT/F/GM)
với current ratio, liabilities/assets, net margin, OCF/revenue. Pinned SEC view
`sec-view-b92d9914f1dc`, filing-date cutoff 2026-10-10; report dates/filings riêng.
Exact financial fields/concept evidence + links đúng issuer/accession/cutoff.
Ford net margin missing và GM margins/cashflow ratios ambiguous giữ unavailable.
**15 checks PASS**: `artifacts/private/kpi-analysis-qa-96cfabe47d97/receipt.json`,
independent Decimal ratios, periods/units/filing cutoff và single-issuer API outage.
SEC không join SBA/default labels; chưa có DSCR/covenants/issuer PD. Handbook
đã cập nhật; checkpoint A3/A2 phía dưới giữ lịch sử. Tiếp theo A5 ABS cash bridge.

**Checkpoint A3:** monitor có **64 KPI**, thêm chín KPI policy economics cho P1:
validation support, action shares, review overflow, expected declared cost,
retrospective proxy, cost/client và difference vs accept_all. Pinned
`retail-policy-bd4b8623de28`, case đầu `lower_thresholds`; không chọn winner.
Ba bảng assumptions, sáu cases/benchmarks và action-level support; cost units
giữ riêng khỏi USD/TWD. **13 checks PASS** tại
`artifacts/private/kpi-analysis-qa-056721421547/receipt.json`, gồm all-case
cost/action decomposition và unavailable-policy safeguards. Final holdout
access ledger unchanged. Checkpoints 55/45 KPI dưới là lịch sử trước A3.

**Checkpoint A2:** monitor có **55 KPI**, thêm lifetime adjacent-pair support,
CURRENT→D3PLUS/D3PLUS→CURRENT rates theo count hoặc opening UPB, bốn confirmed
episode event counts và complete 12-month follow-up shares. Hai bảng support
được xuất cùng provenance/method versions; monthly history window không cắt
lifetime KPIs. `kpi-analysis-qa-20ea65746668`: **11 checks PASS** (origin row
reconciliation, count/UPB rates, event follow-up denominator, export/reload/mobile).
Sustained-cure event counts chưa là probability của risk set; chưa qualified PD/LGD.
Handbook cập nhật; các checkpoint 45 KPI/bridge dưới đây là lịch sử trước A2.

**Phân rã P4:** đã thêm prior/current/delta theo toàn bộ region buckets,
contribution trên prior total và top tăng/giảm; integer-cent reconciliation.
Tổng delta Feb→Mar 2026 **-13.037.124,22 USD**. Đây là grouped snapshot movement,
không phải realized loss hoặc chứng minh nguyên nhân. [Plan 15 bước tiếp theo](PLAN_KPI_ANALYTICS_NEXT_VI.md).
Nghiệm thu bridge **10 checks PASS**: `artifacts/private/kpi-analysis-qa-d384f923595f/receipt.json`.
Đối soát độc lập Decimal từng vùng/tổng; kiểm tra absent buckets, zero baseline,
missing prior, incompatible scope, inconsistent totals, export/reload/mobile.
Handbook đã cập nhật từ export của receipt này. Chưa hoàn thành các bước A2–C6.

**Checkpoint dữ liệu/KPI:** Risk monitor có 45 KPI readouts trên cả năm domain,
actual/formula/support/interpretation, monthly/year-ago comparisons khi có,
D3 numerator/denominator decomposition, calibration/split, SBA status/amount,
region HHI/top-five share/movement và ABS period/tranche tables. Source-null EL
và qualification gaps được giữ rõ; đây không phải completion mọi KPI ngân hàng.
[Handbook chi tiết](KPI_ANALYSIS_GUIDE_VI.md). Browser KPI QA **8 PASS**
(`kpi-analysis-qa-76b73d003e19`), monitor regression **10 PASS**
(`monitor-qa-a6dbe5387a8b`); frozen holdout ledger unchanged.

> Cập nhật 10/10/2026: [Plan chi tiết 50 chức năng và hướng dẫn trong app](PLAN_WORKBENCH_DETAIL.md). Mỗi chức năng có mục tiêu, inputs, phương pháp, outputs, nghiệm thu và bước tiếp theo; đây là roadmap, không chứng nhận đã triển khai đủ.

**Nghiệm thu đợt product UX rebuild (10/10/2026): hoàn tất.** Research7 tài liệu
chính thức; task workflows cho cả5 domain, selected-scope drilldowns, Excel/
review/case/cashflow launch actions, Ctrl/CmdK search, URL restore và mobile.
Đã sửa active-tab reload và discarded async pane; loan list mobile cuộn trong
card, có aria selection.10 browser receipts PASS, tổng132 checks có overlap.
Final Portfolio `exposure-browser-qa-e2cda013ece1`:19 PASS, Mortgage
`browser-qa-1d81ff3991df`:24 PASS, pending-policy/search race
`task-race-qa-b252361edc23`:4 PASS. Không refit/rescore frozen holdout.
[Research + completion audit](PRODUCT_UX_RESEARCH_AND_REBUILD.md) và
[hướng dẫn dùng](WORKBENCH_USER_GUIDE_VI.md). Đây là completion của goal UX;
toàn bộ suite/data/model qualification và50 capabilities vẫn có gap bên dưới.

Checkpoint product UX rebuild: research Taktile, CreditRiskMonitor, Moody’s,
nCino/RDC.AI và SAS public workflows. P4 now has8 task tabs, lazy study loading,
interactive concentration/search/sort/detail→source-bound review draft.
P1 has5 tasks, saved-model KPI/calibration overview and on-demand policy/
subgroup/client explanations. Global Ctrl/CmdK task search opens actual routes.
Actual browser `product-workbench-qa-b5488dc0d20b`: **14 checks PASS**;
`mvp-ux-qa-acff7c9601fa`: **11 checks PASS** across5 launch routes and search.
Actual exports/source values/mobile/reload verified; holdout ledger unchanged.
P2/P3/P5 detail redesign is implemented: Mortgage9 task routes, SBA5 tasks
with status/cohort selection, SEC4 tasks, ABS5 tasks with priority/tranche
selection, Market3 tasks. Homepage has4 direct task actions including Excel.
`remaining-domains-qa-0bccecbab2c8`: **7 checks PASS**, actual source parity,
URL/reload and mobile390px; no browser errors or consumed holdout mutation.
Final homepage/Market acceptance `mvp-ux-qa-702eb2cc9ad4`: **13 checks PASS**,
including direct Excel launch, all5 workspace routes, mobile menu/search,
Market/Bond/source tasks and URL reload; consumed holdout ledger unchanged.
Legacy harness adaptation và documentation audit đã hoàn tất ở checkpoint
nghiệm thu phía trên. Checkpoint này được giữ như lịch sử triển khai.
[Research and rebuild plan](PRODUCT_UX_RESEARCH_AND_REBUILD.md).

Checkpoint MVP UI (10/10/2026): default home, generated hero image integrated
into HTML, five domain launch cards, grouped navigation, emerald/ivory shell,
mobile menu and collapsible source evidence. Portfolio launch selects the
actual9.698-observation/USD snapshot before a personal import is selected.
Final real-browser receipt `mvp-ux-qa-1134f61f4300`: **10 checks PASS** across
five workspace routes, catalog filter, image loading, actual Portfolio
records/amount, saved Retail metrics, desktop/mobile390px and reload.
No unexpected browser errors or consumed holdout change. **15 HTTP/Excel/suite
tests PASS** after redesign. See [MVP_UI_WORKFLOW.md](MVP_UI_WORKFLOW.md).
This closes the requested viewable UI MVP, not the full50-capability suite.

Checkpoint P1 complete-cohort explanations (10/10/2026): immutable
`retail-cohort-explanations-02487bb9d1a2` extends parent
`retail-explanations-84b3ac3bab6e` to **every4.499 validation clients /995
events**, with the same frozen boosting/raw and32 training-reference clients.
All16 coalitions per client;2.303.488 model-row evaluations, no sampling or fit.
Full primary replay PASS; every original12 example reconciles. Maximum
reconstruction residual1,1102e-16. Whole-cohort mean absolute contributions:
repayment status11,75331pp, payment4,80975pp, bill2,72993pp, limit2,54478pp.
These finite-reference magnitudes differ from permutation performance reliance.

Independent audit `retail-cohort-explanations-audit-a441ed7a5c48.json`:
**45.021 checks PASS**, all4.499 clients, own saved-tree traversal/all24 group
orders, reference/ranks/tokens and complete contribution/sign distributions.
An initial audit failed a NumPy allocation on a low-memory host; final8-client
audit chunks cover the same full population, without source/model method changes
or omitted records. Actual consumed holdout ledger unchanged.

Full-cohort registry/API/UI has20-row paging (API maximum50), exact token
search, source-bound per-client exports and URL state. Tokens are study-scoped
pseudonyms, not source IDs or anonymity guarantees. No encoded predictors,
source IDs/reference rows/individual labels are served. Unknown tokens give no
prediction/export or fallback. Eight focused tests PASS, including partial
batch/original-example parity, unique ranks/tokens, pagination, cross-source
rejection and same-size/mtime source corruption.

Actual browser `retail-cohort-browser-qa-5d64a03b5226`: **8 checks PASS**,
all-cohort summary, second-page client outside the original12, private export,
exact URL reload/lowest token, unknown-token empty state and desktop/390px
mobile. Primary row actions remain visible before horizontal scrolling and
operate on the selected client. No unexpected JS errors; consumed holdout
ledger unchanged. Workflow:
[RETAIL_COHORT_EXPLANATIONS_WORKFLOW.md](RETAIL_COHORT_EXPLANATIONS_WORKFLOW.md).

Complete regression `test-batches-b9f9556ff400/receipt.json`: **1.098 tests
PASS**, all115 files/15 sequential fresh-process batches, no failures/errors/
skips or omitted collected tests; no automatic failure retries.

Live HTTP `retail-cohort-live-e5b178d0c426`: **PASS**, all4.499 clients across90
pages reconcile token/rank/probability with saved private evidence; rank4470
report/download matches exactly. Responses private/no-store and exclude
original IDs; consumed holdout ledger unchanged. Updated local app on8770.
New application-client data/qualification, reference sensitivity, causal or
regulated explanations, temporal monitoring and the full50-capability suite
remain open. Earlier checkpoints below describe their original scope.

Checkpoint P1 model explanations (10/10/2026): immutable study
`retail-explanations-84b3ac3bab6e` inspects frozen boosting/raw
`retail-freeze-3dc86f5afe01`, **4.499 validation clients /995 events**.
Whole-cohort permutation moves all encoded columns in each of four groups
together; three seeds retained individually. Mean Brier increases:
repayment status0,05545655, payment history0,00920340,
bill history0,00463848, limit0,00192186. Correlation affects interpretation;
these are fitted-model reliance diagnostics, without causal ranking or CIs.

Local exact grouped Shapley uses all16 coalitions,32 seeded training-reference
clients and12 evenly spaced validation probability ranks. Four probability
contributions +reference reconstruct predictions; maximum residual
1,3878e-17. Highest case86,26895%, reference23,26847%, repayment-status
contribution+56,62826 percentage points. Case IDs are study-local labels;
original client IDs/reference records remain private and absent from exports.
No feature-level SHAP, adverse-action qualification or actual intervention
claims. Cross-group hybrids may be unrealistic; background sensitivity remains
open. No fit/selection/final holdout scoring or ledger mutation.

Independent audit `retail-explanations-audit-d4c7f6227d3d.json`:
**375 checks PASS**, separate depth-first persisted-tree traversal, Brier,
tie-aware concordance AUC, seeded reference/rank selection and all24 group
orders for Shapley. Full source/method/output graph is pinned; first serving
replays before caching, subsequent reads hash-check all evidence.
Workflow: [RETAIL_EXPLANATIONS_WORKFLOW.md](RETAIL_EXPLANATIONS_WORKFLOW.md).
Actual browser `retail-explanations-browser-qa-eb83c145ee0f`: **5 checks PASS**,
global groups,12 local cases, selected-case private export/reconstruction,
desktop/390px mobile and unchanged consumed holdout; no unexpected JS errors.
The first browser harness was interrupted after stalling; an independent warm
page verified UI/export. A later completed run failed a CSS display assertion;
final geometry/nowrap checks account for flex-child blockification. Neither
run is counted as a PASS or used to replace the final actual-data checks.
Complete regression: **1.090 tests PASS**, all113 files across15 fresh
sequential batches, no failures/errors/skips/retries; full collection reconciles
to JUnit totals in `test-batches-94ff9b4cc30d/receipt.json`. Includes13 focused
explanation tests and the complete existing mortgage/business/portfolio/Excel/
ABS suite. A test fixture's missing internal-node value was corrected before
this run; no numerical methods or production source model changed.
Live8770 updated: `retail-explanations-live-70f96ee3fb04/receipt.json`
**PASS**, exact frozen-model/selected-case API-file parity, private no-store
exports and unchanged consumed holdout ledger.
Arbitrary-case on-demand explanations and whole-cohort local-contribution
distributions remain open;12 ranked examples do not close the complete
Explainability capability. The full50-capability suite and intended-use
qualifications remain open.

Checkpoint P1 subgroup diagnostics (10/10/2026): implemented immutable
validation demographic join → coverage/calibration/AUC → declared policy
capture diagnostics → source-bound API/UI/private aggregate export.
Actual `retail-subgroups-3cf671cf3152` uses saved policy
`retail-policy-bd4b8623de28`, case `lower_thresholds`, frozen model
`retail-freeze-3dc86f5afe01`: **4.499 clients /995 source events**.
SEX2/EDUCATION7/MARRIAGE4/AGE4 groups all reconcile to the same cohort.
With minimum50 records, four EDUCATION groups and one MARRIAGE group retain
counts but report descriptive metrics unavailable. AUC/rate denominators
also enforce minimum10 class records; unknown source codes are not merged.

Overall validation mean probability22,4589% versus event rate22,1160%,
calibration gap+0,3429 percentage points, Brier0,1323618952, AUC0,7842100055.
Declared decline rule captures559/995 events (56,1809%) and flags447/3.504
non-events (12,7568%). These are descriptive validation diagnostics, without
confidence/significance intervals, temporal monitoring or fairness certification.
Demographics are joined only for selected validation IDs; model predictors,
fit/selection and consumed final holdout remain unchanged.

Independent NumPy/sklearn/Decimal audit
`retail-subgroups-audit-d3f5e79668a4.json`: **314 checks PASS**.
Actual browser `retail-subgroups-browser-qa-9c07c0d9e7bb`: **5 checks PASS**,
source-bound SEX/EDUCATION/AGE dimensions, retained low-support groups,
scoped private export, desktop/390px mobile and unchanged holdout ledger;
no unexpected browser errors. Workflow:
[RETAIL_SUBGROUPS_WORKFLOW.md](RETAIL_SUBGROUPS_WORKFLOW.md).
Complete regression: **1.077 tests PASS**, all111 files in14 fresh sequential
batches, no failures/errors/skips/retries. Complete collection reconciles to
JUnit counts in `test-batches-e08f87732391/receipt.json`; includes12 focused
subgroup tests and existing mortgage, business, portfolio, Excel and ABS tests.
Live8770 restarted with the updated service. Receipt
`retail-subgroups-live-f4e0fb0873fc/receipt.json`: **PASS**, exact saved/API
education-scope parity, policy/freeze binding, private/no-store export and
unchanged consumed holdout ledger.
Whole five-workspace goal remains active. Intended-use cohorts, uncertainty,
real costs/interventions, explanations and temporal monitoring remain open.

Checkpoint P1 policy workbench (10/10/2026): fixed boosting/raw validation
scores → declared threshold/action/cost engine → capacity diagnostics →
preview → immutable policy version → source-bound private export. Actual
`retail-policy-bd4b8623de28`: 4.499 validation clients/995 source events;
3 declared cases plus constant-action baselines. Giả định capacity600:
review demand2.277/1.053/892, overflow1.677/453/292. Cost units minh họa,
không source cash losses hoặc actual application/intervention outcomes.
No threshold optimization/new model selection/fit/final holdout scoring.

**1.065 tests PASS** (375 engine +690 application), all109 test files in
14 sequential fresh batches; no failures/errors/skips/automatic retries.
Full collected scope reconciled to JUnit counts:
`test-batches-388f12b7a161/receipt.json`. Batching giải phóng memory giữa
processes, không bỏ tests hay thay numerical methodology. P1 focused20tests,
independent saved-score/Fraction audit `retail-policy-audit-05ddcb458e25.json`
**184 checks PASS**, actual consumed holdout ledger unchanged. Cached reads
hash-check complete frozen lineage; same-size/mtime source mutation rejected.

Actual browser `retail-policy-browser-qa-ee755fd4f0a0`: **9 checks PASS**,
preview/edit-save invalidation, new version/export/reload, reversed thresholds,
explicit invalid policy without fallback, 390px and unchanged holdout. One
intentional invalid preview HTTP400 console message is identified separately;
no unexpected browser errors. First browser run's expected error-text assertion
was corrected; first source/model checks were not replaced by fixtures.
Live8770 restarted: `retail-policy-live-b7738c5da1d2/receipt.json` **PASS**,
exact API/file parity, private export, final mobile button layout, unchanged
holdout. Two cached scoped reports took2,588/2,576seconds. Primary full replay
on first access precedes cached hash checks; measurements do not include cold
catalog/model verification.

Workflow: [RETAIL_POLICY_WORKFLOW.md](RETAIL_POLICY_WORKFLOW.md).
Real application data/cost calibration/affordability/limit-pricing, collections
outcomes, explanations/subgroups/monitoring and remaining five-workspace work
are still open. Whole goal remains active; this is not suite completion.

Checkpoint Excel, stability và review (10/10/2026): P4 Exposure có native
XLSX intake → typed private import → scoped Excel report. Template có 2 sheets;
report có 6 sheets, editable factorized scenario formulas, saved ECL/VaR/ES,
review notes và terminal reconciliation. Source March: 9.698 records,
USD 915.208.989,12; adverse Excel EL khớp Python trong một cent. Giữ zero,
missing risk và native currency; không biến source UPB thành EAD.

Excel focused tests **9 PASS**, gồm numeric precision, malformed/macros,
formula cache rejection, source lineage, same-origin HTTP và review currency
scope. Saved-XLSX independent audit **PASS**:
`excel-workbook-audit-20261009T170210086716+0000.json`. Cả 8 sheets được render
và kiểm tra; chưa chạy bằng Microsoft Excel desktop. Actual browser **19 checks
PASS**: `exposure-browser-qa-349d06c7515b`, gồm XLSX download/upload, mobile,
source-bound inventory/bridge/scenario/ECL/tail/review và no JS errors.
Full batch: **1.043 PASS, 1 setup OOM** (223,68s); affected bankruptcy holdout
fixture rerun independently **1 PASS** (9,69s). Sau final currency-scope fix,
9 Excel tests PASS, thêm một regression test. Không tuyên bố một full batch
hoàn toàn xanh; không refit/rescore actual consumed holdouts.

Multi-seed diagnostics đã có `exposure-convergence-0741003b87f4`: 3 seeds ×
1.024/4.096/6.144 draws, 4 cases, 9.602 positions; full primary replay và
independent diagnostic audit `exposure-convergence-audit-edd2670b9753`
**312 checks PASS**. Three seeds/ranges không chứng nhận convergence hoặc ES CI.
Versioned source-bound portfolio reviews đã có; actual
`portfolio-review-d865f99b6cf8` revision1 vẫn **draft**, automated owner pending
analyst assignment, không accounting/capital sign-off. XLSX export chỉ chọn
current review có đúng native currency.

Live8770 đã cập nhật và private XLSX/template/source control/current draft parity
**PASS**: `excel-live-019213c72060.json`.

Hướng dẫn: [EXCEL_WORKFLOW.md](EXCEL_WORKFLOW.md),
[PORTFOLIO_STABILITY_AND_REVIEW.md](PORTFOLIO_STABILITY_AND_REVIEW.md).
Excel intake hiện áp dụng P4; arbitrary company formats và adapters cho các
workspace khác vẫn mở. Toàn bộ 5 workspace/50 capabilities chưa hoàn thành.
Các checkpoints bên dưới giữ lịch sử evidence, không phải trạng thái mới nhất.

Checkpoint tail risk: **1.019 tests pass** (375 engine + 644 application),
full suite 181,19 giây. P4 finite-position Monte Carlo dùng seed tái lập,
common random numbers, Gaussian asset correlation và systemic LGD spread;
native-currency mean/SE, VaR/ES, boundary ties và joint-tail contributions.
Actual `exposure-tail-10a079f18dc9`: 9.602 CURRENT positions, seed 20261009,
4.096 draws ×4 cases. 99% tail mass 40,96 draws; correlation/recovery/risk
inputs đều là assumptions minh họa, chưa calibrated/qualified capital/ECL.
Independent original-CSV/Fraction/Gauss-Legendre/empirical-tail audit
`exposure-tail-audit-6fe926d3a1ab`: **94.393 checks PASS**. 16 focused tests
PASS, gồm reproducibility, native currencies, PD0/1, extreme quantile upper
bound unavailable, fractional ES/tie attribution, cache corruption và ES fault.
API/UI/private JSON export có source binding và full replay trước serving.
Actual combined inventory/bridge/scenario/ECL/tail browser **16 checks PASS**:
`exposure-browser-qa-124c0e921076`; desktop/mobile 390px, seed/tail support,
joint ES contributions, scoped export parity, reload và no JS errors.
Live8770 đã restart và tail API/private export parity PASS; receipt
`artifacts/private/exposure-tail-live-20261009.json`.
Workflow: [EXPOSURE_TAIL_WORKFLOW.md](EXPOSURE_TAIL_WORKFLOW.md).
Multi-seed convergence, actual calibrated default/recovery/contract adapters,
borrower linkage, finance/review và các mục còn lại của toàn 5 workspaces/50
capabilities vẫn mở; không coi software checks là qualification thực tế.

Checkpoint ECL trước đó: **1.003 tests pass** (375 engine + 628 application),
full suite 390,96 giây. P4 declared cash-shortfall ECL/staging engine, API/UI
và exact private export đã có. Conditional hazard → survival/marginal PD;
explicit SICR/default snapshot policy; stage1 default-event cutoff giữ all
future cash/recovery, stage2 lifetime và stage3 declared default month0.
Source March2026:9.602 CURRENT eligible/96 excluded. Lịch36-month bullet,
monthly EIR, risk/recovery/weights và stages đều là assumptions minh họa;
chưa accounting qualified/actual contract evidence. Receipt
`exposure-ecl-ba27d7207a44`, independent original-CSV/Fraction audit
`exposure-ecl-audit-59232552bdd3`:1.885 checks PASS. 28 focused tests PASS,
gồm timing beyond month12, DPD/SICR boundaries, exact weighting/currency,
source corruption và independent marginal-probability fault detection.
Actual combined inventory/bridge/scenario/ECL browser14checksPASS
`exposure-browser-qa-9f5c9c210974`; desktop/mobile, segment/scenario switches,
default-month cutoff, exact scoped exports, reload. Live8770 ECL/report parity
PASS. [EXPOSURE_ECL_WORKFLOW.md](EXPOSURE_ECL_WORKFLOW.md) có contracts,
formulas, illustrative results và rerun commands. Actual cash/EIR/risk adapters,
POCI/revolving/cure/forbearance policies, tail/review và các mục còn lại của
toàn5workspace/50capabilities vẫn tiếp tục.

Checkpoint scenario trước đó: **975 tests pass** (375 engine + 600 application),
full suite 178,75 giây. P4 declared scenario/stress workbench đã có versioned
assumptions, eligibility/exclusions, PD odds/LGD/EAD shocks, clipping counts,
ordered EL attribution và rational private export. Actual source March 2026:
9.602 CURRENT eligible / 96 excluded; source EL vẫn unavailable. Baseline,
mild/adverse và boundary sensitivity dùng parameters minh họa chưa calibrated.
Receipt `exposure-scenario-9655e30419ec`, independent original-CSV Decimal(90)
audit `exposure-scenario-audit-4a1b476f5775`:2.755 checks PASS. 25 focused tests
PASS, gồm source mutation trong projection và wrong-effect fault detection.
Actual inventory/bridge/scenario browser 11 checks PASS
`exposure-browser-qa-51f387098065`; đã sửa version dropdown overflow ở390px.
Live8770 scenario/export JSON parity PASS. Chi tiết:
[EXPOSURE_SCENARIO_WORKFLOW.md](EXPOSURE_SCENARIO_WORKFLOW.md).
Calibrated risk/macro adapters, cash-flow attribution, ECL/staging/tail/review
còn tiếp tục; toàn bộ 5 workspace chưa hoàn thành.

Checkpoint movement trước đó: **950 tests pass** (375 engine + 575 application),
full suite 167,76 giây. P4 source-bound movement bridge tháng 02 → 03/2026
đã có: 9.698 matched same-currency,106 opening-only,0 closing-only;
reported UPB USD 928.246.113,34 → 915.208.989,12, continuing change
−13.037.124,22, residual 0. 106 opening-only records có opening UPB 0;
không suy diễn exit reason/cash-flow decomposition. Immutable receipt
`exposure-movement-dbd1ecad612e`, independent original-CSV/Fraction audit
500 checks PASS `exposure-movement-audit-a691cd413f63`.
15 focused tests PASS; actual inventory/bridge browser 8 checks PASS
`exposure-browser-qa-2aca99dbf228`, gồm exact scoped export/reload/mobile.
UI/API/private export có bucket bridge và observed state transitions.
Chi tiết: [EXPOSURE_MOVEMENT_WORKFLOW.md](EXPOSURE_MOVEMENT_WORKFLOW.md).
Versioned scenario/stress, cash-flow attribution, ECL/staging/tail/review
còn tiếp tục; toàn bộ 5 workspace chưa hoàn thành.

Checkpoint typed import trước đó: **935 tests pass** (375 engine + 560 application),
full suite 179,51 giây. P4 typed exposure inventory đã có CLI import,
source-bound API/UI và exact private export. Actual March 2026 Freddie sample:
9.698 observations, 141 zero UPBs, USD 915.208.989,12 reported principal;
PD/LGD/EAD chưa có nên research EL unavailable. Independent Fraction/SQL
audit 66 checks PASS; 26 focused tests PASS; actual browser 6 checks PASS
`exposure-browser-qa-4bac732d7b4c`, gồm export/reload/mobile và invalid-source
fail without fallback. Declared factorized research EL engine đã được kiểm thử,
chưa có actual calibrated risk inputs hoặc accounting ECL/staging/stress.
Chi tiết: [EXPOSURE_IMPORT_WORKFLOW.md](EXPOSURE_IMPORT_WORKFLOW.md).

Checkpoint HMDA trước đó: **909 tests pass** (375 engine + 534 application),
full suite165,14giây sau page-URL bound fix. P2 HMDA cohort comparison đã có:
3presets,826joint-martrows,ordered/disjointattrition,fixed2023decided weights,
incompletefullsupportunavailable và explicitcommonsubset. Independent rawCSV
audit70checksPASS,12focusedtestsPASS; actualbrowser17checksPASS
`hmda-browser-qa-190c01d247fb` (export,reload,scope/mobile). Chi tiết:
[HMDA_COHORT_WORKFLOW.md](HMDA_COHORT_WORKFLOW.md).
HMDA dated lender API/UI/exact labeled export đã có,
6focusedtests và actual browser12checksPASS (`hmda-browser-qa-933388f8532a`).
HMDA lender reference đã tải
4 files/286.874 bytes; exact year+LEI names match346.456/347.056rows,
600 unmatched giữ nguyên, independent raw JSON/CSV SQL audit15checksPASS.
73 related HMDA tests PASS (21 mới + 52 existing),16,45giây ở checkpoint
source-only trước đó; full897 phía trên đã gồm cả6APItests mới.
County actual download HTTP403; coverage standardization/findings còn tiếp tục.
Chi tiết: [HMDA_REFERENCE_WORKFLOW.md](HMDA_REFERENCE_WORKFLOW.md).
P2 HMDA đã tải347.056 public records/99fields,
canonical/marts và independent SQL audit24checksPASS; HMDA UI/API/scoped export
đã chạy,16 focused tests và browser10 checks PASS.
P5 đã có engine waterfall trước acceleration với
31 tests tình huống, replay có điều kiện trên 20 báo cáo (720 đối chiếu nguồn),
và audit SQL độc lập (580 kiểm tra), đều không có kiểm tra thất bại.
Selected prospectus terms và 140 kiểm tra lãi bằng số hữu tỉ độc lập cũng PASS.
ABS period UI/API/private export đã chạy; browser acceptance 12 checks PASS,
bao gồm exact export, payment-year boundary, URL reload và mobile 390px.
Xác minh toàn bộ nghĩa vụ/hợp đồng và scenario workbench còn tiếp tục. P3 one-time final
`bankruptcy-holdout-907870affe8d`:591 statements/41 events,chosen boosting_platt;
AUC0,962793792/AP0,863689087/Brier0,021610995/logloss0,087159890.
1000 final group-bootstrap draws,585 groups; AUC95% interval
[0,927075734,0,992538961]. Original-source ZIP/horizon ledger **completed**;
replay/failed access cannot reopen it. Saved-score/metric/ledger verification
PASS without rescoring final predictors. No refit/reselection/threshold tuning.
Research model card: [BANKRUPTCY_FINAL_MODEL_CARD.md](BANKRUPTCY_FINAL_MODEL_CARD.md).
Not firm-independent/OOT/production evidence. Model-result UI/API/private aggregate
export đã tích hợp: `bankruptcy-model-view-2f63a60b48df`. Separate validation/final,
cohort support, reliability và 95% intervals đọc saved evidence; không rescore.
[Model app workflow](BANKRUPTCY_MODEL_APP_WORKFLOW.md). Findings/review còn thiếu. P3 actual development assessment
`bankruptcy-assessment-0e7cb5cc894d`: constant/logistic/boosting fit train,
separate Platt calibration,5 candidate validations on887 statements/62 events.
Native/JSON parity max difference0,0 trên5.319 development rows. Group bootstrap
`bankruptcy-comparison-e3ee221ca493`:1000 valid draws/879 groups; calibrated
boosting-minus-calibrated-logistic Brier interval[−0,015113238,−0,002237125].
Prefit rubric selected boosting_platt; authoritative
`bankruptcy-freeze-cebc982ca176` copied/pinned model/encoder/calibration.
Validation AUC0,967917889/AP0,864015573/Brier0,021898554/logloss0,085251500;
not final/OOT/production metrics. Final/ledger/card đã có ở checkpoint mới
phía trên; model-results UI/API/export đã có ở checkpoint mới nhất. Chi tiết:
[BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md](BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md).
P3 one-year bankruptcy protocol đã freeze
`bankruptcy-study-e0c65ad465e3`: train3546/calibration886/validation887/
reserved-final591, 0 exact groups crossing partitions. Development features
`bankruptcy-features-fc51ea164f93`: 5.319×128, final encoded rows0; independent
SQL audit `bankruptcy-feature-audit-cf483766dd8c` PASS (max absolute error
9,5923e−14). Fixed models/calibration/selection rubric đã khóa trước fitting;
model và one-time final đã có ở checkpoint mới phía trên. Registry original-ARFF hash+horizon giữ
cùng study khi case được tạo lại. Xem
[BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md](BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md).
P3 bankruptcy ratio app đã chạy trên
`bankruptcy-case-e1e67482a2b4` → `bankruptcy-view-e99b04caf0ed`: 43.405
statements, 5 separate horizons, 64 feature definitions/320 quality profiles.
Official original ARFF ZIP đã tải thêm (8.834.471 bytes); xác minh 2.092 CSV
rounding differences, giữ CSV mirror/difference table và dùng original ratios.
Browser `bankruptcy-browser-qa-48cc91e0317b` 8 checks PASS; independent SQL
duplicate audit `bankruptcy-duplicates-d2938d9890a8` PASS. Chưa qualified
entity-disjoint/OOT/production validation. Chi tiết và model sequence:
[BANKRUPTCY_RATIO_WORKFLOW.md](BANKRUPTCY_RATIO_WORKFLOW.md).
P5 market-context/assumed-bond app đã chạy trên
`market-case-1f4a60893d6c` → `market-view-171f41206767`: 46.675 native
observations, 2.684 monthly rows, 16.908 aligned native dates. Browser receipt
`market-browser-qa-d459f030ced9`: 13 checks PASS, gồm chart styling/gap,
raw-value retention, exports, mobile và P4/P2 navigation. Independent bond
audit `bond-numerics-0fb948a7d272`: 180 scenarios PASS.
994 DGS30 quotes mâu thuẫn với documented discontinuation; fresh HTTP vẫn
trả cùng conflict. Giữ raw values, quarantine khỏi usable values/chart;
historical Treasury semantics chưa qualified. Chi tiết và source evidence:
[MARKET_AND_BOND_WORKFLOW.md](MARKET_AND_BOND_WORKFLOW.md).
P4 historical foundation: `fdic-history-3e5ccce29513` →
`bank-panel-13a7ad74220f`: 42 quý 2016Q1–2026Q2, 214.809 records,
6.290 CERT; independent JSON audit `bank-panel-audit-29a7dbdd5fa2` PASS,
0 differing rows. 714 EQ null, 217 negative EQ, 722 consolidation records
được giữ; sums chưa là industry totals. P4 UI/export/timeline đã chạy trên
`bank-view-6363e3f7fd89`, browser `bank-browser-qa-3b92675e9f79` 11 checks PASS.
Xem [FDIC_BANK_PANEL_WORKFLOW.md](FDIC_BANK_PANEL_WORKFLOW.md) và
[BANK_APP_WORKFLOW.md](BANK_APP_WORKFLOW.md).
P3 SBA đã có dictionary-backed typed adapter, sáu Parquet files và bốn
descriptive marts trên 2.190.504 source records. Current verified case:
`business-sba-21c568f10f7d`. P3 descriptive UI/scoped report đã chạy trên
snapshot `suite-view-74e07524f6d0`; browser QA `suite-browser-qa-f5d061d221cd`
đạt 16 checks. Chưa qualified default model;
chi tiết semantics/grain/quality ở [SBA_BUSINESS_DATA_CONTRACT.md](SBA_BUSINESS_DATA_CONTRACT.md).
P1 đã freeze `retail-freeze-3dc86f5afe01`, chọn boosting/raw từ validation,
và chạy one-time evaluation `retail-holdout-061c440ea867` trên 3.001 clients,
664 events: AUC **0,777878**, AP **0,543521**, Brier **0,136377**, log loss
**0,432887**. Saved scores/aggregate metrics đối chiếu thành công; không refit
hoặc chọn lại model sau holdout. Rubric được đặt sau development inspection;
split ngẫu nhiên, không OOT và chưa qualified production. Chi tiết đầy đủ:
[RETAIL_FROZEN_HOLDOUT_AND_MODEL_CARD.md](RETAIL_FROZEN_HOLDOUT_AND_MODEL_CARD.md).

Yêu cầu hiện tại: tải các nguồn có thể tiếp cận trước cho cả 5 module, lập kế
hoạch chi tiết và tự code. Toàn bộ suite chưa hoàn tất; kế hoạch đầy đủ ở
[PLAN_FIVE_WORKSPACES.md](PLAN_FIVE_WORKSPACES.md).

## Acquisition thật đã hoàn tất

Batch `suite-619b1ee9aa8c`: **20/20 files tải và profile thành công**, tổng
**1.042.444.750 bytes**. Không có failed source trong batch. Raw và receipts:
`D:\data\Codex\credit-atlas\data\private\public-suite\suite-619b1ee9aa8c`.
Các source metadata/dictionary được tính là file, không tính thành populations.

| Workspace | Dữ liệu thật đã có | Mức hỗ trợ hiện tại |
|---|---|---|
| P1 Retail | UCI 350: 30.000 dòng, 6.636 target=1 / 23.364 target=0; typed facts và 180.000 history rows | Boosting/raw freeze + 3.001 final-test clients và aggregate app/report đã chạy; intended-use/subgroup/policy/monitoring còn thiếu |
| P2 Mortgage | Freddie 2012: 50.000 loans / 4.510.559 loan-months; macro; HMDA MD home-purchase/site-built 2023–2025:347.056 public applications/purchases | Descriptive D01 app đã chạy; HMDA canonical/7.477 dimension marts và aggregate app/API/scoped export đã có; reference joins/coverage/review còn tiếp tục; multi-vintage model chưa qualified |
| P3 Business | UCI365 original-ARFF 43.405 statements/5 horizons/64 financial variables, CSV mirror và 2.092-cell precision audit; SBA 2.190.504 typed records/dictionary/4 marts; SEC 105.441 fact entries/13.374 filings/67 annual research statements | SEC issuer/filing/units/period/ratio explorer và scoped export, SBA/ratio UI; horizon1yr development/freeze/one-time final/group uncertainty/model card và model-result UI/API/export đã có. Findings/review, SEC memo và SME timing còn thiếu |
| P4 Observatory | FDIC 42 quý 2016Q1–2026Q2: 214.809 typed bank-quarter records; failures/assistance: 4.117 separate records; World Bank 122.892 annual rows/7 indicators | Bank panel/peer/quarter/timeline và country same-year/universe/timeline/export đã chạy; consolidation-adjusted industry totals, sovereign-default/vintage và loan-book loss workflows còn thiếu |
| P5 Market/structured | 46.675 native market observations, 994 DGS30 conflicts quarantined; World Omni 2025-A prospectus và 20 monthly certificates/2.980 typed metrics | Market/bond lab và conditional ABS period/waterfall/tranche/checks/private export đã chạy; actual security quotes, loan-level collateral, full legal/obligation evidence, projections và valuation còn thiếu |

UCI retail và bankruptcy có CC BY 4.0, cần attribution. SBA page ghi U.S.
Government Works. FDIC data public. ICE OAS có source terms internal-use-only,
giữ private, không phân phối dataset/derivatives ra ngoài. Mọi downloaded
source trong batch vẫn có `model_qualified=false`, `public_release_approved=false`.

## Những khác biệt quan trọng thấy trực tiếp trong payload

- UCI bankruptcy metadata nêu 10.503 instances, nhưng CSV chứa cả 5 subsets:
  7.027 / 10.173 / 10.503 / 9.792 / 5.910. `year` là code của subset/horizon,
  không phải calendar year. Source mô tả corresponding bankruptcy horizons
  5/4/3/2/1 năm. Chưa xác minh entity-disjointness giữa subsets.
- Bankruptcy A37 thiếu 18.984/43.405 giá trị; missingness cần feature review,
  không điền zero. Ratio extremes cần kiểm tra trước modelling.
- SBA 7(a) dùng status `P I F`, còn 504 dùng `PIF`; `EXEMPT`, `CANCLD`,
  `COMMIT`, `NOT FUNDED`, `CLOSED` có mặt ở source-specific segments.
  Chưa chuẩn hóa chúng thành default/negative outcomes.
- FDIC financials trong batch 20-file đầu là một quý và reconciles meta.total
  với unique CERT×REPDTE. Batch riêng mới đã bổ sung 42 quý; đây vẫn là
  reporting panel latest-revised, không historical as-of release archive.
- FRED observations giữ native dates và missing source values. Latest revision
  không chứng minh historical availability; daily Treasury yields không phải
  bootstrapped zero curve. ICE OAS payload hiện có 794 native rows; không giả
  định nó cung cấp full historical horizon.

Nguồn chính thức: [UCI retail](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients),
[UCI bankruptcy](https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data),
[SBA FOIA](https://data.sba.gov/dataset/7a-504-foia),
[FDIC API](https://api.fdic.gov/banks/docs),
[Treasury DGS10](https://fred.stlouisfed.org/series/DGS10),
[ICE OAS notes](https://fred.stlouisfed.org/series/BAMLC0A0CM).

## Code và actual warehouse run

`src/credit_atlas/public_sources.py`: fixed official catalog, bounded HTTPS
downloads, private immutable receipts, full CSV profiles, FDIC completeness
and bank-quarter grain checks. Native Windows curl; không computer use,
không credentials hoặc automatic redirects.

`src/credit_atlas/public_suite.py`: verifies raw hashes và per-source/batch
contracts, builds source-native Parquet, checks row counts and preserves CSV
sentinels/empty strings. Source hashes reverified before completion. CSV fields
remain source-native strings until typed domain adapters have reviewed meaning.

Latest successful warehouse:
`artifacts/private/source-warehouse-281662304758/warehouse-complete.json`.
**17 tables, 2.320.165 rows** across source-native datasets. Two UCI metadata
JSONs and one SBA dictionary XLSX remain original reference artifacts.
No borrower/entity cross-source joins or model fitting performed in this run.
Earlier failed warehouse attempts are retained as failures.

Full suite after these changes: **482 tests passed** (375 engine + 107
application). New checks cover source boundaries, incomplete API pages,
bank-quarter duplicates, missing/horizon profiles, HTTP redirects, modified
raw hashes and preservation of native CSV empty/sentinel values in Parquet.

Retail extension checkpoint: **490 tests passed** (375 engine + 115 application).
Latest actual case: `artifacts/private/retail-case-470bdb40682f/case-complete.json`.
All 30.000 typed clients and 180.000 history rows reconcile to raw values with
independent bidirectional SQL EXCEPT ALL: zero differing rows. Predictor contract
has 13 monetary numeric fields and six status categorical fields; four
demographic fields and source IDs excluded. Split 60/15/15/10 is deterministic,
client-disjoint and class-stratified, explicitly not temporal/OOT. Model fitting
and final-test scoring had not occurred at this canonical checkpoint. See
[RETAIL_DATA_AND_PROTOCOL.md](RETAIL_DATA_AND_PROTOCOL.md).

Retail feature preparation is implemented and actually run:
`artifacts/private/retail-features-d53aa8ba9ed6/features-complete.json`.
17.999 train-only encoder fit rows; 81 encoded columns; 26.999 development
rows across train/calibration/validation. JSON encoder reload and saved Parquet
matrix parity both pass for every row. Split assignments are independently
rederived from client labels before joining predictors. Reserved final-test
predictor rows are excluded and the development transform refuses that role.
Feature preparation itself does not fit risk models.
At the later development-assessment checkpoint, three retail models were
actually fitted: constant, logistic and bounded histogram boosting, with
separate calibration and same-cohort validation. See
[RETAIL_DEVELOPMENT_RESULTS.md](RETAIL_DEVELOPMENT_RESULTS.md) for actual
metrics, parameters and limits. Run `retail-assessment-b8b96f471254` verifies
JSON/native model parity for all 26,999 development clients and rederives all
six validation metric sets from saved scores. Champion selection and reserved
final-test evaluation had not occurred at this development checkpoint; these random-split results
do not complete P1 or imply out-of-time/general-purpose production validation.
Paired validation uncertainty subsequently completed in
`retail-comparison-b560ea676127`: 1,000 class-stratified client bootstrap
replicates with shared indices across all six score variants. ROC AUC/AP
boosting-minus-logistic intervals include zero; conditional Brier/log-loss
improvement intervals favor boosting. That comparison run did not select a champion or score final test.
Details and statistical limits: [RETAIL_VALIDATION_UNCERTAINTY.md](RETAIL_VALIDATION_UNCERTAINTY.md).
Latest full suite after paired comparison: **507 passing tests** (375 engine +
132 application). New evidence checks require paired client ordering even when
a modified score artifact has an updated digest. No source/feature/model
artifact was changed by the comparison run.
Feature checkpoint software suite: **497 passing tests** (375 engine + 122
application). Added checks cover train-only scaling, serialized encoder state,
unseen categories, rejected nonfinite/boolean values and a synthetic integration
case with deliberately poisoned final-test numeric fields: feature preparation
succeeds without selecting those final-test predictors.

Latest complete suite after development assessment: **501 passing tests**
(375 engine + 126 application). New checks exercise JSON tree threshold/leaf
semantics, reliability boundary/calibration support, all three native/persisted
model fits with poisoned final-test predictors excluded, and rejection of
changed development feature values before fitting.

Commands from `D:\data\Codex\credit-atlas`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/acquire_public_suite.py
.\.venv\Scripts\python.exe -X utf8 scripts/build_public_suite.py --suite suite-619b1ee9aa8c
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_retail.py --suite suite-619b1ee9aa8c
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_retail_features.py --case retail-case-470bdb40682f
.\scripts\test.ps1
```

## P2 HMDA application source/canonical checkpoint

`hmda-source-979e0862af13`: 13 files / 133.468.928 bytes, official HTTP API
và matching-year official cache redirects; 2023/2024/2025 Maryland,
home purchase/site-built. 347.056 public records / 99 fields; CSV count và
public amount sum đối chiếu before/after source aggregates.
`hmda-case-94ca64da2e30`: full raw-field Parquet, selected typed facts,
3 annual summaries / 7.477 rows trên8 dimension marts. Income numeric1111
là value, chỉ categorical denial code1111 là Exempt. NA/Exempt/blank không0.
450 exact public duplicate groups / 682 beyond-first rows retained;
privacy-coarsened public equality không phải loan identity.
Decided denominator actions1+2+3:71.956/74.390/72.103; denied7.497/7.223/7.246.
No default labels, borrower linkage, historical availability, national
representativeness hoặc causal/compliance certification. LTV header/dictionary
name mismatch giữ raw/unqualified. HMDA UI/API/private scoped export đã có;
reference names/coverage/review còn tiếp tục.
35 source/canonical focused tests và independent-auditor test PASS;
actual `hmda-audit-983042fc2736`:24 checks PASS/0 failures, raw99fields
và marts bidirectional differences0; denominator/optional-field units/sentinel
và duplicate counts independently reconciled.
[HMDA_APPLICATION_WORKFLOW.md](HMDA_APPLICATION_WORKFLOW.md).
HMDA view `hmda-view-89499c7d1d02`: intersecting year/LEI/county/loan-type/DTI
filters,8 action outcomes,denominator-aware breakdown,timeline,filtered quality
và private exact aggregate export. Full cold verification + every-read hash
cache guards; changed sources unavailable. Browser `hmda-browser-qa-e939cd411bc7`:
10 checks PASS, no JS errors, desktop/mobile screenshots inspected.
Live API8770 HTTP200:2025 records117.817/decided72.103/denied7.246;
warm intersecting2024/county24031/FHA/DTI45 query46records/46decided.
[HMDA_APP_WORKFLOW.md](HMDA_APP_WORKFLOW.md).


## P4 country source và app checkpoint

World Bank source `country-source-f58e3805c53f`: **22 files / 30.437.643 bytes**,
HTTP API V2, seven WDI indicators 1960–2025, footnotes/metadata/glossaries.
Canonical `country-case-a651e2bdc3d1`: **122.892 rows**, 217 economies/49 aggregates;
64.452 source NULL preserved, no imputation/carry-forward. Missing source ISO3
2.310 rows resolves only by exact unique catalog ISO2 + trim-equivalent label;
924 native-name whitespace differences and blank API units remain inspectable.
Independent `country-audit-ca473df34ec4` SQL reconciliation: **PASS / 0 differing
rows / 0 duplicate keys / 0 orphans**, saved annual coverage/queries/notebook.
Country view `country-view-b6e001ce51a3` provides private scoped API/report,
timeline, same-year cross-section, separate economy/aggregate universe,
latest-known profile with explicit reference year and definition cards.
Latest revised snapshot is not historical publication availability; no sovereign
PD/rating, causal stress or regulatory qualification. See
[COUNTRY_OBSERVATORY_WORKFLOW.md](COUNTRY_OBSERVATORY_WORKFLOW.md).
Actual browser `country-browser-qa-2bfc8b3b2089`: **10 checks PASS**,
VNM 2025 NPL NULL stays unavailable, GDP growth annual value, 49 aggregate
cross-section riêng, export parity, ISO2 missing-ISO3 evidence, URL reload,
390px mobile, independent P2/P3/P5 navigation và no mortgage-run dependency.

## P3 SEC financial normalization checkpoint

Source `sec-source-13cf03606e0c`: **14 JSON files / 18.105.032 bytes**,
four explicit CIKs AAPL/MSFT/F/GM, companyfacts + recent/older filings arrays.
Canonical `sec-case-33077fe45722`: **105.441 fact entries / 13.374 filings /
67 annual research statements**, exact numeric strings, preserved units,
taxonomy/concept/start/end/filed/fiscal labels/frame and source ordinals.
Independent `sec-audit-b3f7c79ffc11`: **0 differing fact/filing rows**;
201 supported Decimal ratios verified,67 unavailable ratio states retained.
Original facts/Parquet types and qualification flags verified; changed canonical
schema rejected even when numeric values and updated file digest match.
View `sec-view-b92d9914f1dc`: issuer/filing/date-cutoff explorer and private
scoped exports. Source conflicts remain visible: Ford unsupported net-income
tag and GM conflicting revenue candidates do not yield invented ratios.
Current SEC API / filing-date filter is not certified historical availability;
custom/dimensional disclosures/debt/covenants/memo workflow remain open.
See [SEC_ISSUER_FINANCIALS_WORKFLOW.md](SEC_ISSUER_FINANCIALS_WORKFLOW.md).
Actual browser `sec-browser-qa-a44fd5141a8a`: **10 checks PASS**. AAPL
filing-specific period/ratio, cutoff/exact export parity, no future fallback,
Ford missing/GM conflict evidence, URL reload,390px mobile,no mortgage-run
dependency và P2/P3/P4 navigation. Live API HTTP200; desktop/mobile inspected.

## P5 issuer ABS source checkpoint

World Omni Auto Receivables Trust 2025-A đã tải trực tiếp bằng HTTP từ
issuer index: `abs-source-e67abf50bb2c`, 4 files / 2.156.553 bytes,
prospectus + 2025/2026 servicer XLS + index. Read-only legacy XLS inventory
`abs-inventory-57a286117455`: 20 collection periods Jan2025–Aug2026,
20.132 stored cells (8.993 populated,11.079 styled blank,60 empty text),
giữ type/format/provenance; counter `nonempty_cells` của inventory ban đầu
đã được sửa bằng receipt mới, giữ receipt cũ.
Canonical `abs-case-fcbaa9573ac3`:2.980 typed reported metrics,
40 source-blank D/E coupons NULL;1.155 checks/0 failed.
Independent `abs-audit-0065fd9be21c` PASS:0 raw-cell differences,
940 source SQL accounting checks/0 failed. 23 new targeted contract tests PASS.
Selected prospectus terms `abs-terms-4367aa1a54a3`:7issuedtranches,
626source-termchecks/0failed;ACT/360vs30/360,reportedSOFRspread/floor,
fundedprincipalallocation theo priority với A-2pro-rata,OC/reserve/reviewtrigger.
17new numerical/contract tests. Chưa loan-level ABS-EE, executedagreements/
amendmentevidence hoặc fullcontractual/projected waterfall. ABS evidence UI
đã có ở checkpoint mới dưới đây. Xem
[STRUCTURED_ABS_SOURCE_WORKFLOW.md](STRUCTURED_ABS_SOURCE_WORKFLOW.md).
Independent baseinterest `abs-interest-audit-2dc6b99f32f5`:140exact-rational
checksPASS,maxdifference0,00USD; no benchmarkfixing/carryover certification.
Conditional pre-acceleration waterfall `abs-waterfall-762205cf20db`:
20periods,220stage rows,720source comparisons/0failed;duevs paid,
fee cap,interest priorities/pro-rata,principal thresholds/sequential allocation,
reserve draws/replenishment,certificate cash/redelivery. Declared-scenario
maturity and terminal depositor-release branches supported; historical source
replay retains explicit gates for these branches. Independent SQL accounting
`abs-waterfall-audit-b0f4a1bcef60`:580checkrowsPASS.31newfocusedtests.
Reviewerfee obligations/legalstate/carryover/agreements remain assumptions or
unverified; no realizedloss/fullcontractual certification. See
[ABS_WATERFALL_WORKFLOW.md](ABS_WATERFALL_WORKFLOW.md).
ABS view `abs-view-1ea94d36115b`: period selector/payment dates,11 priorities,
7 issued-tranche allocations,36 source checks/kỳ, pool/notes chart, terms và
private exact period export. 15 focused API/view tests PASS. Browser receipt
`abs-browser-qa-287c96275587`: 12 checks PASS; desktop/mobile inspected.
Live port 8770 ABS period API HTTP200; qualification vẫn false.
[ABS_APP_WORKFLOW.md](ABS_APP_WORKFLOW.md).
Freddie Clarity và Ginnie production downloads require login; SEC Archives
XML HTTP403. Chưa có session, tiếp tục public issuer source thay vì hỏi lại cookies.

## Work still required — giữ nguyên full scope

Shared suite catalog, retail aggregate và SBA business UI/API/export đã
triển khai trên verified snapshot `suite-view-74e07524f6d0`; scope và commands ở
[SUITE_APP_AND_RETAIL_WORKFLOW.md](SUITE_APP_AND_RETAIL_WORKFLOW.md).
Business workflow chi tiết: [BUSINESS_APP_WORKFLOW.md](BUSINESS_APP_WORKFLOW.md).
Latest suite browser acceptance: `suite-browser-qa-f5d061d221cd`, 16 checks
PASS; standalone mortgage regression: `browser-qa-06f7e2d1aec0`, 24 checks PASS.
Không coi source catalog của P3–P5 là full domain application.

1. Additional source tracks: HMDA coverage ngoài pilot MD2023–2025 đã tải/canonical, FDIC institution history/consolidation
   và mở rộng financial credit-quality fields (42-quarter core panel đã có),
   More SEC issuers/raw filing/custom-tag/debt terms (four-issuer companyfacts/submissions đã có), one ABS-EE asset class, Ginnie pool/loan
   releases, sovereign default/event and publication-vintage series (World Bank country context đã có); authorized competition datasets when
   available. Clarity additional annual mortgage samples require login.
2. Tiếp tục bankruptcy findings/review
   (one-year development/freeze/one-time final/ledger/uncertainty/card và model-result API/UI/private export đã có) và SEC raw filing/custom-dimension/debt terms cùng business memo/model/readiness/finding workflows.
   SEC units/period adapter và filing-specific financial evidence UI/export đã có. Polish original
   ratio/horizon adapter và scoped explorer/export đã có. SBA UI/scoped export, dictionary,
   source-record grain, dates/money/status contracts đã có; không tạo loan/entity
   key hoặc universal default label khi source chưa hỗ trợ.
3. Complete the retail study: intended-use/subgroup review, economic policy,
   monitoring and full workflow integration. Canonical/features, three-model development
   fit, uncertainty, selection rubric, model freeze, reserved random holdout
   evaluation and research model card now exist; full P1 remains incomplete.
4. Credit memo/financial ratios, P4 institution-history/consolidation
   semantics (SBA marts và FDIC historical/custom-peer marts đã có);
   actual deal/waterfall calculations and benchmarks. Supported assumed
   fixed-coupon bond calculations đã có cùng independent 180-case audit;
   chưa security-calibrated và không thay actual collateral/deal system.
5. Integrate five workspace flows, case catalogs, aggregate APIs, private
   findings and exports. Browser must distinguish available, conditional and
   blocked capabilities. Complete all function/data/numerical/model acceptance
   requirements from the plan; current warehouse alone does not meet them.

P2 remains governed by its full R0–R4 plan. Additional workspaces do not turn
its unavailable model data into completion. The active suite goal remains open.

## Nội dung plan và app — checkpoint 10/10/2026

Đã bổ sung bản đồ 50 capability (10/domain), sáu trường mô tả/capability, client Markdown download và workflow deep links. Nội dung dùng chung nguồn editorial `scripts/build_workspace_content.py`; chi tiết trong PLAN_WORKBENCH_DETAIL.md. Hướng dẫn task/source hiện trước API lớn; Retail có model dossier bảy bước và metric interpretation từ saved snapshot. Không fit/chấm lại model. Roadmap vẫn phân biệt đã có/có điều kiện/một phần/cần dữ liệu.

Verification: `artifacts/private/content-detail-qa-37d04a4c18e0/receipt.json` 13 PASS; `artifacts/private/mvp-ux-qa-6b6c8d3bf49f/receipt.json` 13 PASS; `artifacts/private/content-http-20261010-final.xml` 15 PASS. Desktop/mobile inspected; no horizontal overflow at 390px; frozen holdout ledger unchanged. HTTP listener backlog increased to support concurrent same-origin banner/static requests; loopback/allowlist/privacy contracts retained.

## Enterprise credit monitor — 10/10/2026

App mặc định chuyển sang Risk monitor; catalog năm domain/hàng ảnh vẫn tại `?view=suite`. Monitor có năm native-scope KPI cards, mortgage D3 history (12/36/all, count/UPB), geographic concentration, Retail saved reliability, SBA program status composition, ABS reported runoff, feature availability và source-derived investigation queue. Filter/inspect/source/export và workflow actions giữ scope; không live feed, không fake borrower alerts, không rescore holdout.

Research mở rộng: ENTERPRISE_CREDIT_MONITOR_RESEARCH.md, 14 hãng (Oracle, Moody’s, S&P Global, Bloomberg, BlackRock, MSCI, SAS, FIS, Numerix, Experian, nCino, CreditRiskMonitor, Taktile, Regnology). OneSumX owner/2026 product update dùng thông báo Regnology; URL WK cũ không dùng để xác nhận current capability.

Verified receipts: `artifacts/private/monitor-qa-e2b68e7d703a/receipt.json` 10 PASS, including controlled P4 outage isolation; `artifacts/private/mvp-ux-qa-3c12ddc36ffc/receipt.json` 13 PASS; `artifacts/private/monitor-http-20261010.xml` 15 PASS. Desktop and 390px mobile inspected; holdout access ledger unchanged. UI release không hoàn thành các data/model/legal/production dependencies của 50-capability suite.
