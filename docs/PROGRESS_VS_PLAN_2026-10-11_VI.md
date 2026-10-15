# CreditAtlas — đối chiếu tiến độ với plan, 11/10/2026

Đối chiếu trực tiếp PLAN_WORKBENCH_DETAIL.md, PLAN_KPI_ANALYTICS_NEXT_VI.md, FIVE_WORKSPACES_STATUS.md và các receipt có trên đĩa. Đây là kiểm kê scope/trạng thái đã ghi nhận và evidence đã lưu; không phải lần chạy lại toàn bộ test/runtime ngày 11/10.

## 1. Phần trăm và cách tính

Plan chính gồm 50 capability, mỗi capability tính 1 đơn vị. Không có effort weighting đáng tin cậy trong plan nên không tạo một con số % khối lượng công việc hoặc % production readiness.

| Mức đo | Số mục | Tỷ lệ | Ý nghĩa |
|---|---:|---:|---|
| Đã có |21/50|42%|Workflow đã có trong scope nguồn mô tả; không mặc định qualified cho production|
| Đã có + Có điều kiện |30/50|60%|Có workflow hoàn chỉnh trong phạm vi nghiên cứu hoặc assumptions; 9 mục còn gates|
| Có triển khai ít nhất một phần |42/50|84%|21 đã có +9 có điều kiện +12 một phần; không phải completion rate|
| Một phần |12/50|24%|Có sub-workflow, chưa đóng phạm vi capability|
| Cần dữ liệu |8/50|16%|Capability chưa đủ đầu vào/qualification theo roadmap|

42% là tỷ lệ các mục mang trạng thái Đã có, KHÔNG là chứng nhận đã hoàn tất mọi acceptance criterion của toàn bộ dự án. 60%/84% là các mức coverage khác nhau, không cộng lại. Chưa đủ evidence để công bố một tỷ lệ triển khai thực tế tại ngân hàng.

## 2. Theo workspace

| Workspace | Đã có | Có điều kiện | Một phần | Cần dữ liệu | Đã có/10 | Có workflow gồm conditional/10 | Đã triển khai ít nhất một phần/10 |
|---|---:|---:|---:|---:|---:|---:|---:|
|P1 Retail|3|1|2|4|30%|40%|60%|
|P2 Mortgage|7|1|1|1|70%|80%|90%|
|P3 Business|6|0|3|1|60%|60%|90%|
|P4 Portfolio & observatory|5|4|1|0|50%|90%|100%|
|P5 Structured & market|0|3|5|2|0%|30%|80%|

## 3. Chi tiết 50 capability

### P1 — Retail

| ID / chức năng | Trạng thái | Đầu ra hiện tại/phạm vi đã ghi trong plan | Phần tiếp theo chưa đóng |
|---|---|---|---|
|P1.01 Dữ liệu & target|Đã có|Source profile, target card, split support và giới hạn population.|Thêm cohort theo thời gian và nguồn phù hợp thị trường muốn triển khai.|
|P1.02 Application underwriting|Cần dữ liệu|Application score, decision rationale, cutoff/capacity analysis và model card.|Thiết kế application schema và lấy nguồn có quyền truy cập trước khi fit.|
|P1.03 Behavioral model & validation|Đã có|AUC/AP/Brier/log loss, reliability bins, paired uncertainty và selected model.|Thêm cohort ngoài thời gian; kiểm tra calibration theo population triển khai.|
|P1.04 Decision policy|Có điều kiện|Action counts, expected declared cost, retrospective proxy, capacity overflow; preview/version/export.|Đo chi phí vận hành thật, daily inflow và reject outcomes trước policy production.|
|P1.05 Affordability|Cần dữ liệu|Affordability assessment và phần thiếu chứng từ.|Thêm intake income/cash-flow và debt-obligation schema.|
|P1.06 Limit & pricing|Cần dữ liệu|Scenario economics, break-even và constraints.|Thu thập contract economics và thiết kế policy experiments.|
|P1.07 Giải thích từng hồ sơ|Đã có|Global contribution distributions, token search/paging, signed local contributions và private export.|Kiểm tra reference sensitivity và qualification trước scoring hồ sơ mới.|
|P1.08 Collections workflow|Cần dữ liệu|Work queue, cure/recovery outcomes và treatment economics.|Thêm event-level collections data và analyst case ownership.|
|P1.09 Subgroup & monitoring|Một phần|Coverage, calibration/AUC/policy capture theo nhóm và exact export.|Thu thập monitoring cohorts theo thời gian và định nghĩa escalation thresholds.|
|P1.10 Model evidence & governance|Một phần|Model dossier, audit trail và reporting package; app đọc saved artifacts.|Thêm model-review ownership, monitoring protocol và intended-use approval ngoài benchmark.|

### P2 — Mortgage

| ID / chức năng | Trạng thái | Đầu ra hiện tại/phạm vi đã ghi trong plan | Phần tiếp theo chưa đóng |
|---|---|---|---|
|P2.01 Source & run explorer|Đã có|Source/run context, lineage và data readiness.|Thêm authorized annual vintages và reconcile từng acquisition.|
|P2.02 Panel quality|Đã có|Quality issues, affected counts, source investigation evidence.|Thêm cross-vintage quality checks và source reconciliation mới.|
|P2.03 Portfolio & cohorts|Đã có|Monthly charts, profile, selected-scope aggregate export.|Bổ sung nhiều origination vintages và standardize composition comparisons.|
|P2.04 Private loan lifecycle|Đã có|Timeline, observed UPB chart và source-backed event detail.|Thêm search/paging lớn hơn và review gắn loan khi contract được chốt.|
|P2.05 Transition matrix|Đã có|Matrix, selected-cell detail và year-scoped export.|Thêm temporal comparison và confidence intervals khi có đủ vintages.|
|P2.06 Cure & redefault|Đã có|Episode events, follow-up support và loan timeline.|Đánh giá time-to-cure/redefault trên nhiều cohorts với censoring protocol.|
|P2.07 Competing outcomes|Đã có|Cohort support, incidence/exits charts và target exclusions.|Thêm survival/competing-risk model khi temporal cohorts đạt gate.|
|P2.08 Horizon risk models|Cần dữ liệu|Prepared study, gate reasons; model metrics chỉ sau khi gate đạt.|Tải thêm authorized vintages và chốt R2–R3 trong PLAN_MODULE_01.|
|P2.09 Observed loss bridge|Có điều kiện|Loss components/coverage, reconciliation và selected-scope export.|Thêm recovery timing/contract data và mature loss cohorts.|
|P2.10 Evidence & review|Một phần|Private findings, review history và evidence reports.|Thêm identity/roles và formal review policy khi triển khai nhóm.|

### P3 — Business

| ID / chức năng | Trạng thái | Đầu ra hiện tại/phạm vi đã ghi trong plan | Phần tiếp theo chưa đóng |
|---|---|---|---|
|P3.01 SME source explorer|Đã có|Source dictionary, counts và quality evidence.|Thêm historical snapshots và documented loan key qualification.|
|P3.02 Financial normalization|Đã có|Field values/status, source units/periods và concept evidence.|Mở rộng issuer/taxonomy mapping và kiểm tra historical availability.|
|P3.03 Financial ratio analysis|Đã có|Ratio cards, actual/delta tables, numerator-first driver bridge với exact source inputs/counterfactual/effects/residual, baseline statements, Interest coverage tab với candidate evidence và private trend/coverage JSON và Analysis/Facts Excel với server-derived inputs/formulas/source evidence.|Thêm borrower debt-service/covenant inputs và peer/sector comparisons có consistent accounting scope.|
|P3.04 Bankruptcy benchmark|Đã có|Saved validation/holdout metrics, uncertainty và model card.|Thu thập identified dated statements cho deployed corporate-risk study.|
|P3.05 SBA outcomes & cohorts|Đã có|Status explorer, selected cohort/detail và decimal-preserving export.|Thêm longitudinal status dates/coverage trước survival or default modeling.|
|P3.06 Corporate credit memo|Một phần|Financial memo editor, issuer-scoped list, original evidence digest, atomic history và private full JSON export; Issuer filings tab với date/form/item filters, paging và source lineage.|Review full-text issuer filings/exhibits; bổ sung debt/covenant actual inputs. Metadata timeline đã có; không là confirmed credit events.|
|P3.07 Covenant workbench|Cần dữ liệu|Đã có Ford corporate revolving clause evidence/definition/minimum threshold từ acquired2026PDF; actual/headroom/compliance unavailable. Đích đầy đủ: headroom, supported breach assessment và supporting calculations.|Tạo covenant-term intake và source-backed adjustment ledger.|
|P3.08 Debt & cash-flow schedule|Một phần|Debt maturities tab, exact buckets/candidates/definitions, subtotal/total/first-three-years share, private JSON/Excel Maturities/Facts với23formulas; new memo capture. Facilities & covenant có10disclosed versions/5tranches, cutoff/effective selection, prior-date comparison và page/source-bound private JSON. Note cashflows có4Apple series, original-full-issue/no-redemption nominal schedule, calendar-year totals, source clauses và scoped JSON. Payment rules có5base-indenture clauses, issuer API discovery/feed linkage, pages/hashes và privateJSON; adjusted calendar dates chưa qualified.|Hoàn chỉnh amendment chain, dated utilization/outstanding principal, actual payment dates và interest/cash-flow inputs; qualify full debt-service/covenant actuals khi inputs available.|
|P3.09 Sector & concentration|Đã có|Sector/geography cohort tables và scoped exports.|Thêm comparable time snapshots và concentration uncertainty/support.|
|P3.10 Business review/export|Một phần|Private SEC/SBA reports, issuer financial memo store/history, private JSON và filter-scoped SEC Excel Analysis/Facts.|Thêm reviewer workflow/issuer events và scoped business handoff khi có inputs.|

### P4 — Portfolio & observatory

| ID / chức năng | Trạng thái | Đầu ra hiện tại/phạm vi đã ghi trong plan | Phần tiếp theo chưa đóng |
|---|---|---|---|
|P4.01 Typed exposure & Excel intake|Đã có|Verified import, input quality và private inventory.|Thêm column mapping theo source/facility và domain-specific Excel templates.|
|P4.02 Reconcile & concentration|Đã có|Overview KPIs, concentration rows/meters, bucket detail→review draft.|Thêm obligor/group identity và explicit FX policy nếu cần global totals.|
|P4.03 Research expected loss|Có điều kiện|Scenario EL/attribution và exact result exports.|Thêm calibrated probability/recovery evidence và documented economic exposure.|
|P4.04 ECL & staging|Có điều kiện|36-month event curves, stage/scenario comparisons, weighted research ECL và export.|Thu thập actual contract/EIR/risk evidence; review staging và recovery policy.|
|P4.05 Scenario & stress|Có điều kiện|Scenario comparisons, clipping counts, exact ordered EL attribution.|Estimate response functions từ suitable time data và validation protocol.|
|P4.06 Movement bridge|Đã có|Native-currency/bucket bridge, transitions và private exact export.|Thêm disposition reasons và better source linkage khi có evidence.|
|P4.07 Tail risk & concentration|Có điều kiện|VaR/ES, Monte Carlo uncertainty, concentration và convergence reports.|Thêm calibrated dependence, group linkage và production convergence thresholds.|
|P4.08 Bank observatory|Đã có|Bank metrics, peer/history charts, missingness và selected report export.|Thêm publication lags và stress linkage theo bank contracts.|
|P4.09 Country observatory|Đã có|Annual trend, same-year peers và source-qualified export.|Thêm debt/default/availability sources và documented macro stress linkage.|
|P4.10 Finance review package|Một phần|Review revisions, evidence freshness/expiry và finance workbook.|Thêm authenticated reviewer roles và formal review policy.|

### P5 — Structured & market

| ID / chức năng | Trạng thái | Đầu ra hiện tại/phạm vi đã ghi trong plan | Phần tiếp theo chưa đóng |
|---|---|---|---|
|P5.01 Deal & terms catalog|Một phần|Deal source context, tranche terms và unsupported legal scope.|Thu thập complete agreements, amendments và term extraction review.|
|P5.02 Collateral pool|Một phần|Pool/note trends, period metrics và source comparisons.|Thêm deal-specific asset IDs/schema và collateral-history adapter.|
|P5.03 Cash-flow projection|Cần dữ liệu|Forward pool cashflows và scenario assumptions.|Thiết kế collateral schedule intake và calibrate suitable behavior models.|
|P5.04 Sequential waterfall|Có điều kiện|Priority explorer, stage allocations, full ledger và period export.|Verify full legal regimes, prior obligations và amendments trước full contractual engine.|
|P5.05 Tranche & triggers|Có điều kiện|Tranche balances/payment detail và source checks.|Bổ sung verified trigger state/history và loss-allocation/legal regimes.|
|P5.06 Scenario valuation|Một phần|Assumed bond price/schedule/export; actual ABS valuation chưa hỗ trợ.|Thu thập instrument quotes và supported projected cashflows trước calibrated valuation.|
|P5.07 Bond sensitivity|Có điều kiện|Duration, convexity, bump residuals và bond scenario export.|Thêm trade/settlement dates, day-count/accrual và curve benchmark pricers.|
|P5.08 CDS credit curve|Cần dữ liệu|Credit curve, implied spreads và pricing residuals.|Lấy licensed term quotes và freeze pricing conventions/benchmark.|
|P5.09 Position & scenario comparison|Một phần|Market context, scenario outputs và independent scoped exports; chưa combined security-position book.|Thêm typed security-position mapping và supported instrument cashflow engines.|
|P5.10 Surveillance & numerical evidence|Một phần|Period check report, discrepancy support và conditional qualification.|Thêm fresh servicing periods, legal change detection và review ownership.|

## 4. Plan phân tích/KPI: 17 mục riêng, không cộng vào 50 mục

Các A/B/C là các lát cắt mở rộng, có overlap với 50 capability. Tính chúng riêng để tránh đếm hai lần. A1–A5 và B1–B6 đã triển khai trong scope:11/17 =64,7% về delivery coverage. C1–C6 chưa đạt đầy đủ:0/6 đóng toàn bộ gates. B1 đã bổ sung UCI retail acquisition profile nhưng còn missing profiles ở scope khác; B4–B6 đã kiểm tra native baseline sáu workbook và18ca input đại diện; SEC blank-to-zero đã sửa. Chưa full native/production qualification. Do đó64,7% không là tỷ lệ acceptance hoàn toàn.

| Mục | Đã triển khai / trạng thái | Còn thiếu / giới hạn |
|---|---|---|
|A1 Regional movement|Bridge P4 exact cents, tất cả vùng, đối soát tổng|Không suy nguyên nhân entries/exits từ grouped bridge|
|A2 Migration/cure readout|Lifetime transitions, confirmed events,12m follow-up|Không phải horizon PD/cure causal probability|
|A3 Policy economics|Saved validation case/cost/capacity/action support|Costs khai báo, chưa actual profit/production decision policy|
|A4 Issuer ratios|16 ratios/4 issuer; annual trend/driver/coverage|Borrower debt service, covenant terms, peer scope còn thiếu|
|A5 Structured cash bridge|Reported/conditional cash-reserve ledger và replay KPIs|Chưa complete contractual waterfall/forward projection|
|B1 Quality controls|22 controls; UCI retail raw missingness0/690000 cells và23feature/source tables|Whole-source parser completeness chưa semantic validity/OOT; một số profiles khác unavailable|
|B2 Comparable baseline|Auto đúng tháng lịch trước/manual/disable P2/P4/P5|Không tự dùng nearest period hoặc áp mọi KPI lifetime|
|B3 Analyst review|Captured KPI/source evidence, revisions/history/export|Self-declared review, chưa authenticated approval|
|B4 KPI Excel|110 KPI/control rows,4 sheets,delta formulas/cached audit|Actuals browser-derived; native baseline/KPI representative cases PASS, full qualification còn mở|
|B5 Corporate Excel|Analysis/Facts; source inputs/ratio/driver formulas|Native baseline/SEC missing-zero-prior cases PASS sau sửa source guard; full qualification còn mở|
|B6 Maturity Excel|Maturities/Facts;6 bucket,23formulas/source audit|Principal buckets chưa full debt-service; native baseline/zero-missing cases PASS|
|C1 Retail OOT|Chưa đủ later dated cohorts|Temporal validation/mature labels/intended-use|
|C2 Mortgage PD12|Chưa đủ authorized multi-vintage panel|Clarity access, temporal splits, model/calibration/OOT|
|C3 Qualified LGD|Observed-loss bridge có, qualification gate blocked|Recovery timing/components/discount/coverage|
|C4 DSCR/covenants|Một phần: coverage proxies và principal profiles|Facility interest/service schedule, actual legal thresholds|
|C5 Decision-grade EL/ECL|Conditional engines có|Actual positions + qualified PD/LGD/EAD/staging/EIR/governance|
|C6 Structured valuation|Historical replay + assumption bond study|Collateral forecasts/full legal waterfall/security curves/benchmark|

## 5. Cập nhật mới đã có evidence nghiệm thu

KPI inspector có88 KPI nghiệp vụ và22 quality controls; tìm/lọc, hồ sơ từng chỉ số, bảng dữ liệu/search/paging/CSV. Toàn bộ88 KPI đã map source/input references:61derived,26saved aggregates và1required-input EL. Source-pointer audit6groupsPASS; browser9groupsPASS; Excel regression110rowsPASS. Mapping không đồng nghĩa record-level recomputation của saved model metrics hay88actual/qualified metrics. Trong16SEC ratios,13supported và3unavailable tại snapshot.

Issuer filings đã tích hợp API/UI/private JSON, date/form/item filters, paging, reload và outage recovery. Backend29testsPASS; browser8groupsPASS, đối chiếu metadata bốn issuer. Item codes chỉ dùng discovery, chưa xác nhận default/breach hoặc thay full-text review. P3.06/P3.10 tiếp tục Một phần.

SEC refresh14API files đã verify105441facts,13374filing occurrences và67annual snapshots;201supported ratio checksPASS,0differing rows. SHA cả14files giống snapshot trước: không thêm observations mới. Bốn PDF Ford đã tải/extract/identity-check: term loan64pages, amendments2025 171pages, annual report212pages và amendments2026 333pages, tổng780pages. Facilities & covenant có10versions/5tranches, cutoff/effective selection, prior-boundary comparison, source pages và private JSON; backend facilities+events34testsPASS, browser5groupsPASS. Covenant clause/definition pages39/132 đã visual-review; actual liquidity/headroom, full amendment chain và debt-service chưa qualified. P3.07 vẫn Cần dữ liệu, P3.08 Một phần.

Apple8-K90pages đã acquired/identity-check; bốn note series có source-backed original-full-issue/no-redemption nominal cashflow schedule và calendar-year totals trong app/private JSON. Backend note+facilities36testsPASS; independent PDF/source/browser6groupsPASS. Actual balances/payments/business-day calendar/full issuer DSCR còn thiếu; P3.08/C4 vẫn Một phần.

Apple public issuer API đã dùng để discover/acquire S-3ASR/base-indenture bundle92pages. Payment rules tab có5clauses vàsource-feed/PDF/page lineage; backend rules+notes34PASS/browser6groupsPASS. Following vàno-delay-interest rules có evidence; series Place of Payment/overrides/calendar/current actuals chưa qualified.

Retail source quality bổ sung verified pre-freeze acquisition profile:30000clients/23predictors/690000cells,0parser-missing. API/UI/JSON/review capture và quality-scope Excel đã tích hợp; backend27testsPASS, browser6groupsPASS, five-domain inspector9groupsPASS và110-row Excel regressionPASS. Missingness không là semantic validity/final-test/OOT; ledger unchanged, counts50capabilities và88KPI/22controls giữ nguyên. Xem RETAIL_SOURCE_QUALITY_VI.md.

P5 SOFR benchmark: acquired443SOFRAI observations +SIFMA2025/2026/calendar/method evidence,5files925844bytes. New ABS SOFR nguồn tab/API/privateJSON compares20periods;20/20 rate/coupon precision matches and20/20 base-interest cents. Raw exact19/20SOFR and15/20coupon retained, binarycache deltas4–5e-18. Backend40PASS, independent rational20period auditPASS, browser6groupsPASS. Historical15:00publication vintage/conforming changes/unscheduled calendar/legal waterfall/valuation remain unverified; P5.05conditional/P5.10partial unchanged. See ABS_SOFR_BENCHMARK_VI.md.

Static pool history: acquired issuer index +StaticPool-WOART.xlsx +ManagedPool-Retail.xlsx,3files606781bytes. New P5 Static pool app/API/privateJSON projects21cohorts2021–2026 across delinquency/net-loss/ABSspeed;1998populated+1362blank positions, age12/24 comparisons and raw source cells. Backend26PASS; independent63cohort-metric groups/1998cells/1362blanksPASS; browser4groupsPASS after selector/mobile fixes. Managed aggregate adapter now separately projects7periods/210values/105checks/14raw ratios (MANAGED_POOL_ANALYTICS_VI.md);6legacy sheets not normalized; loan-level/forecast/LGD/historical availability remain unqualified. P5.02/P5.10partial unchanged. See STATIC_POOL_HISTORY_VI.md.

ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. See ABS_EE_MIRROR_COVERAGE_VI.md.

P4 acceptance checkpoint 11/10/2026: fixed exact XLSX significant-digit validation and allowlisted Excel POST error messages. Backend62PASS; independent import66checks/bridge500checksPASS; browser5groupsPASS including source/bucket→draft, exports, invalid numeric rejection, valid EXAMPLE intake/mobile. Full scope/ownership/native Excel/governance qualification remains open. See P4_ACCEPTANCE_AUDIT_VI.md.

Native Excel checkpoint: six workbooks9264cells/746formula cells baseline PASS;18representative input cases/59checks PASS. SEC missing-numerator blank-to-zero bug fixed in new exports; UI3groups/backend7PASS. Original source files and frozen holdout ledger unchanged. Native visual/full-feature qualification remains open. See NATIVE_EXCEL_VALIDATION_VI.md.

ABS-EE definition checkpoint: acquired official GovInfo2025CFR PDF/XML2files403351bytes. P5 field dictionary covers62observed mirror columns with proposed Item3correspondence,coverage and private export. Independent62PDF/XML definitions/coverage PASS,backend8PASS,browser5groups/coverage regression4groupsPASS. SEC specification ZIPHTTP403; XSD/original-filing XML/EX103/current-rule/labels/fidelity/model gates remain false. Counts unchanged. See ABS_EE_FIELD_DEFINITIONS_VI.md.

Sovereign checkpoint: app now serves BoC–BoE2023–2026 four official editions/12source files,42519entity-year rows/16selected metrics. Independent680304positions PASS,including1341raw markers/9954schema-absent IADB positions;59backend/HTTP/WDI tests PASS. Explicit2024TOTAL alias and2023country universe retained; all258World amounts match flat precision,68source count conflicts retained. Archive browser5groups/current regression9groups PASS; prior WDI regression10groups PASS. Original publication-byte availability/PD/LGD/macro stress/review qualification remain open. P4.09 evidence expanded;50capability states unchanged. See SOVEREIGN_ARCHIVE_EDITIONS_VI.md.

Utility DSCR/covenant checkpoint: EBMUD hai systems,20continuing records/260positions và60roundedACFR records/300positions,40DSCR checks independentPASS. API/UI/privateJSON có filters,bridges,source differences,history và legal evidence. Hai official statements2026 thêm590pages/22selected clause pages;reported1.1x covenant tách1.6xpolicy,proposed redline/default caveat và certificate/effective-date requirement giữ rõ. Independent legal auditPASS,36backend/HTTP checksPASS,browser5groupsPASS. Executed full indenture chain,historical applicability,certificate và adjusted test qualification chưa có;threshold/headroom/compliance null. P3.03/P3.07/P3.08/C4 chưa nâng completion state. Xem UTILITY_DEBT_SERVICE_VI.md và UTILITY_COVENANT_EVIDENCE_VI.md.

DSCR analytics checkpoint:32exact adjacent-year bridges và8missing-prior scopes;source USD input deltas,revenue/O&M/source residual/debt-service effects,counterfactual vàrational0/1residual trong API/UI/privateJSON. Five-year reported parity/total DSCR chart bổ sung. Independent40scope auditPASS,46backend/HTTP checksPASS,browser5groupsPASS. Accounting attribution order-dependent,không causal/legal qualification;50states unchanged. Xem UTILITY_DSCR_DRIVERS_VI.md.

## 6. Evidence kiểm tra trên đĩa

| Receipt | Kết quả đã lưu | Phạm vi |
|---|---|---|
|[p4-acceptance-qa-435791cbf240](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|P4 intake/precision/concentration/review draft/private exports/mobile|
|[absee-profile-qa-eee5f9a1c959](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Quarantined ABS-EE coverage UI/API/JSON/mobile/outage/ledger|
|[absee-profile-audit-00668467a11d](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Independent localParquet488219rows/651missingness/99money sums; not XML fidelity|
|[managed-pool-qa-bc2cc24261d2](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Managed stock/flow source/API/JSON/mobile/outage/ledger|
|[managed-pool-audit-8693d36cb33c](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Independent210values/105checks/14raw ratios|
|[kpi-analysis-qa-95251bc16b81](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|KPI/source/baseline regression|
|[kpi-workbook-qa-08a849344ada](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|KPI Excel|
|[sec-trends-qa-3cf29a711bdc](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Annual ratio trends/driver bridge|
|[sec-coverage-qa-1c32f79854e0](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Explicit interest coverage proxies|
|[sec-debt-qa-662fad1cb983](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Principal maturity source profile|
|[sec-workbook-qa-03d578d3b62d](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|SEC Analysis/Facts Excel|
|[sec-debt-xlsx-qa-de64508d62d6](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Maturity Excel|
|[corporate-memo-qa-2cf35018c3e3](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Memo immutable capture/history|
|[kpi-inspector-qa-9479d922c579](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Latest KPI inspector/input source/CSV/mobile|
|[kpi-trace-qa-6806b6dbe015](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|88 metric source/input trace audit|
|[sec-events-qa-a355fade2b6e](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Issuer filings metadata/browser/export|
|[facilities-qa-18dedf9f1512](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Versioned facility calendar/covenant clause/source/export|
|[note-schedule-qa-9827487edb65](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Source note terms/nominal cashflows/independent PDF/browser/export|
|[note-rules-qa-f5dd8158e6b9](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Issuer API-linked base payment rules/source/cutoff/browser/export|
|[retail-source-quality-qa-594921ea7ac8](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Acquisition profile/API/UI/JSON/Excel scope/mobile/outage/ledger|
|[kpi-inspector-qa-0b9964df5e79](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Five-domain inspector regression after source-quality integration|
|[abs-benchmark-qa-22780656071d](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Administrator SOFR/SIFMA calendar/UI/export/mobile/outage|
|[abs-benchmark-audit-a9d88282311d](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Independent20-period date/rational-rate/coupon/interest source comparison|
|[pool-history-qa-5930436fbc94](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Static-pool selectors/curve/source/export/reload/mobile/outage|
|[pool-history-audit-a38fbe7ce809](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)|PASS|Independent63cohort-metric groups/1998populated/1362blank source positions|

Receipt PASS không được dùng để chứng nhận phần ngoài phạm vi test: production governance, actual institution ECL, full legal terms, multi-vintage OOT, licensing hay toàn bộ native Excel qualification.

## 7. Thứ tự tiếp tục

1. Intake facility/debt-service/covenant terms có source/effective/test dates; đối chiếu amendments rồi qualify DSCR/headroom theo convention cụ thể.
2. Mở rộng authorized mortgage vintages và recovery inputs để đóng C2/C3; cohort mới cho C1.
3. Linked positions/risk parameters cho C5; collateral legal/forecast/curve inputs cho C6.
4. Đóng các missing profiles và full-record source trace nếu cần; metadata discovery chưa thay full-text issuer credit review.
5. Authenticated reviewer, mở rộng native Excel qualification và end-to-end reproduction/handoff.

Goal toàn bộ CreditAtlas tiếp tục active. Kiểm kê này không đánh dấu hoàn thành50capability hay toàn bộ R0–R4 của D01.
