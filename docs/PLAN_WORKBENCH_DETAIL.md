# CreditAtlas — plan chi tiết 50 chức năng và nội dung trong app

Ngày 10/10/2026. Tài liệu này mở rộng PLAN_FIVE_WORKSPACES.md; giữ toàn bộ data/model gates của kế hoạch gốc. Đây là roadmap và hướng dẫn phân tích, không chứng nhận 50 chức năng đã triển khai.

Nội dung được đồng bộ vào app từ scripts/build_workspace_content.py. Mỗi workspace có bản đồ 10 chức năng; chọn mục để đọc chi tiết hoặc mở màn đã có. Plan và app dùng chung nội dung nghiệp vụ.

Trạng thái: **Đã có** = workflow hiện chạy trong scope source nêu ở mục đó; **Có điều kiện** = nghiên cứu/assumptions hoặc supported regime; **Một phần** = đã có sub-workflow nhưng còn gap; **Cần dữ liệu** = chưa có đủ inputs/qualification. Các trạng thái là checkpoint ngày trên, không phải live health feed.

## Cách triển khai một chức năng

Chốt user question và data contract → acquisition/canonical reconciliation → phương pháp và source/target gates → màn inputs/results/evidence → private export/review → independent numerical/source audit → browser/mobile/scope checks. Đạt UI tests không thay data/model qualification.

## Luồng làm việc và thứ tự phát triển

**P1 — Retail:** đọc source/target → validation/model card → thử costs và thresholds trên validation → kiểm tra subgroup → giải thích từng hồ sơ → xuất evidence. Mở Model & evidence để xem split/model dossier; không dùng UCI behavioral history làm application-time underwriting. Ưu tiên tiếp: cohort ngoài thời gian, intended-use/subgroup review, economic inputs; affordability/limits/collections cần nguồn riêng.

**P2 — Mortgage:** xác minh run/source → monthly portfolio/cohorts → transitions/cure → lifecycle của một loan → competing exits → loss bridge → lưu finding. HMDA applications là nguồn khác Freddie performance. Ưu tiên thêm annual samples có quyền truy cập và đủ temporal holdout trước fit horizon models; loan-month splits không được làm rò cùng borrower.

**P3 — Business:** SBA status/cohort để khám phá lending records; SEC financial statements để đọc issuer facts; UCI bankruptcy để đánh giá benchmark riêng. Không join các nguồn này thành một borrower chỉ vì cùng sector. Ưu tiên normalized facts/ratio evidence rồi financial memo; covenant/debt schedules cần legal terms và cashflow inputs thực.

**P4 — Portfolio:** tải mẫu Excel → thay EXAMPLE bằng positions thật → import/reconcile → concentration → movement → scenario/ECL/tail assumptions → source-bound review → xuất workbook riêng tư theo currency. Reported balance không tự là EAD; source EL unavailable không tự thành zero. Ưu tiên linked positions/risk parameters và scenario/staging validation trước kết quả decision-grade.

**P5 — Structured:** đọc deal/terms → chọn reported period → pool history → replay waterfall → tranche balances → source checks → market/bond scenarios với assumptions tách riêng. Replay lịch sử không tự là forward pricing. Ưu tiên verified legal rules, triggers, collateral projections; CDS cần tenor quotes và độc lập pricing benchmark.

### Một đợt build cần bàn giao gì?

1. **Spec nghiệp vụ:** câu hỏi của analyst, population, grain, target/horizon, currency/date và quyền dữ liệu. Chọn một capability làm scope; ghi rõ dependencies còn thiếu.
2. **Data contract:** source manifests, schema/canonical mapping, reconciliation, missing/zero, lineage và quality exceptions. Lưu raw/canonical/snapshot có version; không ghi đè evidence cũ.
3. **Phương pháp:** công thức/conventions, benchmark, temporal/split rules nếu có model; độc lập audit numerical invariants. Không gọi exploratory hoặc assumption-only study là production validation.
4. **App:** inputs → kết quả → denominators/interpretation → evidence → review/export. Loading, empty, missing, stale và unsupported scopes phải có trạng thái rõ.
5. **Nghiệm thu:** data/model gates trước, rồi API/source parity, browser/mobile/navigation/export. Receipt lưu private; tests UI không thay source rights, OOT, legal qualification hoặc economic validation.
6. **Cập nhật plan:** ghi phần đã thực hiện và phần tiếp theo bằng scope cụ thể. Đồng bộ nội dung app bằng script builder; giữ cùng version/checkpoint để tra lại.

### Cách dùng nội dung mới trong app

Mở workspace → mở **Kế hoạch chi tiết 10 chức năng** → chọn capability. Sáu trường giải thích mục tiêu, inputs, phương pháp, outputs, nghiệm thu và next step. **Mở workflow liên quan** đưa đến phần đang có; không đồng nghĩa toàn bộ capability đã hoàn tất. **Tải kế hoạch (.md)** lưu bản từng domain. Trong task, mở **Hướng dẫn tác vụ** trước khi diễn giải kết quả thật bên dưới. Retail Model & evidence có thêm bảy bước nghiên cứu và giải thích metric.

## P1

### P1.01 — Dữ liệu & target

**Trạng thái:** Đã có.

**Mục tiêu:** Xác định mẫu khách hàng và sự kiện mà model thực sự học.

**Dữ liệu cần dùng:** UCI350: khách hàng thẻ Taiwan; bill/payment/status sáu tháng; target tháng kế tiếp.

**Phương pháp / thao tác:** Đối chiếu client và history; tách ID, target, predictors và trường demographic; đọc grain trước khi chia tập.

**Đầu ra:** Source profile, target card, split support và giới hạn population.

**Điều kiện nghiệm thu / cách đọc:** Client/history counts reconcile; source ID không là predictor; tháng và missing sentinels có nghĩa rõ.

**Bước phát triển tiếp theo:** Thêm cohort theo thời gian và nguồn phù hợp thị trường muốn triển khai.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=retail&workspace_tab=evidence)

### P1.02 — Application underwriting

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** Đánh giá hồ sơ tại thời điểm xin vay và đề xuất quyết định cấp tín dụng.

**Dữ liệu cần dùng:** Application-time income, bureau, requested amount, decision date; booked performance và reject population.

**Phương pháp / thao tác:** Chốt feature availability trước quyết định; định nghĩa target/horizon; tách thời gian và kiểm tra selection bias.

**Đầu ra:** Application score, decision rationale, cutoff/capacity analysis và model card.

**Điều kiện nghiệm thu / cách đọc:** Không dùng bill/status sau booking làm approval-time feature; có OOT và intended-use review.

**Bước phát triển tiếp theo:** Thiết kế application schema và lấy nguồn có quyền truy cập trước khi fit.

### P1.03 — Behavioral model & validation

**Trạng thái:** Đã có.

**Mục tiêu:** So sánh khả năng xếp hạng và xác suất của khách hàng thẻ đã có lịch sử.

**Dữ liệu cần dùng:** Train/calibration/validation/final-test client splits; history features; saved constant/logistic/boosting results.

**Phương pháp / thao tác:** Học encoder trên train; so sánh candidates trên validation; calibration riêng; freeze rồi đọc final test đã lưu.

**Đầu ra:** AUC/AP/Brier/log loss, reliability bins, paired uncertainty và selected model.

**Điều kiện nghiệm thu / cách đọc:** Không tune trên final test; random split được ghi rõ; bin rỗng không vẽ thành zero.

**Bước phát triển tiếp theo:** Thêm cohort ngoài thời gian; kiểm tra calibration theo population triển khai.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=retail&workspace_tab=validation)

### P1.04 — Decision policy

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Chuyển saved probability thành ba nhóm accept/review/decline dưới assumptions công khai.

**Dữ liệu cần dùng:** Validation scores; lower/upper thresholds; sáu action×outcome costs; review capacity.

**Phương pháp / thao tác:** Accept khi p<L; review khi L≤p<U; decline khi p≥U. Expected cost cộng (1-p)c0+pc1; giữ threshold ties.

**Đầu ra:** Action counts, expected declared cost, retrospective proxy, capacity overflow; preview/version/export.

**Điều kiện nghiệm thu / cách đọc:** Không tự reassignment khi vượt capacity; cost units không tự gọi là cash loss; validation comparisons là exploratory.

**Bước phát triển tiếp theo:** Đo chi phí vận hành thật, daily inflow và reject outcomes trước policy production.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=retail&workspace_tab=policy)

### P1.05 — Affordability

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** Kiểm tra khả năng trả nợ từ thu nhập và nghĩa vụ thanh toán.

**Dữ liệu cần dùng:** Verified income, recurring expenses, debt payments, household scope và loan schedule.

**Phương pháp / thao tác:** Chuẩn hóa kỳ thu nhập/chi phí; tính DTI hoặc residual income theo policy được xác nhận; chạy sensitivity.

**Đầu ra:** Affordability assessment và phần thiếu chứng từ.

**Điều kiện nghiệm thu / cách đọc:** Không suy income từ credit limit; DTI phải ghi denominator, kỳ và policy threshold.

**Bước phát triển tiếp theo:** Thêm intake income/cash-flow và debt-obligation schema.

### P1.06 — Limit & pricing

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** So sánh hạn mức/lãi suất theo economics và constraints.

**Dữ liệu cần dùng:** Contract rate/fees, PD horizon, LGD/EAD, funding/capital costs, take-up và affordability.

**Phương pháp / thao tác:** Lập profit/loss assumptions theo cùng horizon; thử limit/rate scenarios; tách risk và demand response.

**Đầu ra:** Scenario economics, break-even và constraints.

**Điều kiện nghiệm thu / cách đọc:** Không gọi price tối ưu khi thiếu cost/take-up evidence; không mượn PD khác target.

**Bước phát triển tiếp theo:** Thu thập contract economics và thiết kế policy experiments.

### P1.07 — Giải thích từng hồ sơ

**Trạng thái:** Đã có.

**Mục tiêu:** Đọc nhóm yếu tố làm saved probability cao/thấp hơn reference.

**Dữ liệu cần dùng:** Frozen model, training reference, bốn feature groups và toàn bộ4499 validation clients.

**Phương pháp / thao tác:** Grouped permutation đo performance reliance; finite-reference Shapley phân rã probability bằng16 coalitions.

**Đầu ra:** Global contribution distributions, token search/paging, signed local contributions và private export.

**Điều kiện nghiệm thu / cách đọc:** Contributions cộng về prediction đúng tolerance; references/source pinned; không gọi là nguyên nhân hoặc adverse-action reason.

**Bước phát triển tiếp theo:** Kiểm tra reference sensitivity và qualification trước scoring hồ sơ mới.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=retail&workspace_tab=explanations)

### P1.08 — Collections workflow

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** Ưu tiên can thiệp và theo dõi hiệu quả thu hồi.

**Dữ liệu cần dùng:** Delinquency/contact/actions/promises/payments, treatment timestamps và costs.

**Phương pháp / thao tác:** Chốt eligible population; so sánh treatments với control hoặc thiết kế causal evaluation; quản lý case history.

**Đầu ra:** Work queue, cure/recovery outcomes và treatment economics.

**Điều kiện nghiệm thu / cách đọc:** Behavioral score không chứng minh uplift; không tạo SLA/contact events giả.

**Bước phát triển tiếp theo:** Thêm event-level collections data và analyst case ownership.

### P1.09 — Subgroup & monitoring

**Trạng thái:** Một phần.

**Mục tiêu:** Kiểm tra support và kết quả theo nhóm trước khi kết luận về model/policy.

**Dữ liệu cần dùng:** Validation demographics, predictions, labels; source-bound subgroup study.

**Phương pháp / thao tác:** Nhóm theo SEX/EDUCATION/MARRIAGE/declared age bands; giữ counts; metrics unavailable nếu thiếu class support.

**Đầu ra:** Coverage, calibration/AUC/policy capture theo nhóm và exact export.

**Điều kiện nghiệm thu / cách đọc:** Bỏ demographic predictors không chứng minh fairness; small groups không được gán ranking metrics; chưa có temporal drift.

**Bước phát triển tiếp theo:** Thu thập monitoring cohorts theo thời gian và định nghĩa escalation thresholds.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=retail&workspace_tab=policy)

### P1.10 — Model evidence & governance

**Trạng thái:** Một phần.

**Mục tiêu:** Giúp người review biết model dùng để làm gì, đã chọn ra sao và còn thiếu bằng chứng nào.

**Dữ liệu cần dùng:** Source contract, split support, saved model selection/holdout, uncertainty và limitations.

**Phương pháp / thao tác:** Đọc target→availability→train/calibration→validation selection→freeze→saved final test; ghi assumption và intended use.

**Đầu ra:** Model dossier, audit trail và reporting package; app đọc saved artifacts.

**Điều kiện nghiệm thu / cách đọc:** Không refit/rescore khi mở màn; benchmark Taiwan không trở thành Vietnam PD; chưa có authenticated sign-off.

**Bước phát triển tiếp theo:** Thêm model-review ownership, monitoring protocol và intended-use approval ngoài benchmark.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=retail&workspace_tab=evidence)

## P2

### P2.01 — Source & run explorer

**Trạng thái:** Đã có.

**Mục tiêu:** Chọn đúng sample, reporting period và frozen run trước phân tích.

**Dữ liệu cần dùng:** Freddie annual sample2012, raw receipt và run lineage.

**Phương pháp / thao tác:** Đọc source years, release, coverage và rebuild evidence; giữ sample scope trong exports.

**Đầu ra:** Source/run context, lineage và data readiness.

**Điều kiện nghiệm thu / cách đọc:** Không gọi sample50k là toàn thị trường; không thay extraction time bằng publication time.

**Bước phát triển tiếp theo:** Thêm authorized annual vintages và reconcile từng acquisition.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sources)

### P2.02 — Panel quality

**Trạng thái:** Đã có.

**Mục tiêu:** Xác định reporting gaps và lỗi linkage trước khi dùng diễn biến khoản vay.

**Dữ liệu cần dùng:** Origination/performance panel, keys/months, sentinels và quality findings.

**Phương pháp / thao tác:** Kiểm tra uniqueness, adjacent months, missing states, terminal contradictions và source dimensions.

**Đầu ra:** Quality issues, affected counts, source investigation evidence.

**Điều kiện nghiệm thu / cách đọc:** Unknown/gap không trở thành current; không nối qua khoảng thiếu dữ liệu.

**Bước phát triển tiếp theo:** Thêm cross-vintage quality checks và source reconciliation mới.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sources)

### P2.03 — Portfolio & cohorts

**Trạng thái:** Đã có.

**Mục tiêu:** Xem quy mô, trạng thái và cơ cấu loan book theo tháng.

**Dữ liệu cần dùng:** Observed loan-month states/UPB; segment, reporting-month filters và vintage labels.

**Phương pháp / thao tác:** Đếm loans và số dư riêng; chọn kỳ, segment và count/balance basis; đọc cohort support trước so sánh.

**Đầu ra:** Monthly charts, profile, selected-scope aggregate export.

**Điều kiện nghiệm thu / cách đọc:** Zero UPB giữ riêng; count và balance có denominator khác; không cộng duplicate loan-months thành unique loans.

**Bước phát triển tiếp theo:** Bổ sung nhiều origination vintages và standardize composition comparisons.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=portfolio)

### P2.04 — Private loan lifecycle

**Trạng thái:** Đã có.

**Mục tiêu:** Đọc reporting path của một khoản vay để kiểm tra kết luận aggregate.

**Dữ liệu cần dùng:** Run-scoped pseudonymous loan key, observed states/UPB và confirmed events.

**Phương pháp / thao tác:** Lọc outcome hoặc prefix; chọn loan; xem monthly path và confirmation dates; giữ gaps.

**Đầu ra:** Timeline, observed UPB chart và source-backed event detail.

**Điều kiện nghiệm thu / cách đọc:** Không lộ raw loan ID; không coi observed timeline là forecast; không backdate confirmation.

**Bước phát triển tiếp theo:** Thêm search/paging lớn hơn và review gắn loan khi contract được chốt.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=lifecycle)

### P2.05 — Transition matrix

**Trạng thái:** Đã có.

**Mục tiêu:** Đo di chuyển giữa delinquency states trong adjacent reporting periods.

**Dữ liệu cần dùng:** Adjacent loan-month pairs; opening UPB; selected reporting year/segment.

**Phương pháp / thao tác:** Count hoặc opening-balance weights; chia cho origin denominator; bấm cell đọc pair/loan support.

**Đầu ra:** Matrix, selected-cell detail và year-scoped export.

**Điều kiện nghiệm thu / cách đọc:** Không nối gaps/terminal pairs sai; năm không có pairs giữ unavailable; lifetime comparator ghi rõ scope.

**Bước phát triển tiếp theo:** Thêm temporal comparison và confidence intervals khi có đủ vintages.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=transitions)

### P2.06 — Cure & redefault

**Trạng thái:** Đã có.

**Mục tiêu:** Phân biệt current một tháng, sustained cure và tái delinquency.

**Dữ liệu cần dùng:** D3 episodes, CURRENT nonterminal consecutive months, gaps và follow-up windows.

**Phương pháp / thao tác:** Sustained cure xác nhận ở tháng CURRENT thứ ba liên tiếp sauD3; redefault sau cure là event riêng.

**Đầu ra:** Episode events, follow-up support và loan timeline.

**Điều kiện nghiệm thu / cách đọc:** Gap/unknown phá linkage; terminal CURRENT không thành cure; follow-up thiếu không thành no-event.

**Bước phát triển tiếp theo:** Đánh giá time-to-cure/redefault trên nhiều cohorts với censoring protocol.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=transitions)

### P2.07 — Competing outcomes

**Trạng thái:** Đã có.

**Mục tiêu:** Đọc D3, prepayment/maturity và other exits trong cùng estimand.

**Dữ liệu cần dùng:** Early-entry eligible loans, horizon6/12/24m, endpoint observations và censoring.

**Phương pháp / thao tác:** Giữ eligibility/available labels; đọc competing incidence theo segment/horizon; không cộng independent classifier probabilities.

**Đầu ra:** Cohort support, incidence/exits charts và target exclusions.

**Điều kiện nghiệm thu / cách đọc:** Không gọi horizon connector là monthly prediction; censored/unknown không thành negative.

**Bước phát triển tiếp theo:** Thêm survival/competing-risk model khi temporal cohorts đạt gate.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=vintage)

### P2.08 — Horizon risk models

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** Fit và kiểm định forecast delinquency đúng horizon/feature availability.

**Dữ liệu cần dùng:** Nhiều origination vintages, macro availability, frozen temporal splits và final OOT.

**Phương pháp / thao tác:** Audit feature time; fit train-only; calibration; lựa chọn trên development; giữ final OOT riêng.

**Đầu ra:** Prepared study, gate reasons; model metrics chỉ sau khi gate đạt.

**Điều kiện nghiệm thu / cách đọc:** Một vintage2012 chưa đủ temporal evaluation; readiness screen không là qualified score.

**Bước phát triển tiếp theo:** Tải thêm authorized vintages và chốt R2–R3 trong PLAN_MODULE_01.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=models)

### P2.09 — Observed loss bridge

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Đọc các thành phần realized/source-reported loss với đúng units và coverage.

**Dữ liệu cần dùng:** Source loss/recovery/cost fields, observation periods và terminal information.

**Phương pháp / thao tác:** Reconcile components; giữ missing và sign conventions; tách observed loss khỏi PD×LGD×EAD assumptions.

**Đầu ra:** Loss components/coverage, reconciliation và selected-scope export.

**Điều kiện nghiệm thu / cách đọc:** Không fill missing bằng zero; sample không representative LGD calibration; UPB không tự là economic loss.

**Bước phát triển tiếp theo:** Thêm recovery timing/contract data và mature loss cohorts.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=loss)

### P2.10 — Evidence & review

**Trạng thái:** Một phần.

**Mục tiêu:** Lưu nhận định có scope, lineage và history để người khác đối chiếu.

**Dữ liệu cần dùng:** Current run/view/filters, quality/target/numerical evidence và reviewer text.

**Phương pháp / thao tác:** Lưu draft; sửa bằng revision; reopen/history/export; report giữ source/run/filter binding.

**Đầu ra:** Private findings, review history và evidence reports.

**Điều kiện nghiệm thu / cách đọc:** Không sửa source bằng memo; reviewed không là authenticated bank approval.

**Bước phát triển tiếp theo:** Thêm identity/roles và formal review policy khi triển khai nhóm.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=evidence)

## P3

### P3.01 — SME source explorer

**Trạng thái:** Đã có.

**Mục tiêu:** Hiểu booked-program grain và nghĩa các field SBA.

**Dữ liệu cần dùng:** Sáu SBA FOIA files, dictionary, program/status/date fields.

**Phương pháp / thao tác:** Reconcile segments; đọc definitions; phân biệt records, source loans và borrower identities.

**Đầu ra:** Source dictionary, counts và quality evidence.

**Điều kiện nghiệm thu / cách đọc:** Không cộng files thành unique borrowers nếu chưa có identity; giữ EXEMPT/unknown/cancelled.

**Bước phát triển tiếp theo:** Thêm historical snapshots và documented loan key qualification.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=business&workspace_tab=dictionary)

### P3.02 — Financial normalization

**Trạng thái:** Đã có.

**Mục tiêu:** Chuyển SEC facts thành annual financial fields có bằng chứng filing cụ thể.

**Dữ liệu cần dùng:** Companyfacts/submissions, concepts/units/start/end/accession/filing date.

**Phương pháp / thao tác:** Chọn issuer/cutoff/annual filing; screen duration330–400days; giữ competing candidates và custom-tag gaps.

**Đầu ra:** Field values/status, source units/periods và concept evidence.

**Điều kiện nghiệm thu / cách đọc:** Không ghép quarterly/YTD thành annual theo fiscal-year label; conflicts không chọn alias đẹp hơn.

**Bước phát triển tiếp theo:** Mở rộng issuer/taxonomy mapping và kiểm tra historical availability.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sec&workspace_tab=statements)

### P3.03 — Financial ratio analysis

**Trạng thái:** Đã có.

**Mục tiêu:** Đọc liquidity, leverage, profitability và interest-coverage proxies qua các annual report periods của cùng issuer.

**Dữ liệu cần dùng:** Normalized SEC fields/filings, explicit expense concept, exact units/durations và original 10-K selection.

**Phương pháp / thao tác:** Chọn3/5/10 report periods; so adjacent annual periods330–400days khi supported same-concept inputs; relative delta cần positive baseline. Coverage dùng expense concept được chọn, same annual period và positive denominator; giữ negative numerator.

**Đầu ra:** Ratio cards, actual/delta tables, numerator-first driver bridge với exact source inputs/counterfactual/effects/residual, baseline statements, Interest coverage tab với candidate evidence và private trend/coverage JSON và Analysis/Facts Excel với server-derived inputs/formulas/source evidence.

**Điều kiện nghiệm thu / cách đọc:** Amendments giữ riêng; không skip gaps/concept changes; không đổi cash interest thành expense; operating-income/OCF proxies chưa là EBIT ICR, DSCR hoặc covenant.

**Bước phát triển tiếp theo:** Thêm borrower debt-service/covenant inputs và peer/sector comparisons có consistent accounting scope.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sec&workspace_tab=trends)

### P3.04 — Bankruptcy benchmark

**Trạng thái:** Đã có.

**Mục tiêu:** So sánh historical financial-statement classifiers trên source target một năm.

**Dữ liệu cần dùng:** UCI365 original ARFF; subset5 one-year label; frozen splits/model/calibration.

**Phương pháp / thao tác:** Train-only preprocessing; select candidate trên validation; freeze boosting/Platt; đọc saved591 final statements.

**Đầu ra:** Saved validation/holdout metrics, uncertainty và model card.

**Điều kiện nghiệm thu / cách đọc:** Không pool five horizons thành một PD; thiếu firm IDs/publication dates nên chưa entity-disjoint/OOT.

**Bước phát triển tiếp theo:** Thu thập identified dated statements cho deployed corporate-risk study.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=bankruptcymodel)

### P3.05 — SBA outcomes & cohorts

**Trạng thái:** Đã có.

**Mục tiêu:** Mô tả status/approval/charge-off theo program và cohorts.

**Dữ liệu cần dùng:** Program,status,approval fiscal year,NAICS/geography và reported amounts.

**Phương pháp / thao tác:** Chọn program/dimension/bucket; đọc count và amount scope; tách paid/charged-off/withheld/cancelled/undisbursed.

**Đầu ra:** Status explorer, selected cohort/detail và decimal-preserving export.

**Điều kiện nghiệm thu / cách đọc:** Terminal snapshot không là fixed-horizon PD; post-outcome fields không làm approval predictors.

**Bước phát triển tiếp theo:** Thêm longitudinal status dates/coverage trước survival or default modeling.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=business&workspace_tab=cohorts)

### P3.06 — Corporate credit memo

**Trạng thái:** Một phần.

**Mục tiêu:** Tập hợp financial facts và analyst rationale theo đúng issuer/filing.

**Dữ liệu cần dùng:** Verified SEC filing facts/annual trend và submissions/history filing timeline; full-text event/debt/covenant inputs còn cần bổ sung.

**Phương pháp / thao tác:** Tạo9 narrative sections; server capture selected filing và history anchored tại filing date; revise narrative với optimistic revision; evidence immutable.

**Đầu ra:** Financial memo editor, issuer-scoped list, original evidence digest, atomic history và private full JSON export; Issuer filings tab với date/form/item filters, paging và source lineage.

**Điều kiện nghiệm thu / cách đọc:** Reviewed là self-declared analyst status; không issuer PD hoặc credit approval; thiếu source mới không ghi đè capture cũ.

**Bước phát triển tiếp theo:** Review full-text issuer filings/exhibits; bổ sung debt/covenant actual inputs. Metadata timeline đã có; không là confirmed credit events.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sec&workspace_tab=memo)

### P3.07 — Covenant workbench

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** Theo dõi điều khoản tài chính của facility theo hợp đồng.

**Dữ liệu cần dùng:** Signed facility/covenant terms, definitions, test dates và permitted adjustments.

**Phương pháp / thao tác:** Tính independent covenant ratios; reconcile adjustments; so threshold đúng kỳ/contract.

**Đầu ra:** Đã có Ford corporate revolving clause evidence/definition/minimum threshold từ acquired2026PDF; actual/headroom/compliance unavailable. Đích đầy đủ: headroom, supported breach assessment và supporting calculations.

**Điều kiện nghiệm thu / cách đọc:** Thiếu terms thì không gắn actual breach badge; SEC generic ratios không thay contract definitions.

**Bước phát triển tiếp theo:** Tạo covenant-term intake và source-backed adjustment ledger.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sec&workspace_tab=facilities)

### P3.08 — Debt & cash-flow schedule

**Trạng thái:** Một phần.

**Mục tiêu:** Đọc principal maturity profile, versioned facility calendar và dependencies cho full debt-service.

**Dữ liệu cần dùng:** Verified SEC selected-filing instant facts; acquired Ford facility versions và Apple2025fixed-note terms. Full utilization/calendar/cashflows vẫn cần qualification.

**Phương pháp / thao tác:** Match exact CIK/accession/filing date/end/USD; giữ6 fiscal-year buckets; total/share chỉ khi complete nonnegative; không fallback missing/ambiguous.

**Đầu ra:** Debt maturities tab, exact buckets/candidates/definitions, subtotal/total/first-three-years share, private JSON/Excel Maturities/Facts với23formulas; new memo capture. Facilities & covenant có10disclosed versions/5tranches, cutoff/effective selection, prior-date comparison và page/source-bound private JSON. Note cashflows có4Apple series, original-full-issue/no-redemption nominal schedule, calendar-year totals, source clauses và scoped JSON. Payment rules có5base-indenture clauses, issuer API discovery/feed linkage, pages/hashes và privateJSON; adjusted calendar dates chưa qualified.

**Điều kiện nghiệm thu / cách đọc:** Principal buckets không là exact payment dates, carrying debt, EAD hoặc DSCR; after-year-five open ended; debt/lease families không cộng overlap.

**Bước phát triển tiếp theo:** Hoàn chỉnh amendment chain, dated utilization/outstanding principal, actual payment dates và interest/cash-flow inputs; qualify full debt-service/covenant actuals khi inputs available.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sec&workspace_tab=debt)

### P3.09 — Sector & concentration

**Trạng thái:** Đã có.

**Mục tiêu:** Xác định source-program concentration theo ngành/vùng.

**Dữ liệu cần dùng:** SBA NAICS/geography/program/status aggregate marts và denominators.

**Phương pháp / thao tác:** Chọn dimension/bucket; so records/amounts trong cùng program/source grain; giữ unknown sector.

**Đầu ra:** Sector/geography cohort tables và scoped exports.

**Điều kiện nghiệm thu / cách đọc:** Booked SBA program không đại diện toàn bộ SME economy; approval amount không tự là EAD.

**Bước phát triển tiếp theo:** Thêm comparable time snapshots và concentration uncertainty/support.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=business&workspace_tab=cohorts)

### P3.10 — Business review/export

**Trạng thái:** Một phần.

**Mục tiêu:** Đóng gói financial/outcome evidence theo issuer hoặc program scope.

**Dữ liệu cần dùng:** Selected SEC filing/cutoff hoặc SBA program/dimension/bucket, source quality.

**Phương pháp / thao tác:** Export source projection; financial memo giữ owner/identity/date/evidence digest qua revisions; SBA nguồn riêng.

**Đầu ra:** Private SEC/SBA reports, issuer financial memo store/history, private JSON và filter-scoped SEC Excel Analysis/Facts.

**Điều kiện nghiệm thu / cách đọc:** Không fuzzy-match SBA name với SEC để tạo labels; không trộn reporting grains; owner chưa authenticated.

**Bước phát triển tiếp theo:** Thêm reviewer workflow/issuer events và scoped business handoff khi có inputs.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=sec&workspace_tab=memo)

## P4

### P4.01 — Typed exposure & Excel intake

**Trạng thái:** Đã có.

**Mục tiêu:** Nhập portfolio có currency/units/date/risk semantics rõ.

**Dữ liệu cần dùng:** InputPositions/InputControl XLSX; position/pool/representation/as-of/currency/amount và optional risk contract.

**Phương pháp / thao tác:** Giữ13 headers; validate units/date/IDs; values-only intake; lưu workbook lineage và tạo import riêng.

**Đầu ra:** Verified import, input quality và private inventory.

**Điều kiện nghiệm thu / cách đọc:** File≤20MB/50000positions; formula inputs/unsafe numeric precision bị reject; missing risk không thành zero.

**Bước phát triển tiếp theo:** Thêm column mapping theo source/facility và domain-specific Excel templates.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=excel)

### P4.02 — Reconcile & concentration

**Trạng thái:** Đã có.

**Mục tiêu:** Xem balances/record support và vùng tập trung trong cùng currency.

**Dữ liệu cần dùng:** Verified imported amounts, region/segment/source_state/representation.

**Phương pháp / thao tác:** Reconcile native-currency sums/zero balances; share=amount bucket/tổng currency; search/sort/select detail.

**Đầu ra:** Overview KPIs, concentration rows/meters, bucket detail→review draft.

**Điều kiện nghiệm thu / cách đọc:** Không cộng cross-currency; source observations không tự là borrower concentration; reported amount khác EAD.

**Bước phát triển tiếp theo:** Thêm obligor/group identity và explicit FX policy nếu cần global totals.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=overview)

### P4.03 — Research expected loss

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Tính expected loss theo declared probability và exposure contract.

**Dữ liệu cần dùng:** PD horizon/target/measure, LGD, EAD và scenario eligibility.

**Phương pháp / thao tác:** Factorized EL=PD×LGD×EAD; reconcile eligible/excluded; giữ source EL riêng với illustrative scenario EL.

**Đầu ra:** Scenario EL/attribution và exact result exports.

**Điều kiện nghiệm thu / cách đọc:** Không mượn PD khác target; actual source import vẫn EL unavailable nếu không có risk inputs.

**Bước phát triển tiếp theo:** Thêm calibrated probability/recovery evidence và documented economic exposure.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=scenarios)

### P4.04 — ECL & staging

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Đọc timing của expected cash shortfall và declared stage assessment.

**Dữ liệu cần dùng:** Hazard/default curves, schedules/EIR assumptions, SICR/default policy, recoveries/cost/lag/scenario weights.

**Phương pháp / thao tác:** Chuyển conditional hazard thành marginal default mass; tính discounted shortfall theo thời điểm; stage1 cutoff default events, giữ recovery tail.

**Đầu ra:** 36-month event curves, stage/scenario comparisons, weighted research ECL và export.

**Điều kiện nghiệm thu / cách đọc:** Bullet/EIR/recovery terms hiện minh họa; stage3/POCI/revolving policies không mặc định supported; chưa accounting compliance.

**Bước phát triển tiếp theo:** Thu thập actual contract/EIR/risk evidence; review staging và recovery policy.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=ecl)

### P4.05 — Scenario & stress

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Đọc độ nhạy PD/LGD/EAD và biết yếu tố nào làm EL thay đổi.

**Dữ liệu cần dùng:** Versioned odds/LGD addition/EAD factor assumptions và selected eligible segment.

**Phương pháp / thao tác:** PD odds transform; clip LGD tại boundaries; ordered attribution với residual; giữ scenario inputs trong version.

**Đầu ra:** Scenario comparisons, clipping counts, exact ordered EL attribution.

**Điều kiện nghiệm thu / cách đọc:** Không gọi macro-calibrated stress khi chỉ có assumptions; excluded positions không bị gán zero loss.

**Bước phát triển tiếp theo:** Estimate response functions từ suitable time data và validation protocol.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=scenarios)

### P4.06 — Movement bridge

**Trạng thái:** Đã có.

**Mục tiêu:** Giải thích số dư thay đổi giữa hai typed snapshots.

**Dữ liệu cần dùng:** Same-source namespace position keys, currency, opening/closing amount và buckets.

**Phương pháp / thao tác:** Remove missing/currency-out→continuing change→bucket transfers→add new/currency-in→residual.

**Đầu ra:** Native-currency/bucket bridge, transitions và private exact export.

**Điều kiện nghiệm thu / cách đọc:** Missing record không là default/payoff; currency migration không là FX P&L; residual phải giữ rõ.

**Bước phát triển tiếp theo:** Thêm disposition reasons và better source linkage khi có evidence.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=movement)

### P4.07 — Tail risk & concentration

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Đọc tổn thất đuôi dưới dependence/recovery assumptions.

**Dữ liệu cần dùng:** Eligible position EAD, declared PD/LGD, latent-factor rho, systemic LGD spread, seed/draws.

**Phương pháp / thao tác:** Seeded position loss simulation; empirical VaR; ES đúng tail mass với ties; segment contribution trong cùng joint tail; multi-seed diagnostics.

**Đầu ra:** VaR/ES, Monte Carlo uncertainty, concentration và convergence reports.

**Điều kiện nghiệm thu / cách đọc:** Correlation/recovery chưa calibrated; thiếu obligor linkage; finite tails/CI unavailable giữ đúng; chưa capital approval.

**Bước phát triển tiếp theo:** Thêm calibrated dependence, group linkage và production convergence thresholds.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=tail)

### P4.08 — Bank observatory

**Trạng thái:** Đã có.

**Mục tiêu:** Đọc tình hình institution-quarter và peer context của ngân hàng.

**Dữ liệu cần dùng:** FDIC CERT×REPDTE financials, failures, metric definitions và reporting units.

**Phương pháp / thao tác:** Chọn quý/universe/bank; compare same-quarter peers; adjacent quarter changes; kiểm tra publication scope.

**Đầu ra:** Bank metrics, peer/history charts, missingness và selected report export.

**Điều kiện nghiệm thu / cách đọc:** USD thousand giữ đúng; institution event không là borrower default; reporting date không tự là availability date.

**Bước phát triển tiếp theo:** Thêm publication lags và stress linkage theo bank contracts.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=bank)

### P4.09 — Country observatory

**Trạng thái:** Đã có.

**Mục tiêu:** Đọc annual macro/sovereign context theo quốc gia và indicator.

**Dữ liệu cần dùng:** World Bank country/year series, units, regional/aggregate definitions và current classifications.

**Phương pháp / thao tác:** Chọn country/indicator/year/range; compare same-year values; giữ missing và overlapping aggregates.

**Đầu ra:** Annual trend, same-year peers và source-qualified export.

**Điều kiện nghiệm thu / cách đọc:** Không thay missing bằng latest; ratio không cộng thành tổng; current region/income labels không historical classification.

**Bước phát triển tiếp theo:** Thêm debt/default/availability sources và documented macro stress linkage.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=country)

### P4.10 — Finance review package

**Trạng thái:** Một phần.

**Mục tiêu:** Lưu rationale và study versions để analyst đối chiếu lại quyết định nghiên cứu.

**Dữ liệu cần dùng:** Source import/currency, scenario/ECL/tail evidence, owner/expiry/status/acknowledgment.

**Phương pháp / thao tác:** Create draft→revision→review/history; pin evidence refs; export review và six-sheet Excel report.

**Đầu ra:** Review revisions, evidence freshness/expiry và finance workbook.

**Điều kiện nghiệm thu / cách đọc:** Reviewed không là human-authenticated sign-off; Excel notes không ghi ngược app; source values không bị sửa bởi memo.

**Bước phát triển tiếp theo:** Thêm authenticated reviewer roles và formal review policy.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=exposure&workspace_tab=review)

## P5

### P5.01 — Deal & terms catalog

**Trạng thái:** Một phần.

**Mục tiêu:** Hiểu deal, collateral, issued tranches và terms đã hỗ trợ.

**Dữ liệu cần dùng:** World Omni2025-A prospectus, servicing certificates và selected prospectus terms.

**Phương pháp / thao tác:** Đọc issuer/deal/currency/payment conventions; đối chiếu terms và qualification trước replay.

**Đầu ra:** Deal source context, tranche terms và unsupported legal scope.

**Điều kiện nghiệm thu / cách đọc:** Chưa xác minh đầy đủ agreements/amendments/legal state; terms không mặc định full contractual waterfall.

**Bước phát triển tiếp theo:** Thu thập complete agreements, amendments và term extraction review.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=abs&workspace_tab=evidence)

### P5.02 — Collateral pool

**Trạng thái:** Một phần.

**Mục tiêu:** Đọc actual reported pool thay đổi theo servicing periods.

**Dữ liệu cần dùng:** 20 monthly certificates; reported pool/note/distribution/reserve metrics.

**Phương pháp / thao tác:** Select collection/payment dates; reconcile typed amounts với reports; giữ aggregate history và coverage.

**Đầu ra:** Pool/note trends, period metrics và source comparisons.

**Điều kiện nghiệm thu / cách đọc:** Aggregate pool reports không là asset-level persistent panel; Ginnie/ABS-EE loan-level tracks còn thiếu.

**Bước phát triển tiếp theo:** Thêm deal-specific asset IDs/schema và collateral-history adapter.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=abs&workspace_tab=overview)

### P5.03 — Cash-flow projection

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** Dự báo cash flows của collateral theo contract và loss/prepay assumptions.

**Dữ liệu cần dùng:** Asset schedules, rates/reset terms, default/prepay/recovery timing và servicing fees.

**Phương pháp / thao tác:** Projected contractual collections→defaults/prepayments→recovery lag→available funds; conserve cash theo kỳ.

**Đầu ra:** Forward pool cashflows và scenario assumptions.

**Điều kiện nghiệm thu / cách đọc:** Reported history không được gọi là projection; chưa có complete collateral contracts.

**Bước phát triển tiếp theo:** Thiết kế collateral schedule intake và calibrate suitable behavior models.

### P5.04 — Sequential waterfall

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Theo dõi available cash được phân bổ theo từng priority.

**Dữ liệu cần dùng:** Reported inputs và selected pre-acceleration terms; cash/reserve beginning states.

**Phương pháp / thao tác:** Thực thi ordered fee/interest/principal/reserve stages; giữ due/paid/unfunded và before/after states; A2pro-rata trong supported terms.

**Đầu ra:** Priority explorer, stage allocations, full ledger và period export.

**Điều kiện nghiệm thu / cách đọc:** Cash/balance conservation; reviewer prior obligations có giả định; không gọi unconditional legal compliance.

**Bước phát triển tiếp theo:** Verify full legal regimes, prior obligations và amendments trước full contractual engine.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=abs&workspace_tab=waterfall)

### P5.05 — Tranche & triggers

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Đọc nghĩa vụ và số dư từng lớp chứng khoán trong kỳ.

**Dữ liệu cần dùng:** Seven issued tranches, coupons/day counts, funded principal, OC/reserve và selected review trigger.

**Phương pháp / thao tác:** Select tranche; reconcile interest/principal/ending balance; đọc trigger qualification theo terms đã hỗ trợ.

**Đầu ra:** Tranche balances/payment detail và source checks.

**Điều kiện nghiệm thu / cách đọc:** Stage shortfalls không cộng thành credit loss; không prorate pool loss thành tranche loss; unsupported triggers giữ gap.

**Bước phát triển tiếp theo:** Bổ sung verified trigger state/history và loss-allocation/legal regimes.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=abs&workspace_tab=tranches)

### P5.06 — Scenario valuation

**Trạng thái:** Một phần.

**Mục tiêu:** Định giá dòng tiền theo discount assumptions và kiểm tra độ nhạy.

**Dữ liệu cần dùng:** Fixed-coupon face/coupon/yield/years/frequency; actual instrument quotes chưa có.

**Phương pháp / thao tác:** Dùng coupon-date cashflows; discount theo declared yield; giữ conventions và independent par/annuity benchmarks.

**Đầu ra:** Assumed bond price/schedule/export; actual ABS valuation chưa hỗ trợ.

**Điều kiện nghiệm thu / cách đọc:** Treasury/index OAS không là deal quote; không gọi market-calibrated ABS price.

**Bước phát triển tiếp theo:** Thu thập instrument quotes và supported projected cashflows trước calibrated valuation.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=market&workspace_tab=bond)

### P5.07 — Bond sensitivity

**Trạng thái:** Có điều kiện.

**Mục tiêu:** Đọc price sensitivity khi giả định yield thay đổi.

**Dữ liệu cần dùng:** Declared fixed-coupon terms và discount yield/conventions.

**Phương pháp / thao tác:** Tính duration/convexity; đối chiếu analytical sensitivity với finite bumps; inspect schedule principal conservation.

**Đầu ra:** Duration, convexity, bump residuals và bond scenario export.

**Điều kiện nghiệm thu / cách đọc:** Scope coupon-date benchmark; chưa dirty/clean/accrued/spread curve của mọi actual security.

**Bước phát triển tiếp theo:** Thêm trade/settlement dates, day-count/accrual và curve benchmark pricers.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=market&workspace_tab=bond)

### P5.08 — CDS credit curve

**Trạng thái:** Cần dữ liệu.

**Mục tiêu:** Bootstrap risk-neutral survival/hazard từ CDS term quotes.

**Dữ liệu cần dùng:** Reference entity quotes/tenors, recovery, discount curve và CDS conventions.

**Phương pháp / thao tác:** Price premium/protection legs theo accrual conventions; solve hazard từng tenor; reprice quotes bằng independent pricer.

**Đầu ra:** Credit curve, implied spreads và pricing residuals.

**Điều kiện nghiệm thu / cách đọc:** Index OAS không thay CDS quotes; risk-neutral probability không thay borrower real-world PD.

**Bước phát triển tiếp theo:** Lấy licensed term quotes và freeze pricing conventions/benchmark.

### P5.09 — Position & scenario comparison

**Trạng thái:** Một phần.

**Mục tiêu:** Đặt market context và instrument scenarios cạnh nhau với scopes rõ.

**Dữ liệu cần dùng:** Native Treasury/OAS series, declared bond scenarios và currency/date conventions.

**Phương pháp / thao tác:** Filter native dates; giữ Sunday OAS observations và Treasury discontinuation quarantine; không interpolate tùy tiện.

**Đầu ra:** Market context, scenario outputs và independent scoped exports; chưa combined security-position book.

**Điều kiện nghiệm thu / cách đọc:** Index không là executable price; actual exposure representations không double-count cùng underlying risk.

**Bước phát triển tiếp theo:** Thêm typed security-position mapping và supported instrument cashflow engines.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=market&workspace_tab=series)

### P5.10 — Surveillance & numerical evidence

**Trạng thái:** Một phần.

**Mục tiêu:** Đối chiếu reported history, numerical invariants và qualification của replay.

**Dữ liệu cần dùng:** Reported source metrics, canonical mappings, conservation checks và period history.

**Phương pháp / thao tác:** Đọc source comparisons; reconcile pool/note/payments/reserve; mở ledger/tranche evidence và exact export.

**Đầu ra:** Period check report, discrepancy support và conditional qualification.

**Điều kiện nghiệm thu / cách đọc:** Không bỏ dropped amendments/unsupported triggers; chưa live surveillance event feed.

**Bước phát triển tiếp theo:** Thêm fresh servicing periods, legal change detection và review ownership.

[Mở workflow liên quan](http://127.0.0.1:8770/?view=abs&workspace_tab=checks)

## Theo dõi triển khai

Các chức năng cần data mới không được thay bằng mock results. Mỗi đợt implementation phải cập nhật source scope, gates, evidence và trạng thái trong FIVE_WORKSPACES_STATUS.md. Corporate memo, collections, affordability, full legal waterfall và CDS tiếp tục là dependencies thật của suite.

[Plan tổng thể](PLAN_FIVE_WORKSPACES.md) · [Trạng thái thực tế](FIVE_WORKSPACES_STATUS.md) · [Cách dùng app](WORKBENCH_USER_GUIDE_VI.md)

## Enterprise monitor update

[Nghiên cứu mở rộng 14 hãng và bản monitor đã triển khai](ENTERPRISE_CREDIT_MONITOR_RESEARCH.md). App mở mặc định Risk monitor; trang năm workspace và 50 capability plans tiếp tục truy cập riêng.
