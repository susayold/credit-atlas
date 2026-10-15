# CreditAtlas — kế hoạch dữ liệu và triển khai 5 workspace

> Cập nhật 10/10/2026: [Plan chi tiết 50 chức năng và hướng dẫn trong app](PLAN_WORKBENCH_DETAIL.md). Mỗi chức năng có mục tiêu, inputs, phương pháp, outputs, nghiệm thu và bước tiếp theo; đây là roadmap, không chứng nhận đã triển khai đủ.

Ngày: 09/10/2026. Phạm vi: tải các nguồn tiếp cận được trước, lập kế hoạch
chi tiết và tự triển khai. Đây là kế hoạch toàn bộ suite; hoàn thành ingestion
không đồng nghĩa hoàn thành 50 chức năng hoặc có model đã được kiểm định.

## 1. Giữ cấu trúc từ research đã thống nhất

Một ứng dụng CreditAtlas, năm workspace chuyên biệt. Shared core quản lý
source snapshots, schema, units, evidence, run registry, findings và exports.
Mỗi workspace sở hữu data contracts, target, model và phép tính riêng.
Research gốc: `D:\data\Codex\research\credit-risk-master\2026-10-08\CREDIT_RISK_MASTER_RESEARCH.md`,
chương 33–37 và các case D01–D11. Kế hoạch D01 đầy đủ tiếp tục có hiệu lực
trong `PLAN_MODULE_01.md`; kế hoạch suite này không thay thế các gate R0–R4.

| Workspace | Câu hỏi chính | Cases khởi đầu | Nguồn ưu tiên |
|---|---|---|---|
| P1 Retail | Ai có khả năng trễ/default theo target cụ thể; policy nào phù hợp? | Behavioral benchmark rồi application/booked loans | UCI credit cards; Home Credit/AmEx/LendingClub nếu có quyền truy cập |
| P2 Mortgage & real estate | Khoản vay chuyển trạng thái, cure, exit và loss ra sao? | D01 rồi HMDA/CRE | Freddie 2012 hiện có, FRED; Clarity thêm vintage khi đăng nhập |
| P3 Business credit | SME/corporate có dấu hiệu rủi ro và bằng chứng nào? | SBA snapshot và Polish benchmark; SEC issuer memo tiếp theo | Sáu SBA FOIA CSV + dictionary, UCI bankruptcy, SEC |
| P4 Portfolio & observatory | Exposure tập trung/loss ra sao; ngân hàng và quốc gia có chỉ báo gì? | Bank-quarter observatory; typed exposure import | FDIC financials/failures, exports phù hợp từ P1–P3, macro |
| P5 Structured & market | Cash/loss đi qua cấu trúc và giá nhạy với assumptions ra sao? | Market context, bond benchmark và simple waterfall | Treasury yields, corporate OAS context; SEC ABS/Ginnie ở bước collateral |

Không gọi UCI credit cards là application underwriting data. Không gọi FDIC
bank-quarter là loan book. Không gọi OAS index là quote của từng bond/CDS.
Không coi SBA terminal status là fixed-horizon PD. Polish horizon code không
phải năm lịch; thiếu issuer ID thì không khẳng định entity-disjoint temporal
validation. P5 waterfall với terms giả định phải được gắn nhãn scenario.

## 2. Thứ tự thực hiện

### A. Thu thập trước và lưu evidence

Batch đầu gồm UCI 350/365 payload + metadata, sáu SBA FOIA segments as-of
2026-06-30 và dictionary, FDIC financials quý 2026-06-30 cùng failures,
UNRATE/USSTHPI/MORTGAGE30US/DGS2/DGS10/DGS30/BAMLC0A0CM.
Endpoint phải lấy từ nguồn chính thức; raw giữ private trên D:.

Downloader lưu start receipt, per-source receipt, full batch receipt, bytes,
SHA-256, URL, thời điểm tải, units/source scope và rights. HTTP lỗi không được
ghi nhận là dataset thành công. File chưa hoàn tất có hậu tố `.partial`.
FDIC phải đối chiếu returned rows với source total; thiếu pagination thì fail.
CSV phải đọc hết rows, kiểm tra width/header và missing sentinels. Dictionary
XLSX phải kiểm tra ZIP integrity trước khi parse nội dung.

Các nhóm dữ liệu tiếp theo vẫn thuộc phạm vi acquisition, không bị loại bỏ:
HMDA theo lender/year extracts và dictionary; SBA lịch sử đã chia file;
FDIC historical quarter panels và metric definitions; SEC companyfacts và
submissions theo issuer; một ABS-EE asset class/deal với XML/schema; Ginnie
pool/loan disclosure theo release; sovereign/BIS/World Bank theo country/date.
Home Credit/AmEx/Clarity chỉ tiếp tục khi có quyền truy cập. Không tải toàn
bộ EDGAR hay hàng chục GB mortgage khi chưa chọn contract/coverage cần thiết.

### B. Canonical adapters và kiểm tra chất lượng

Mỗi source có namespace và version riêng. Canonical tables giữ source key
trong private storage; browser chỉ đọc aggregate hoặc pseudonymous keys
đúng scope. Phải lưu observation time, source snapshot time, extraction time
và publication time khi thực sự biết; không điền extraction thay publication.

UCI retail: ID uniqueness, đúng binary target, feature numeric/sentinels,
six-month history ordering, sensitive fields và feature availability memo.
UCI bankruptcy: reconcile từng horizon subset, missingness và extreme ratios,
không ghép doanh nghiệp qua subset nếu không có entity key.
SBA: grain/dedup, approval/disbursement/status/charge-off dates, amount units,
unknown/EXEMPT/cancelled status và definition mapping từ dictionary.
FDIC: CERT×REPDTE uniqueness, complete pagination, units/ratio definitions,
reporting-versus-publication time và institution history theo CERT.
FRED: native dates/frequency, missing values, revisions và rights. Treasury
constant-maturity yields không phải zero-coupon discount curve đã bootstrap.

### C. Xây shared suite explorer

Source catalog và receipt explorer cho cả P1–P5, phân biệt downloaded,
profiled, canonical, descriptive ready, model qualified và blocked.
Hiển thị rõ supported functions/data gaps cho mỗi workspace. URL state,
private findings, source/method versions và aggregate exports được reuse từ
D01 sau khi contracts của từng case đã rõ. Không reuse mortgage model/target
cho dataset khác chỉ để tất cả workspace có bảng metrics.

### D. Các vertical slices và chức năng đầy đủ

Ưu tiên P1 benchmark → P3 descriptive SME/ratio → P4 bank observatory →
P5 market/bond/waterfall, song song tiến độ code P2 hiện có theo dependencies.
Một slice phải có raw → canonical → checks → aggregate → UI → export →
rerun evidence. Không kết luận suite hoàn tất khi chỉ dựng navigation.

## 3. P1 — Retail: mười khả năng và gate

| Khả năng | Triển khai | Điều kiện kiểm chứng |
|---|---|---|
| Intake/source explorer | Dataset/feature contracts, source profile, target card | Rows/classes/IDs reconcile; sentinel definitions review |
| Application score | Source-specific feature/model pipeline | Cần application-time features và appropriate label; UCI behavioral không thay thế |
| Behavioral score | UCI six-month features; constant/logistic/challenger | ID excluded, train-only transforms, held-out calibration/evaluation |
| Decision/policy workbench | Implemented research threshold/action/cost scenarios, review capacity, preview/version/export on fixed validation | Cost assumptions explicit; không gọi observed outcomes cho rejected population |
| Affordability | Income/payment/cash-flow rules | Thiếu income thật thì blocked hoặc educational assumptions |
| Limit/pricing scenario | Versioned cost/limit assumptions | Không khẳng định optimized production pricing từ benchmark |
| Explainability | Implemented whole-validation grouped permutation + exact four-group finite-reference probability Shapley for every4,499 validation clients; whole-cohort contribution distributions, paginated token search, source-bound API/UI/private per-client export | Source/model/reference pinned; cross-group hybrids may be unrealistic, no causal interpretation or approved adverse-action reasons; new application-client scoring, reference sensitivity and intended-use qualification remain open |
| Collections | Behavioral priorities và case workflow | Cần events/contact/repayment data cho efficacy claims |
| Monitoring/fairness | Implemented validation subgroup coverage/calibration/AUC/policy capture by SEX, EDUCATION, MARRIAGE and declared age bands; source-bound immutable study/API/UI/export | Minimum support enforced; no temporal monitoring, causal effects or fairness certification; real monitoring cohorts remain required |
| Evidence/governance | Model card, findings, frozen protocol, exports | Complete lineage; benchmark scope không thành VN calibration |

P1 model sequence: freeze cohort/target/feature list, deterministic split,
train-only preprocessing, constant/logistic reference, nonlinear challenger,
separate calibration, untouched evaluation, uncertainty and leakage audit.
Không gọi random holdout là OOT nếu source chỉ có cùng historical cohort.

## 4. P2 — Mortgage: tiếp tục đúng kế hoạch D01

Mười khả năng giữ nguyên: source/run explorer; panel quality; portfolio/cohort;
private lifecycle; count/opening-UPB transitions; cure/redefault; competing
outcomes; horizon-risk models; observed loss bridge; evidence/review/export.
Hiện có actual 2012 descriptive pipeline và app. Multi-vintage temporal study,
selection freeze, final OOT và qualified scoring vẫn cần data/gates R2–R3.
Macro context là descriptive extension, không mở khóa model thiếu vintages.
Sau D01: HMDA origination-market case; CRE/DSCR/maturity case riêng.

Acquisition/canonical checkpoint: D08 đã có 347.056 HMDA public records,
Maryland/home-purchase/site-built 2023–2025, 99 raw fields, selected typed
application facts và 7.477 dimension marts. Kế hoạch/contract và các bước
app/review/coverage tiếp theo ở [HMDA_APPLICATION_WORKFLOW.md](HMDA_APPLICATION_WORKFLOW.md).
Application/purchase outcomes và public privacy modifications không thay
Freddie loan-performance vintages hoặc các D01 qualification gates.

## 5. P3 — Business/SME/corporate

| Khả năng | Input và xử lý | Evidence/gate |
|---|---|---|
| SME source/borrower explorer | SBA source-native ingestion và status/date audit | Unique source loan key và full segment reconciliation |
| Financial statement normalization | SEC concepts/units/periods/accessions | Filing/as-of context; custom tags/gaps explicit |
| Ratio analysis | Polish/SEC ratios với definition cards | Missing/extreme không silently truncate; units đúng |
| Bankruptcy benchmark | Từng Polish horizon riêng, source-specific target | Không pool horizons thành một PD; entity overlap unknown |
| SME outcomes | SBA status/cohort/charge-off descriptive | EXEMPT/unknown/cancelled separate; timing qualification trước survival model |
| Corporate credit memo | Financial facts + verified issuer/event sources | Facts trỏ raw filing; narrative không tạo fact mới |
| Covenant workbench | Facility terms + independent calculations | Terms chưa có thì assumptions-only, không actual breach |
| Debt/maturity/cash-flow | Schedules và scenarios | Cần debt terms; annual ratios không thay schedule |
| Sector/concentration | SBA NAICS/geography/status with denominators | Scope booked program, không toàn bộ SME economy |
| Review/export | Memo version, findings, supporting calculations | Source rights, issuer identity và date scope |

Post-outcome SBA fields (status, charge-off amount/date, final payoff) không
được đưa vào approval-time predictors. Historical snapshot availability phải
được kiểm tra trước khi gọi backtest as-of. Không fuzzy-match SBA names với SEC
để tự tạo default labels cho corporate financials.

## 6. P4 — Portfolio/finance/observatory

Checkpoint 09/10/2026: typed import/reconcile/concentration và declared
factorized research EL contract đã triển khai, API/UI/private export đã có.
Actual source snapshot 9.698 observations giữ EL unavailable vì chưa có risk
inputs. Xem [EXPOSURE_IMPORT_WORKFLOW.md](EXPOSURE_IMPORT_WORKFLOW.md) để chạy
lại và xem gates. [Movement bridge](EXPOSURE_MOVEMENT_WORKFLOW.md) cũng đã có
ordered source attribution/residual và source-bound app/export, independent
500-check audit PASS. [Declared scenario workbench](EXPOSURE_SCENARIO_WORKFLOW.md)
đã có versioned assumptions, eligibility/clipping, PD/LGD/EAD sensitivity và
ordered EL attribution; independent 2.755-check audit PASS. Calibrated risk/
macro stress vẫn chưa qualified. Tiếp tục theo thứ tự cash-flow/risk evidence
adapters → accounting-qualified ECL/staging → calibrated tail/review. [Declared ECL
research engine](EXPOSURE_ECL_WORKFLOW.md) đã có full cash-tail/recovery timing,
conditional hazards, snapshot SICR/default, scenario weights và source-bound
UI/private export; 1.885 independent checks PASS. Actual contract/EIR/risk
evidence và unsupported POCI/revolving/cure policies còn thiếu;
các mục dưới đây vẫn là toàn bộ scope, không đánh dấu toàn P4 hoàn thành.

| Khả năng | Implementation | Gate |
|---|---|---|
| Typed exposure import | Units/currency/date/target validation | Reject unknown score semantics, mixed scopes |
| Reconcile/concentration | Counts, balances, currency and segments | Input totals/exclusions reconcile |
| Research EL | Explicit PD/EAD/LGD assumptions | Proxy label; no regulatory/accounting compliance claim |
| ECL/staging | Marginal/conditional probability contract + cash schedules | Default/staging/SICR/discount/recovery policy required |
| Scenario/stress | Versioned responses/assumptions | Calibrated relationship or assumption disclosure |
| Movement bridge | Ordered changes and residual attribution | No double counting; residual retained |
| Tail/concentration simulation | [Seeded finite-position dependence/recovery engine](EXPOSURE_TAIL_WORKFLOW.md), native-currency VaR/ES/joint-tail attribution; actual research run verified | Research assumptions only; multi-seed convergence, calibrated correlation/recovery and obligor linkage still open |
| Bank observatory | FDIC quarter/history panel, peers and missingness | Definitions/units and publication availability |
| Country observatory | Macro/sovereign default-debt series | Country scope and native grain; index is not PD |
| Finance/review package | [Source-bound research snapshots, versions, rationale, owner/expiry and private export](PORTFOLIO_STABILITY_AND_REVIEW.md) | Research annotation only; no source overrides, actual accounting approval or authenticated human sign-off |

Không cộng mortgage underlying và security position vào cùng exposure total
như hai independent assets nếu cùng rủi ro được nắm giữ theo hai representation.
FDIC failure event không biến thành borrower default label.

## 7. P5 — Structured/market

| Khả năng | Implementation | Gate |
|---|---|---|
| Deal/instrument catalog | Contract schemas, sources, supported terms | Unsupported terms explicit |
| Collateral pool | Typed source exports / ABS or Ginnie adapter | Asset ID persistence, period/deal reconciliation |
| Cash-flow projection | Schedule + default/prepay/recovery assumptions | Projection identified; no invented realized cash flows |
| Sequential waterfall | Fees/interest/principal/residual state machine | Cash and balance conservation every period |
| Tranche loss/trigger | Priority/timing/attachment rules | Deal-specific terms; not pro-rata pool loss |
| Scenario valuation | Cash flows + discount assumptions | No market-calibrated price without instrument quotes |
| Bond sensitivity | Coupon/day-count/accrual conventions | Independent benchmark and finite-difference checks |
| CDS credit curve | Quotes, recovery, discount, conventions | Risk-neutral semantics; reference-pricer repricing |
| Position/scenario comparison | Supported instrument positions | Currency/date conventions; execution assumptions explicit |
| Surveillance/numerical evidence | Pool/deal changes and invariant reports | No dropped amendments/unsupported triggers |

Treasury and index OAS permit market-context exploration; they do not supply
ABS deal waterfalls or CDS term quotes. ICE series stays internal/private under
its source terms. SEC ABS/Ginnie acquisition and schema selection remain a
required next data track for actual structured surveillance.

## 8. Shared contracts and project organization

Code packages: shared acquisition/catalog/quality/run/evidence; separate retail,
mortgage, business, portfolio and structured calculations. Tables never use
untyped universal `PD` or mix reporting grain in one mart. Model/scenario
exports carry target, horizon, probability measure, currency, source snapshot,
method digest, coverage and limitations. Default users see supported analytical
flows; internal implementation details stay in source/evidence views.

All raw/private receipts, IDs, model scores and research derivatives live under
ignored D: paths. Browser serves explicit routes, not raw data directories.
Aggregate summaries must verify source/method digests and use whitelisted
fields. New source rights do not authorize external publication automatically.

## 9. Acceptance và tiến độ thực tế

Per-source: verified HTTP status, nonempty payload, hash, grain, schema,
missingness, completeness, definitions, date/rights scope. Per-case: source-native
canonical counts reconcile, target exclusions, deterministic reproduction.
Per-model: saved protocol, feature availability/leakage audit, support,
train-only fitting, calibrated held-out results, artifact parity and intended-use
model card. Per-numerical engine: conservation, benchmark, convergence and
explicit unsupported assumptions. Per-app: runtime/API/browser/mobile/export
checks, private ID exclusion, altered evidence rejection and saved findings.

The suite is complete only after the agreed functions have supported evidence
or an explicitly accepted conditional scope; unavailable data stays an open
dependency. Counts of passing software tests do not substitute for actual data
qualification or completed model/market studies.

Commands and actual per-source results will be maintained in
`FIVE_WORKSPACES_STATUS.md`, with immutable private run receipts. Continue
development autonomously on available sources while authentication-dependent
tracks remain recorded as blocked dependencies.


## 10. Excel integration checkpoint — 10/10/2026

P4 has native XLSX intake and six-sheet review export with typed source lineage,
editable factorized scenario formulas, source reconciliation and currency-scoped
reviews. See [EXCEL_WORKFLOW.md](EXCEL_WORKFLOW.md). This establishes the common
analyst file workflow. Subsequent domain adapters must preserve each source's
keys, target, units and dates; importing all spreadsheets through P4 would not
turn HMDA decisions, SBA approvals or SEC issuer statements into loan exposure.
Dictionary XLSX is schema documentation, not portfolio positions. CSV can be
opened in Excel but does not carry worksheets, formulas or Excel validation.
Application intake, financial-statement templates and mortgage contract sheets
remain separate mappings before sharing the same file upload/review interface.
