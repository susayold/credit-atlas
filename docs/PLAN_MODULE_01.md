# CreditAtlas — Plan chi tiết module đầu tiên

**Module:** P2 — Mortgage & Real Estate.  
**Case:** D01 — Residential Mortgage Lifecycle & Loss Lab.  
**Ngày:** 08/10/2026.  
**Workspace:** D:/data/Codex/credit-atlas.

## Quyết định triển khai

Xây một app CreditAtlas; triển khai một case mortgage đủ sâu trước, rồi mở rộng các workspace khác. D01 nghiên cứu vòng đời khoản vay nhà ở: trạng thái trả nợ, chuyển trạng thái, cure/redefault, competing exits, vintage và observed loss. Phần model được nghiệm thu sau khi dữ liệu và protocol đủ điều kiện.

Nguồn chính là Freddie Mac annual loan-performance samples. Reuse engine credit-risk-strategy-lab qua commit pin và kiểm tra parity. FRED/ALFRED, FHFA, Fannie, HMDA và multifamily có thứ tự mở rộng riêng trong kế hoạch.

## Thứ tự triển khai

| Mốc | Làm gì | Khi nào đạt |
|---|---|---|
| R0 | Xác nhận source/code/schema/hashes; clean rebuild; đo tài nguyên | Pipeline có receipts, totals và đối chiếu giải thích được |
| R1 | Source/DQ, danh mục, timeline, transitions, episodes, vintage, loss và findings | Cùng frozen run; số liệu reconcile; user flow và export được kiểm tra |
| R2 | Qualify nhiều năm; chốt features và temporal splits | Coverage, support, maturity và leakage checks đạt protocol |
| R3 | Constant/logistic baseline, boosting challenger, calibration và OOT | Cùng cohort; selection freeze; model card và serving parity |
| R4 | Reproduction toàn case, QA và tài liệu bàn giao | Người khác chạy lại và đọc được question/data/method/results/limits |

**Budget dự kiến:** 160–232 giờ chủ động; khoảng 6–12 tuần nếu dành 20–30 giờ/tuần. R0+R1 khoảng 56–80 giờ. Estimate chưa bao gồm thời gian chờ access; support của nguồn có thể kéo dài phần model.

## Điểm xuất phát đã kiểm tra trong workspace

Kế hoạch gốc bên dưới được giữ như specification tại thời điểm lập. Các câu “chưa chạy trong lượt lập plan” là ghi nhận lịch sử. Bảng này bổ sung evidence local hiện có, không thay thế checklist nghiệm thu từng release.

| Phần | Evidence hiện có | Việc còn phải làm |
|---|---|---|
| Foundation | Engine pin 8d9994cfcb91fe871d66a4238c3f56053d71e920; sample 2012: 50.000 loans, 4.510.559 loan-months | Semantic trace trên corpus 2012 đã pass; dependency/resource documentation và cross-vintage review còn mở |
| Tests engine | 375 tests chạy đạt trong môi trường mới | Tests adapter/service/privacy/review/error handling |
| Reproduction | Hai pipeline đối chiếu 13 tables và 4 stable summaries; không có row differences | Final reproduction gồm app/report và model khi đã có |
| Descriptive app | Code views, frozen snapshot, timeline private, report và findings đã có | Browser QA real-data đạt 39 checks; stale/missing/unlisted run, connection failure và malformed JSON fail closed; chart/support audit đối chiếu mẫu số monthly, vintage, profile, transition và loss; năm màn chính pass 390px. Tiến độ mới nhất ở IMPLEMENTATION_STATUS.md và D01_CHART_SUPPORT_AUDIT_VI.md |
| Model | Chỉ có annual vintage 2012; 102 positive early-entry D3: 89 Relief, 13 non-Relief | Qualify vintages khác; support/protocol review; chưa fit model mortgage đủ điều kiện |
| Cập nhật acquisition 15/10/2026 | Browser QA real-data chạy lại: 39 checks PASS; chart/support audit qua 6 nhóm. Tải Release 47 public example ZIP và File Layout tháng 07/2026; 31/35 trường khớp layout | Example files không phải annual sample: 1.000 origination IDs và 12 performance IDs không giao nhau. Không ghép thành panel; thêm 0 vintage. Annual downloads vẫn cần Clarity login; xem IMPLEMENTATION_STATUS.md và FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md |

Công việc tiếp theo là hoàn thiện R0/R1 và chuẩn bị R2. Số lượng loan-month không phải số lượng independent positive outcomes.

## Sprint tiếp theo

1. Hoàn thiện inventory/dependency/resource receipts; semantic audit Release 47 corpus 2012 đã có tại D01_CANONICAL_SEMANTIC_AUDIT_VI.md.
2. Xử lý lỗi browser; kiểm tra run/segment/basis/timeline/export/finding/mobile.
3. Kiểm tra adapter/service: không trộn run; không lộ source loan IDs; artifact bị sửa phải bị từ chối.
4. Đối chiếu portfolio/transition/vintage/loss; bổ sung follow-up audit cure/redefault.
5. Hoàn thiện freshness/missingness/support monitoring và investigation runbook.
6. Lưu findings có evidence; viết run instructions và R1 acceptance memo.
7. Pilot annual vintage bổ sung khi có quyền truy cập; ghi schema/support/footprint trước mở rộng protocol.

## Mục lục chi tiết

- [47.1. Quyết định: làm module nào trước và sản phẩm phải giải quyết gì?](#chuong-47-1)
- [47.2. Đã có gì trong GitHub và khoảng trống nào thật sự phải giải quyết?](#chuong-47-2)
- [47.3. Scope từng đợt và những điều kiện phụ thuộc](#chuong-47-3)
- [47.4. Mười khả năng cụ thể của D01 và mapping về module P2](#chuong-47-4)
- [47.5. Data acquisition plan: nguồn nào trước, nguồn nào sau?](#chuong-47-5)
- [47.6. Storage, ngân sách máy và nguyên tắc mở rộng](#chuong-47-6)
- [47.7. Kiến trúc kế thừa: một domain engine, một cách tính](#chuong-47-7)
- [47.8. Contracts và tables: giữ grain, version và availability](#chuong-47-8)
- [47.9. Target contract đầu tiên: giữ early-entry D3 trước prepayment/maturity](#chuong-47-9)
- [47.10. Các semantics bắt buộc giữ từ source dictionary](#chuong-47-10)
- [47.11. Feature plan và temporal protocol](#chuong-47-11)
- [47.12. Model plan: baseline, challenger, calibration và lựa chọn cuối](#chuong-47-12)
- [47.13. Validation report: đo gì và tránh kết luận quá tay?](#chuong-47-13)
- [47.14. Transitions, vintage, competing events và episodes](#chuong-47-14)
- [47.15. Loss plan: descriptive bridge trước severity/LGD](#chuong-47-15)
- [47.16. Macro, forecast và stress: mở từng bước có bằng chứng](#chuong-47-16)
- [47.17. App journey: màn hình, actions và dữ liệu hiển thị](#chuong-47-17)
- [47.18. Backlog triển khai: 30 công việc với dependencies và nghiệm thu](#chuong-47-18)
- [47.19. Extensions được tách khỏi critical path](#chuong-47-19)
- [47.20. Effort và lịch làm: gate quyết định chất lượng, lịch giúp tổ chức công việc](#chuong-47-20)
- [47.21. Verification plan: checks cần thiết cho risk results và user flow](#chuong-47-21)
- [47.22. Definition of Done theo từng release](#chuong-47-22)
- [47.23. Kế hoạch 10 ngày làm việc đầu: làm gì ngay khi bắt đầu implementation?](#chuong-47-23)
- [47.24. Output giao cho P4/P5 và phần shared core thực sự được xây](#chuong-47-24)
- [47.25. Những điểm chưa chắc chắn và quyết định xử lý](#chuong-47-25)
- [47.26. Nguồn được đọc và độ chắc chắn của plan](#chuong-47-26)

Giữ đủ 26 mục và 30 task của chương 47. Research gốc: [CREDIT_RISK_MASTER_RESEARCH.md](D:/data/Codex/research/credit-risk-master/2026-10-08/CREDIT_RISK_MASTER_RESEARCH.md). SHA-256 lúc trích: 7140a343a3e89970de7d9d6bfe7a27d0fd5648b09d24dba099e40140f3e7ed60.

---

<a id="chuong-47"></a>

## 47. P2 / D01 — Kế hoạch xây Residential Mortgage Lifecycle & Loss Lab

**Ngày lập và đối chiếu: 08/10/2026. Đây là kế hoạch triển khai; lượt này chưa tải thêm annual data, chạy lại pipeline, fit model hoặc xây app.** Phạm vi chọn từ [P2 ở chương 34](D:/data/Codex/research/credit-risk-master/2026-10-08/CREDIT_RISK_MASTER_RESEARCH.md#chuong-34), [charter D01 ở 44.1](D:/data/Codex/research/credit-risk-master/2026-10-08/CREDIT_RISK_MASTER_RESEARCH.md#chuong-44-1) và [ưu tiên ở 46.1](D:/data/Codex/research/credit-risk-master/2026-10-08/CREDIT_RISK_MASTER_RESEARCH.md#chuong-46-1). Kế hoạch này cụ thể hóa D01 bằng tài liệu repo đọc trực tiếp qua GitHub, thay cho việc giả định mọi phần còn cần xây từ đầu.

<a id="chuong-47-1"></a>

### 47.1. Quyết định: làm module nào trước và sản phẩm phải giải quyết gì?

**Module đầu tiên là P2 — Mortgage & Real Estate. Case triển khai đầu tiên là D01 — Residential Mortgage Lifecycle & Loss Lab**, dùng lịch sử khoản vay thế chấp nhà ở Mỹ. CreditAtlas tiếp tục là sản phẩm chung với năm workspace; đợt này chỉ làm một workspace có dữ liệu, phương pháp và kết quả kiểm tra được. D08 HMDA và D09 multifamily giữ là các case tiếp theo trong P2.

Sản phẩm giúp một risk analyst trả lời sáu câu hỏi:

1. Dữ liệu đang bao phủ những khoản vay, tháng và vintage nào; phần nào thiếu hoặc không đủ follow-up?
2. Tình trạng danh mục thay đổi thế nào; tăng D3 là tăng số ca mới, thay đổi mix hay thay đổi mẫu số?
3. Khoản vay chuyển giữa current, D1, D2, D3+, REO và các trạng thái kết thúc như thế nào?
4. Trong quần thể và horizon đã định nghĩa, xác suất quan sát D3 trước prepayment/maturity có thể được ước lượng đáng tin đến đâu?
5. Những khoản có thông tin loss cho thấy các thành phần tổn thất nào; bao nhiêu khoản còn unresolved hoặc thiếu dữ liệu?
6. Một kết luận trong dashboard được tạo bởi dữ liệu, công thức, target và run nào; reviewer có thể kiểm tra và lưu nhận xét ra sao?

Đối tượng sử dụng ban đầu: **bạn với vai trò builder/analyst**, một người đọc portfolio hoặc phỏng vấn với vai trò viewer, và một reviewer nghiên cứu. Không có nhu cầu đã xác nhận về phục vụ ngân hàng nhiều người dùng, live loan origination hay ra quyết định cấp tín dụng thật. Vì vậy MVP ưu tiên phân tích, tái tạo bằng chứng, tương tác và review nội bộ.

**Sản phẩm đầu tiên được nghiệm thu là bản phân tích mô tả R1; bản mô hình được nghiệm thu riêng ở R3.** Tách hai đích giúp hoàn thành một app hữu ích ngay với foundation hiện có, đồng thời dành thời gian cho dữ liệu và validation của phần dự báo.

<a id="chuong-47-2"></a>

### 47.2. Đã có gì trong GitHub và khoảng trống nào thật sự phải giải quyết?

Repo nền ưu tiên: [susayold/credit-risk-strategy-lab](https://github.com/susayold/credit-risk-strategy-lab). Tài liệu được đọc ở nhánh `master` ngày 08/10/2026; `block-status.md` tự ghi ngày cập nhật 12/09/2026. Đọc tài liệu không thay cho kiểm tra code, dữ liệu local và chạy lại kết quả. Những số liệu bên dưới là **bằng chứng do repo ghi nhận**, chưa được tái đo trong lượt lập plan này.

| Thành phần | Bằng chứng đã đọc | Phần cần làm khi triển khai |
|---|---|---|
| Nguồn Freddie | Release 47; annual sample 2012; 50.000 loans và 4.510.559 loan-month rows | Tìm đúng snapshot local, đối chiếu hashes và quyền dùng; bổ sung các vintage cần cho protocol |
| Canonical/pipeline | `dim_loan`, `fact_loan_month`; raw preservation, sentinels; pipeline tám stage | Clean rebuild, đọc code và kiểm tra chuyển tiếp run; acceptance qua nhiều vintage |
| Nhãn early-entry | 48.066 eligible; 102 positive D3; contract về gaps, exits và maturity | Giữ định nghĩa hiện có; audit trên vintage mới và event support theo split |
| Cohort/vintage | Stock, first-event ledger, curves 6/12/24 tháng, competing exits, loan bootstrap | So sánh nhiều vintage; tách hiệu ứng thời gian/mix; kiểm tra uncertainty |
| Transitions/cure | Adjacent transitions; sustained cure/redefault; mart theo Relief | Kiểm tra gaps, mẫu số, repeated episodes; phân tầng giai đoạn và uncertainty |
| Loss bridge | Một terminal record/loan; signed components; unresolved coverage | Independent reconciliation; đa vintage; chỉ fit severity nếu đủ resolved outcomes và denominator phù hợp |
| Origination models | Constant/logistic/HistGradientBoosting và shared comparison runner đã có engineering tests | Chưa có so sánh model trên bộ mortgage đạt protocol; actual 2012-only gate vẫn chặn fit |
| Behavioral | Landmark features, current-state baseline, gated logistic đã có | Target/population riêng; shared-loan protocol và multi-vintage evaluation chưa hoàn tất |
| Macro/forecast/policy | Adapter as-of và nhiều thành phần đã được kiểm thử bằng fixtures; có descriptive S0/S1 replay | Real macro acquisition, forecast backtest, validated strategy và scenario study còn thiếu |
| Website/Excel | Local dashboard; workbook 15 sheets; repo ghi 4.569 preview cells khớp XLSX | Browser QA, đồng nhất snapshot, adapter CreditAtlas và giới hạn export/publication |
| Reproducibility | Repo ghi 375 tests; hai foundation runs khớp 13 tables và bốn summaries | Chạy lại trong môi trường được pin và snapshot hiện tìm thấy; mở rộng reproduction cho final case |

Nguồn đối chiếu: [README](https://github.com/susayold/credit-risk-strategy-lab/blob/master/README.md), [implementation status](https://github.com/susayold/credit-risk-strategy-lab/blob/master/block-status.md), [model comparison](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/model-comparison.md).

**Khoảng trống quan trọng nhất là support và protocol, không phải thiếu tên thuật toán.** Trong 102 positive early-entry, repo ghi 89 thuộc Relief Refinance và chỉ 13 thuộc non-Relief. Split audit hiện có 100 positive đủ điều kiện train, còn các vintage calibration/validation/final test chưa có. 4,51 triệu monthly records không biến thành 4,51 triệu independent outcomes cho target này. Vì vậy chưa hợp lý để train thêm một model rồi tuyên bố flagship đã hoàn thành.

Hai sửa nghĩa cần ghi rõ so với cách nói khái quát ở chương 34: annual sample year là **origination vintage**, còn acquisition/first observation xác định entry; lựa chọn vintage trên UI phải có tên trục chính xác. Target D3 hiện tại cũng cần giữ tên **D3 event risk**, thay vì mặc định đổi thành default PD. Chi tiết gốc: [source semantics ADR](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/decisions/ADR-002-source-semantics.md).

<a id="chuong-47-3"></a>

### 47.3. Scope từng đợt và những điều kiện phụ thuộc

| Release | Đầu ra được nghiệm thu | Chức năng mở | Điều kiện chuyển tiếp |
|---|---|---|---|
| R0 — xác nhận foundation | Inventory, hashes, dependency map; clean rebuild có receipt | Có thể đọc lại source/derived evidence hiện có | Snapshot tìm được, schema đúng; khác biệt giữa runs được giải thích |
| R1 — descriptive app | Panel/DQ, cohort/vintage, transitions, cure/redefault, loss bridge, evidence views | Bản phân tích dùng được trên 2012, kèm đúng coverage | Tổng số/UPB/nhãn đối chiếu; UI và report dùng cùng frozen run |
| R2 — multi-vintage research data | Các sample cần thiết, label/feature/split manifest; support review | Dataset dùng cho model đúng target/population | Vintages, availability, class support, maturity và protocol đạt yêu cầu đã ghi |
| R3 — validated research model | Baseline/challenger/calibration, uncertainty, OOT evaluation; model card | Horizon-risk page, frozen scoring và nghiên cứu screening nếu phù hợp | Same-cohort comparison, rubric/freeze trước final test; limitations được ghi |
| R4 — đóng gói D01 | Reproduction toàn case, browser QA, typed exports, reviewer memo, case study | Một module CreditAtlas có thể demo và bàn giao | Check nghiệm thu ở 47.21–47.22; xuất dữ liệu theo phạm vi nguồn cho phép |

**Trong scope chính:** residential fixed-rate mortgage của nguồn đã chọn; historical sample analytics; first-observed early-entry 12m D3 risk; observed transitions/cure/exits/loss; local/private app; nghiên cứu so sánh mô hình có temporal validation.

**Extensions sau scope chính:** behavioral model hoàn chỉnh; macro forecast và stress/reverse stress; severity/LGD model; Fannie external-source validation; HMDA market context; multifamily DSCR/maturity. Chúng có dependencies khác nhau và không phải điều kiện để R1 có giá trị.

CRE DSCR/maturity thuộc **P2-09**, làm qua D09 khi có annual/loan-level contracts phù hợp. D01 chưa bao phủ cash-flow underwriting của office/hotel/retail hay risk của mọi thị trường nhà ở. Dữ liệu mortgage Mỹ cũng chưa cung cấp calibration cho tín dụng Việt Nam.

<a id="chuong-47-4"></a>

### 47.4. Mười khả năng cụ thể của D01 và mapping về module P2

Mười khả năng dưới đây là các luồng trong một case. Chúng không tạo mười project hoặc mười services. Một khả năng có thể có bản descriptive ở R1 và phần model nâng cao mở sau.

| ID | Khả năng | Người dùng làm gì / kết quả nhận được | Release chính và mapping |
|---|---|---|---|
| D01-F01 | Source & run explorer | Chọn snapshot/run, xem nguồn, coverage, version, trạng thái và failures | R0/R1; P2-01 |
| D01-F02 | Panel & quality audit | Xem keys, missingness, gaps, sentinels, exclusions; drill vào evidence | R1/R2; P2-01/02 |
| D01-F03 | Portfolio & cohort explorer | Lọc origination vintage, product, Relief; xem counts, UPB và monthly stock | R1/R2; P2-03 |
| D01-F04 | Loan lifecycle timeline | Xem các tháng, entry, gap, first D3, terminal và cure confirmation của một loan trong private mode | R1; P2-02/04/07 |
| D01-F05 | Transition & roll analysis | Chuyển count/opening-balance matrices, xem roll paths và đủ/thiếu support | R1; P2-04 |
| D01-F06 | Cure & redefault episodes | Xem episode, one-month cure, sustained cure và redefault với follow-up | R1; P2-07 |
| D01-F07 | Vintage & competing outcomes | Xem incidence 6/12/24m, risk sets, D3/prepaid-or-matured/other exits và censoring | R1/R2; P2-06 |
| D01-F08 | Horizon-risk models | So baseline/challenger, calibration, uncertainty và OOT cho một target/version | R3; P2-05 |
| D01-F09 | Observed loss bridge | Xem signed components, terminal support, missing/unresolved và thời điểm loss | R1/R2; P2-08 |
| D01-F10 | Evidence, review & scenario package | Lưu findings, methodology, limits và exports; scenario chỉ khi qualified extension có dữ liệu/model | R1/R4; P2-10 |

Đích đầu tiên là **F01–F07, F09 và phần evidence của F10**. F08 chỉ có kết quả mortgage thực sau R2; trước đó trang model hiển thị trạng thái triển khai và lý do chưa đủ evidence. Scenario chưa có backtest sẽ có nhãn assumption/simulation rõ; không bơm sẵn số liệu để hoàn thiện giao diện.

<a id="chuong-47-5"></a>

### 47.5. Data acquisition plan: nguồn nào trước, nguồn nào sau?

| Nguồn | Dùng vào việc gì | Cách tiếp cận và thứ tự | Điều kiện kiểm tra |
|---|---|---|---|
| S01 Freddie, sample 2012 hiện có | Clean rebuild và descriptive MVP | Tái dùng annual ZIP/snapshot có manifest; không tải lại nếu file hợp lệ | File/hash/release/layout; quyền nghiên cứu đã ghi; sampling scope |
| S01 Freddie, annual samples bổ sung | Temporal train/calibration/validation/final test | Candidate train 2006–2012, calibration 2014, validation 2016, final 2018 theo protocol repo; acquire theo batch nhỏ | Mỗi năm có official annual sample đúng release; không thay bằng format examples; eligibility/support riêng |
| S25 FRED/ALFRED | Macro context và optional predictive as-of features | Adapter hiện có; UNRATE, USSTHPI, MORTGAGE30US sau core R1 | API access hợp lệ, series units/frequency/vintages và revision availability |
| S26 FHFA HPI | Regional collateral-price context hoặc scenario proxy | Pilot một index definition và geography/version; latest series dùng retrospective context nếu thiếu historical releases | Trục geography, seasonal adjustment, frequency, base/index type; không suy thành valuation cá nhân |
| S02 Fannie residential | External-source extension | Sau R3/R4, pilot và harmonize contract riêng | Feature/target/population/selection/time semantics tương thích trước validation |
| S27 FHFA/CFPB NSMO | Distinct public-use mortgage sample; possible separate external-cohort study | Review May 2026 PUF/codebook first; download only after FHFA monitoring/Terms acknowledgement is authorized | 62,359 mortgages originated 2013–2024 with quarterly performance through 2025Q3; survey selection, weights, quarterly censoring, and source-specific target must be audited; never relabel or pool as Freddie vintage |
| S28 FHFA Enterprise PUDB | Separate acquisition/credit-access composition workspace; no D01 model role | Official annual Census Tract file, dictionary and record-count workbook; 2025 pilot acquired and profiled | 2,093,767 2025 acquisitions, borrower/tract characteristics; no payment performance or applicant-denial denominator. Historical annual comparisons require release-matched dictionaries and explicit schema/geography review; see `docs/FHFA_PUDB_CREDIT_ACCESS_REVIEW_VI.md` |
| S29 HUD FHA Insurance in Force by Tract | Separate FHA geographic-exposure/concentration panel; no D01 model role | Download official HUD ArcGIS CSV; aggregate only by state in the app | 85,154 unique 2010 Census tracts; 7,683,397 active FHA-insured loans across nonblank cells. `-4` is undocumented and excluded; publisher coverage metadata conflicts (2025-03 vs 2021-09); no performance/denial outcomes; see `docs/HUD_FHA_IIF_TRACT_REVIEW_VI.md` |
| S12 HMDA / S03 Fannie MF | Case D08/D09 mở breadth của P2 | Sau D01; workspace chung, pipeline và target riêng | Không ghép identity hoặc outcome vào Freddie loans khi thiếu link đáng tin |

Freddie công bố đường tải qua Clarity và các layout/guide theo release; dữ liệu lịch sử có thể được sửa lại. Kế hoạch ưu tiên **official annual samples**, giữ quyền truy cập và version, thay vì crawler vào các trang giới thiệu sản phẩm. [Freddie SFLLD](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset).

NSMO là nguồn bổ sung riêng có hiệu suất mortgage thực, nhưng PUF có sample frame/selection và tần suất quan sát khác; chỉ dùng như case riêng hoặc external-cohort study sau target audit. Đã tải technical documentation/codebook chính thức và lưu tại `docs/D01_NSMO_SOURCE_REVIEW_VI.md`; chưa lấy microdata vì FHFA yêu cầu người dùng đồng ý monitoring/Terms trước khi truy cập.

**Acquisition sequence:** kiểm tra 2012 → pilot một vintage train khác, chẳng hạn 2008 nếu file hợp lệ → profile schema/event/footprint → lần lượt qualify các năm mà protocol cần → mở các partition sau. Trước khi chạy model vẫn phải có đủ bộ dữ liệu cần cho protocol đã chốt. Một pilot 2008+2012 chỉ giải quyết engineering/coverage, chưa giải quyết calibration/validation/OOT.

Không xem outcome của final-test cohort để chọn features, thresholds hoặc vintage có kết quả đẹp. DQ/support audit của cohort đó phải giới hạn, có log và tách khỏi model selection; việc đã xem counts cũng cần được ghi trong study history. Nếu protocol hiện có không khả thi do support, viết revision có lý do từ coverage trước khi fit; không lấp bằng random split.

Snapshot Freddie đọc từ release hiện nay chưa chứng minh các field đã công bố tại ngày lịch sử. Claims ban đầu là **retrospective temporal validation using latest source release**. ALFRED as-of đúng cho macro cũng không tự biến mortgage source thành archive point-in-time.

<a id="chuong-47-6"></a>

### 47.6. Storage, ngân sách máy và nguyên tắc mở rộng

Đo máy ngày 08/10/2026 trong lượt này: Intel i5-9500; physical RAM 25.709.551.616 bytes, khoảng **23,94 GiB**; D: còn khoảng **85 GiB** tại thời điểm kiểm tra. Free space thay đổi theo các tác vụ khác. Không lấy kích thước ZIP 2012 khoảng 70,5 MB trong repo để suy ra tổng raw+staged+Parquet+temp+artifacts sẽ nhỏ tương ứng.

Toàn bộ code, data, scratch và exports mới nằm dưới **D:\data\Codex**. Đường repo local sẽ xác định ở M01-001; nếu cần tạo mới, đường đề xuất là `D:\data\Codex\credit-atlas`. Đây là đường thiết kế, chưa tạo checkout trong lượt này. Dataset private đặt ở thư mục riêng thuộc D:, được ignore và không đi vào app bundle.

Budget khởi điểm đề xuất, kiểm tra lại sau pilot:

- Mỗi lần qualify một hoặc hai vintage; đo source ZIP, staged files, canonical tables, peak RSS, DuckDB spill và wall time.
- Ngưỡng tài nguyên đề xuất: tiến trình analytics peak khoảng 8–12 GiB và DuckDB temp có budget khoảng 10 GiB; pin thực tế sau benchmark. Đây là lựa chọn cấu hình dự kiến, chưa là kết quả chạy.
- Giữ ít nhất khoảng 25 GiB D: trống làm headroom; đạt ngưỡng thì tạm dừng acquisition/large run và lập phương án storage cụ thể. Không tự xóa các run cũ hoặc dữ liệu khác để lấy chỗ.
- Khởi đầu budget tổng mới 20–35 GiB rồi điều chỉnh theo pilot. Cần nguyên bản ZIP, một canonical snapshot chính, frozen aggregate/report artifacts và receipt; tránh tạo nhiều bản full panel cho mỗi model.
- Chạy bounded-memory/SQL column projection theo partitions; không load mọi loan-month thành một pandas DataFrame hoặc tạo nhiều fit processes cùng lúc.

Runtime và kích thước final case chỉ được chốt sau R0/pilot. Mục tiêu tối ưu là tái tạo được bằng máy hiện có trước khi quyết định dịch vụ cloud.

<a id="chuong-47-7"></a>

### 47.7. Kiến trúc kế thừa: một domain engine, một cách tính

**Reuse `crsl` làm mortgage domain engine sau audit.** Canonical, label, transition và loss calculations hiện có là ứng viên kế thừa. CreditAtlas bổ sung shared run/evidence contracts và workspace UI; không duy trì hai pipeline tính D3/loss khác nhau cho hai website.

Trình tự tích hợp:

1. Pin commit và dependencies của repo hiện tại; kiểm tra code/artifact map trước khi chọn extraction scope.
2. Chạy domain CLI với snapshot riêng, lấy immutable artifacts/manifest làm giao diện đầu ra.
3. Viết adapter giữa aggregate/report contract của `crsl` và CreditAtlas; giữ source semantics trong domain package.
4. Chỉ chuyển hoặc đóng gói code sang monorepo khi clean rebuild và parity đã đạt. Dữ liệu private vẫn có paths/manifests riêng.
5. Dùng D02 sau này để kiểm chứng phần nào thực sự chung; chưa tạo universal feature/default engine từ một domain.

~~~mermaid
flowchart LR
    A["Official snapshots trên D:"] --> B["Source contracts và hash checks"]
    B --> C["crsl: canonical / labels / marts"]
    C --> D["Frozen aggregate + evidence contract"]
    C --> E["Qualified splits / features / models"]
    E --> D
    D --> F["CreditAtlas P2 workspace"]
    F --> G["Findings / review / reproducible exports"]
~~~

Đây là sơ đồ triển khai dự kiến. Nếu snapshot hoặc contract chưa qualified, dependent model stage trả trạng thái unmet và không sinh prediction artifacts.

Stack giữ nền đang có: Python ≥3.12; repo pin DuckDB 1.5.5, PyArrow 22.0.0, scikit-learn 1.8.0 cho optional model dependencies. Phiên bản này được đọc từ [pyproject.toml](https://github.com/susayold/credit-risk-strategy-lab/blob/master/pyproject.toml), không phải đề nghị tự động nâng lên phiên bản mới. Tái tạo môi trường cũ trước; kiểm tra tương thích nếu sau đó thay pins, đặc biệt custom JSON-tree persistence phụ thuộc layout của scikit-learn.

Analytics dùng Parquet + DuckDB; immutable file manifests làm registry trước. CreditAtlas lâu dài theo [kiến trúc 38.4](D:/data/Codex/research/credit-risk-master/2026-10-08/CREDIT_RISK_MASTER_RESEARCH.md#chuong-38-4), FastAPI và React là các lựa chọn đã đề xuất, nhưng R0 phải đọc stack website hiện có để quyết định reuse components. R1 có thể hoàn thiện trên website sẵn có và adapter aggregate trước khi port UI. Chỉ thêm API khi có nhu cầu drill-down/private query thực; chưa cần PostgreSQL, Redis, MLflow services hoặc orchestration riêng để có MVP local.

<a id="chuong-47-8"></a>

### 47.8. Contracts và tables: giữ grain, version và availability

Tên chung `loan_static/loan_monthly` ở charter 44.1 là tên logic. Khi kế thừa repo, **giữ `dim_loan` và `fact_loan_month`**; CreditAtlas mapping sang contract chung qua adapter, tránh rename toàn codebase chỉ để đồng nhất từ ngữ.

| Dataset/artifact | Grain | Nội dung bắt buộc | Acceptance chính |
|---|---|---|---|
| Source manifest | Một asset / snapshot / release | URL, hash, retrieval time, layout hash, sample type/year, rights record | Source/release rõ, private payload không lọt repository |
| `dim_loan` | source + release + loan | Origination fields, source/raw provenance, source vintage, acquisition/first-payment | Unique keys; percentages/null/enum đúng dictionary |
| `fact_loan_month` | source + release + loan + report_month | Numeric delinquency, balance/rate, REO, termination, modifications, loss fields có sẵn | Duplicate/gap/sentinel/enum checks; valid parent loan |
| Observation audit | Loan + entry contract version | First observation, ages, exclusions, coverage, structural missingness | Eligibility không sử dụng tương lai; population totals reconcile |
| Labels | Loan + landmark + target version | Event/horizon, outcome, competing/censor status, known month | Mỗi kết quả có trace tới future window hợp lệ |
| Episodes/events | Loan + episode/event ID | First D3, cure confirmation, redefault, termination/gaps | Không backdate cure; terminal uniqueness và tie rule rõ |
| Split manifest | Loan + study version | Role, label availability, cutoffs, exclusions, lock/access history | Không overlap loan; immature rows không vào fitting |
| Feature/model artifacts | Study + model + cohort/landmark | Allowlist, encoder fit provenance, hashes, scores/calibration khi qualified | Train-only transform; same-cohort models; preserved order |
| Aggregate marts/report package | Run + metric + dimensions | Counts, UPB, valid/support denominators, null reasons, lineage | UI/Excel/report lấy cùng metric contract và snapshot |
| Findings/review record | Finding/case + run reference | Evidence refs, rationale, author/time, status/history | Lưu được và mở lại; không thay đổi underlying frozen metrics |
| Scenario artifact, optional | Scenario + origin + horizon + model | Assumptions/path versions, output kind, validation purpose | Tách giả định khỏi observed/predictive results |

Header chung: `data_snapshot_id`, `source_release`, `run_id`, `code_commit`, `target_version` nếu có, `economic_as_of`, availability evidence/status, unit/currency/balance basis, population và permitted use. Giữ riêng **nguồn observed**, **method/model status**, **assumption mode**; một badge observed-data không đồng nghĩa mô hình đã validated.

Không nối các release của cùng source như independent loans; adapter phải chọn snapshot/release hoặc làm revision analysis rõ. Key private source IDs dùng cho processing; drill-down nội bộ có pseudonymous ID. Pseudonym không tự cho phép public row-level release.

<a id="chuong-47-9"></a>

### 47.9. Target contract đầu tiên: giữ early-entry D3 trước prepayment/maturity

**Target chính R3 là contract đang có trong repo: first-observed early-entry 12-month D3 event before prepayment.** Product label nên dùng tiếng Việt: “rủi ro vào trạng thái D3 trong 12 tháng đầu quan sát, trước prepaid/matured”. Source termination `01` gộp prepaid và matured, vì vậy phần mô tả UI phải nêu cả hai. Chưa gọi kết quả là contractual-origination PD hoặc regulatory-default probability.

| Thành phần | Quy định kế thừa / cần đóng băng |
|---|---|
| Landmark t | Tháng performance đầu tiên thực sự quan sát trong source |
| Entry population | Source age và contractual age ở mức 0–1, khớp chính xác theo contract; loại entry đã modified, severe/REO, unknown hoặc terminal |
| Contractual age | `report_month - first_payment_month + 1` theo tháng; giữ khác biệt với origination/acquisition year |
| Window | t+1 tới t+12 inclusive; không đưa entry month vào future target |
| Positive | First numeric delinquency `03`–`99` trong window, với path liên tục/known tới event |
| Negative: không event | Quan sát đủ 12 tháng liên tục và không đạt numeric D3 |
| Negative: competing prepay | Prepaid/matured trước D3 theo estimand hiện có; có competing flag, không diễn giải là latent good nếu khoản vay tiếp tục sống |
| Unknown/censored | Gap/unknown trước khi xác định; hết dữ liệu khi chưa classifiable; không tự đổi thành negative |
| Other exit | Credit/other termination hoặc REO trước numeric D3, chưa có event đủ định nghĩa: giữ outcome unavailable cho binary target này |
| Tie cùng tháng | Numeric D3 ưu tiên theo monthly tie rule; không chứng minh thứ tự intramonth |
| Label-known month | Khi đủ bằng chứng outcome trong reconstruction; lọc theo fit cutoff; không tự là historical publication timestamp |
| Relief segment | Giữ flag và diagnostic riêng; không tự loại, không dùng như shortcut feature chưa qua review |

Các quy tắc này đến từ [observation and censoring contract](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/methodology/observation-and-censoring.md). Điểm dễ nhầm là **prepay trước D3 được gán 0 có chủ ý trong estimand event-before-prepayment**, còn censored/unknown không được gán 0. Một target “default nếu khoản vay không prepay” là câu hỏi khác, không được suy ra từ nhãn đang có.

Bảng reconciliation mà clean rebuild phải kiểm tra với snapshot hiện có:

~~~text
50.000 loans
  = 48.066 eligible + 1.919 not-early-entry + 15 terminal-at-entry
48.066 eligible
  = 45.241 complete/no-event + 102 D3 + 2.641 prepaid/matured + 82 other exits
47.984 endpoint-available
  = 47.882 negative + 102 positive
2.016 unavailable/ineligible
  = 1.919 + 15 + 82
~~~

Đây là expected reference của repo, không phải kết quả mới chạy. Mọi khác biệt khi dùng release/snapshot khác phải xuất được exclusion/revision ledger; không ép totals khớp bằng cách sửa target. Event-support table cần positive/negative/censored/other exits theo vintage, partition, Relief và features available, thay vì chỉ một tổng 102.

**Behavioral rolling 12m là extension riêng.** Nếu sau này muốn score tại một tháng t sau entry, phải có contract riêng cho eligible states, history, prior D3/episodes, horizon và weights. Không đem behavioral score so với early-entry score trên hai population/targets khác nhau rồi chọn model tốt hơn. M01-X02 sẽ audit contract đã có trong repo trước khi mở nghiên cứu này.

<a id="chuong-47-10"></a>

### 47.10. Các semantics bắt buộc giữ từ source dictionary

| Dữ liệu | Cách xử lý đúng trong plan | Lỗi mà acceptance phải bắt |
|---|---|---|
| Delinquency `00/01/02/03–99` | Map CURRENT/D1/D2/D3PLUS theo source code | Nhân code với 30 để dựng số ngày quá hạn chính xác |
| `RA` / `XX` | REO / UNKNOWN trên axis riêng | Coerce thành delinquency integer hoặc negative outcome |
| Zero-balance code `01` | PREPAID_OR_MATURED | Gọi mọi exit là voluntary refinancing |
| Codes `02/03/09` và `15/16/96` | Credit termination / other termination riêng theo release | Mặc định whole-loan sale là default |
| Rates, DTI, LTV/CLTV, MI, ELTV | Source lưu percentage points; đổi sang fraction có chỉ dẫn ở consumer | Tính 80 thành 0,008 hoặc nhân tỷ lệ hai lần |
| FICO/VantageScore `9999` | Canonical null; valid score range đúng dictionary | Đưa 9999 vào scaling hoặc xem là high score |
| DTI/LTV/CLTV/MI/ELTV `999` | Sentinel theo field; MI 0 và DTI 0 có thể valid | Một quy tắc replace 999 cho mọi dollar field |
| VantageScore/ELTV/valuation method | Kiểm tra coverage theo thời gian; 2012 VantageScore toàn sentinel | Giữ feature không có thông tin rồi diễn giải coefficient/importance |
| Relief/HARP | Relief flag của nguồn; HARP subset theo logic/documentation | Coi Relief đồng nghĩa HARP hoặc infer missing DTI là thiếu thu nhập |
| Loss và recoveries | Signed components theo release; missing khác 0; negative values giữ nếu valid | Clipping hết loss/recovery âm hoặc dùng sign từ layout cũ |
| Geography/borrowers/assistance | Giữ conditional availability và definition changes | Xem pre-2018 borrowers=2 là chính xác hai người; coi structural missing là borrower risk |

Source authority: [canonical dictionary](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/data_dictionary/canonical.md) và [ADR-002](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/decisions/ADR-002-source-semantics.md). R0/R2 phải đối chiếu trực tiếp code, source layout và raw edge rows; tài liệu được đọc chưa thay cho validation parser.

Rule thất bại nghiêm trọng như duplicate grain, enum chưa biết, post-terminal path bất hợp lý hoặc join fanout phải tạo failure report và dừng dependent stage. Missing thuộc đặc tính nguồn được giữ thành null + reason; nó không tự làm hỏng toàn bộ dữ liệu.

<a id="chuong-47-11"></a>

### 47.11. Feature plan và temporal protocol

**Origination-feature baseline** kế thừa strict allowlist hiện có: Classic FICO, original DTI, original LTV/CLTV, original UPB, original term, dwelling units; categorical occupancy, purpose, property type, first-time-homebuyer. Missing indicators; median imputation/scaling và category vocabulary fit trên train only. Chưa dùng future delinquency, current/terminal balance, actual loss, future modifications hoặc label dates làm predictors.

Loan IDs/private geography không là model inputs. Original interest rate, seller/channel, Relief/HARP và field thay đổi definition chỉ xét ở ablation đã định nghĩa khi đủ availability; model baseline không tự thêm mọi numeric column. Entirely missing feature được loại/ablate trong research dù engineering encoder có thể xử lý nó để tránh crash. [Feature catalogue](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/feature-catalogue.md).

Candidate protocol đã có trong repo:

| Partition | Origination vintages dự kiến | Information/fit boundary | Mục đích |
|---|---|---|---|
| Train | 2006–2012 | Initial fitting 01/2014; label-known month phải trước cutoff | Fit preprocessing/model và bounded training-only candidate selection |
| Calibration | 2014 | Calibration fitting 01/2016; labels phải known trước cutoff; scoring landmark không sớm hơn upstream fit | Fit calibration; không tune threshold/champion bằng final test |
| Validation | 2016 | Selection freeze 01/2018; labels phải known trước cutoff; landmarks phù hợp upstream fit | Chọn cấu hình/rubric sau train-only selection; đánh giá stability |
| Final test | 2018 | Scoring sau freeze và valid landmark; evaluation chỉ sau đủ horizon | Một lần đánh giá cuối với model, target, cohort và thresholds đã frozen |

Đây là **candidate protocol, chưa research-approved trong repo**. R2 phải rà soát ngày thực của từng loan; origination year chỉ phân role, không tự đảm bảo observation/label timing. Source first observation có thể muộn hơn nhiều so với origination year. Những vintage nằm ngoài schedule giữ trong audit với role unused hoặc extension, không tự đưa vào training.

Model-B behavioral có repeated landmarks nên cần protocol riêng: outer partitions tách loans, label-known cutoff, spacing/history, weights và clustered evaluation rõ. Bắt buộc chốt shared-loan protocol trước fitting; chưa để target này mở rộng số hàng train nhằm bù event support của early-entry.

Gate R2 tối thiểu:

1. Nguồn, layout, rights, canonical integrity và target reconciliation đạt trên các vintage cần thiết.
2. Không overlap loan giữa partitions; preprocessing chỉ fit trên included train; final-test accesses có log.
3. Labels đủ known/mature trước đúng cutoff; same-month cutoff không tự được tính là đã biết trước fit.
4. Đo event counts, uncertainty và subgroup support. Repo có guardrail phát triển ≥100 positive/100 negative mỗi partition; **không coi đó là chứng minh sample size đủ** cho model phức tạp hoặc mọi segment.
5. Protocol revision/selection history được lưu; model readiness chỉ bật sau các checks đã chốt. Censored exclusions và quần thể mất do missing features phải báo riêng.

Nguồn: [validation protocol](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/methodology/validation-protocol.md). Dataset release có follow-up tới 03/2026 ở lần đối chiếu này; nếu thêm recent vintage, audit maturity theo từng landmark. Không dùng một năm hiện đại chỉ để dashboard trông cập nhật khi outcomes chưa đủ horizon.

<a id="chuong-47-12"></a>

### 47.12. Model plan: baseline, challenger, calibration và lựa chọn cuối

| Thứ tự | Model/method | Mục đích | Điều kiện và output |
|---|---|---|---|
| 1 | Constant event-rate baseline | Đo mức risk và giá trị vượt dự đoán không phân biệt loans | Fit train; giữ calibration/validation/OOT scores cùng cohorts |
| 2 | Logistic regression | Baseline dễ audit cho target early-entry 12m | Feature allowlist, bounded regularization menu; save encoder/coefs/version |
| 3 | Histogram gradient boosting đã có trong repo | Challenger phi tuyến trên cùng feature/target/population | Candidate menu nhỏ, train-only selection; version-pinned persistence/parity |
| 4 | Calibration | Sửa probability fit nếu đủ support | Fit separate common calibration cohort; raw/calibrated results đều giữ |
| 5, optional | Discrete-time hazard / competing-risk covariate model | Mô tả timing và joint event probabilities | Contract risk sets/exit/censoring riêng; horizon outputs reconcile |

Candidate configuration trong repo đã có nhưng chưa là tuned/validated model. Audit và reuse comparison runner trước, không cài thêm nhiều boosting libraries để tăng danh sách thuật toán. Deep sequence model chưa nằm trong critical path của D01 đầu tiên.

**Training selection:** chốt trước một menu nhỏ regularization/tree complexity; temporal folds nằm trong train và respect label availability. Không dùng internal random monthly split làm validation chính. Giữ kết quả cả candidates thất bại hoặc inferior; tính budget fit/RAM trước run.

**Calibration:** ưu tiên identity/no-calibration reference và một sigmoid calibration candidate; isotonic chỉ xem khi sample/support cho phép và được predeclare. Chọn method theo protocol qua validation, không chọn sau final test. Class weights hoặc resampling nếu nghiên cứu thêm phải ghi ảnh hưởng tới probability base rate và calibration; không tự SMOTE loan-month rows.

**Rubric chọn model:** threshold chấp nhận về calibration/discrimination/utility/stability phải định nghĩa và đóng băng trước final test. Challenger chỉ được chọn nếu lợi ích có support và uncertainty hợp lý, không có deterioration quan trọng về calibration, vintage/segment stability và reproducibility. Nếu evidence không rõ, giữ logistic hoặc kết luận chưa có champion; không buộc model phức tạp thắng.

Không tuyên bố hệ số là causal borrower behavior. Origination-feature model quan sát ở early entry vẫn chịu source revisions và booked/acquired-loan selection; nó không chứng minh rejection inference hay khả năng underwriting toàn bộ applicants.

<a id="chuong-47-13"></a>

### 47.13. Validation report: đo gì và tránh kết luận quá tay?

| Câu hỏi | Metrics/evidence cần có | Cách đọc |
|---|---|---|
| Ranking có ích không? | ROC-AUC, PR-AUC và event prevalence; risk bands với event counts | PR-AUC phải đọc cùng base rate; overall metric có thể bị mix chi phối |
| Probability đúng mức không? | Brier/log loss, calibration-in-the-large, slope/reliability plots nếu đủ support | Hiển thị uncertainty; sparse bins giữ counts/intervals, không vẽ đường trơn giả chính xác |
| Có ổn định qua thời gian không? | Metrics theo vintage/period; feature/missingness/category drift | Drift flag dẫn tới investigation, không tự chứng minh model thất bại |
| Có bị Relief chi phối không? | Support và metrics Relief/non-Relief, ablations đã predeclare | Với 13 positive non-Relief hiện tại chưa đủ để kết luận subgroup calibration mạnh |
| Screening nghiên cứu có gì? | Fixed cutoff risk, retained count/principal, concentration và paired differences | Đây là retrospective retained-cohort analysis, không actual approval rate hay causal savings |
| Uncertainty có đáng tin không? | Loan bootstrap cho aggregates/repeated landmarks; paired comparisons cùng loans | Nêu cách resample, support và interval; cả vintage shocks không được bootstrap loans xóa đi |
| Serving có đúng model đã đánh giá? | Batch/query/native-vs-artifact parity, hashes/feature ordering | Tránh UI dùng scores từ run hoặc encoder khác |

Confidence level và bootstrap repetitions được chốt trong protocol/config; bắt đầu bằng bounded budget theo benchmark, không cứng nhắc một con số lặp cho mọi bảng. Khi chỉ có một vài vintage, cần report thời gian/segment cụ thể và limitations; bootstrap từng loan không chứng minh generalization sang chu kỳ khác.

Mỗi model comparison phải dùng cùng target version, loan IDs, feature contract, outer split và calibration population; nếu models nhận inputs khác thì đó là một study riêng cần giải thích. Report giữ raw/calibrated metric sets và exclusions rõ, không chỉ bảng “best AUC”.

Final-test process: freeze code/model/data/target/rubric/thresholds → ghi access receipt → score đúng cohort → sinh report → giữ cả kết quả không tốt. Sau final test, tuning thay đổi cần study version và evaluation plan mới, không sửa quietly rồi gọi cùng test untouched.

<a id="chuong-47-14"></a>

### 47.14. Transitions, vintage, competing events và episodes

**Monthly stock:** counts và balances của active states tại report month. **Incidence:** first events trong cohort với risk set/maturity rõ. **Transition:** chỉ adjacent known observations hợp lệ. Ba metric families có mẫu số khác nhau; UI có metric tooltip và denominator panel để không so như cùng một rate.

Transition acceptance:

- Mỗi pair là loan/t → loan/t+1 khi hai tháng liên tiếp theo calendar; gap không được nối tắt.
- Source state và terminal axis được lưu riêng; terminal handling explicit, không tạo giả “cure” vì zero balance.
- Count matrix dùng eligible pair count; balance matrix dùng opening principal của pairs có balance hợp lệ; missing-balance counts giữ riêng.
- Row sums reconcile với valid transitions của row; pooled segments khớp tổng và bảo toàn loan counts/UPB đúng basis.
- Heatmap cho phép mở numerator, denominator, distinct-loan support, time window và evidence refs.

Cure/redefault acceptance: one-month cure riêng; sustained cure chỉ confirmed ở **tháng current thứ ba liên tiếp** sau D3 episode, không backdate về tháng đầu; unknown/gap phá episode continuity; redefault là D3 sau confirmation. Loan bootstrap tôn trọng repeated episodes; tỷ lệ redefault dùng cohort đã sustained cure và đủ follow-up, không toàn active book.

Vintage/competing evidence: giữ event ledger và observation status, curves 6/12/24 tháng với maturity/risk-set masks; D3, prepaid/matured và other exits trong cùng framework. Event probabilities phải nhất quán với survival/risk sets, không cộng hai độc lập classifiers rồi gọi joint distribution. Censoring cần estimand/method assumptions rõ, nhất là source gaps và other exits; unavailable label không có nghĩa unavailable mọi descriptive view.

R1 kế thừa descriptive competing-event curves hiện có sau reconciliation. Một covariate survival/competing-risk model là extension, không cần fit để dashboard có vintage analysis.

<a id="chuong-47-15"></a>

### 47.15. Loss plan: descriptive bridge trước severity/LGD

R1 xử lý **observed loss components**. Bản loss page phải cho biết population terminal được chọn, component coverage, balance basis, thời điểm observations và resolved/unresolved. Numeric D3 target ở 47.9 không tự quyết định loan nào có complete loss data.

Trình tự:

1. Audit một-terminal-per-loan rule, post-terminal repeats, disposition/defect dates và lựa chọn authoritative terminal record theo source.
2. Giữ raw components, signed values và missing reasons; dùng công thức theo Release 47, có source-field mapping.
3. Independent recomputation của bridge từ raw terminal records; kiểm tra zero/negative/missing edge cases và các trường hợp exception được ghi.
4. Tổng component bridge đối chiếu reported loss trên rows đủ components; report residual, unavailable count và unresolved coverage riêng.
5. Phân nhóm loss theo event/vintage/Relief/available fields trong scope support; tránh gọi resolved-only mean là expected loss cho toàn bộ loans.

ADR repo ghi 374 reported-loss rows match signed components, sáu trường hợp thiếu defect dates và một recent disposition. Đây là reference cần tái kiểm tra, **không phải 374 independent complete training labels đã đủ cho severity model**. B18 hiện vẫn dưới model-support gate và expected-loss dollars chưa available. [ADR-002](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/decisions/ADR-002-source-semantics.md), [block status](https://github.com/susayold/credit-risk-strategy-lab/blob/master/block-status.md).

Severity/LGD chỉ mở sau multi-vintage qualification, recovery completion/time-to-resolution audit và balance/default denominator được chốt. Negative net losses hoặc ratios ngoài khoảng 0–1 có thể có nghĩa theo components; không clipping để làm distribution đẹp. Chưa lấy `D3-risk × resolved mean loss` làm accounting ECL hay lender P&L.

<a id="chuong-47-16"></a>

### 47.16. Macro, forecast và stress: mở từng bước có bằng chứng

Repo đã có adapter cho UNRATE, USSTHPI và MORTGAGE30US, kiểm tra revisions/units/staleness và join không fanout. R1 có thể hiển thị retrospective context khi nguồn cho phép; predictive macro fit là extension sau source acquisition thật.

As-of plan kế thừa convention của repo: cutoff là đầu ngày, sử dụng knowledge tới ngày trước; giữ `reference_period`, `realtime_start/end`, revision và availability status. Không tự dùng latest series khi historical vintage request thiếu; không interpolate annual/quarterly tới loan-month rồi gọi dữ liệu observed monthly. [Macro availability contract](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/methodology/macro-availability.md). FRED có real-time parameters để truy xuất knowledge theo thời gian. [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).

FHFA regional HPI chỉ là context. Nếu tạo proxy current property value hoặc proxy LTV bằng index ratio, output phải ghi giả định base value/geography/quality và là proxy; thiếu đúng original valuation basis thì không tạo. Latest HPI series không có archival publication evidence dùng cho descriptive context, không đưa ngược vào earlier prediction. [FHFA HPI datasets](https://www.fhfa.gov/data/hpi/datasets).

Optional forecast/stress sequence:

1. Naive carry-forward và transition-based projection đã có engineering components; audit input maturity và mass conservation.
2. Rolling-origin backtest bằng vintages/periods đủ mature; train/filter/calibrate đúng origin, compare baseline và uncertainty.
3. Chọn một scenario path có units/horizon/mapping/assumptions versioned; nghiên cứu sensitivity trước khi kết luận response model.
4. Chỉ gọi scenario stress output khi model/input qualification và limitations đã rõ. Future actual macro path là oracle retrospective sensitivity nếu dùng, không normal forecast.

Với fixed-rate loans, mortgage market rate không tự reset coupon. Loan-level employment, current individual house valuation hoặc causal recovery effect chưa có từ national series. Một scenario “HPI giảm 20%” có thể là sensitivity assumption được ghi; không tự có phép tính “PD tăng 2 lần” nếu chưa ước lượng hoặc đặt tên assumption đúng.

<a id="chuong-47-17"></a>

### 47.17. App journey: màn hình, actions và dữ liệu hiển thị

| Màn hình | Nội dung chính | Action hữu ích | Acceptance |
|---|---|---|---|
| Overview / readiness | Dataset scope, metric headlines, implemented/evidenced/qualified status | Chọn run; mở lý do unmet và findings | Badges đúng status; numbers đến từ frozen contract |
| Sources & quality | Release, vintages, joins, missingness, exclusions, footprint | Lọc vintage/field/check; mở evidence refs | Null khác zero; failure và structural availability dễ đọc |
| Portfolio & vintage | Monthly stock, count/UPB, Relief/product mix, incidence/competing curves | Lọc cohort; đổi count/balance; so vintage khi đủ coverage | Metric definition, denominator, support và horizon đi cùng chart |
| Transitions & lifecycle | Heatmap, roll paths, loan timeline, cure/redefault episodes | Chọn pair/cell; mở timeline private hoặc aggregate drill-down | Không nối gaps; episode confirmation đúng; selected run giữ xuyên drill-down |
| Models & validation | Target, features, support, split, raw/calibrated metrics, reliability và OOT | So frozen models; mở model card và limits | Unqualified model có trạng thái rõ; không hiện giả risk score |
| Loss & coverage | Signed loss bridge, resolved/unresolved, dates/components | Lọc terminal cohort; xem component exceptions | Denominator/balance basis đúng; missing loss không thành 0 |
| Evidence & review | Methodology, run lineage, findings, comments/history, export | Lưu finding, đánh dấu review status, mở lại case và download allowed report | Record persist; report gắn đúng run/target/filter và giới hạn |

User journey MVP: **chọn frozen run → xác nhận coverage → chọn cohort → nhìn monthly stock/vintage → mở transition/episode → xem loss coverage → lưu finding với evidence refs → xuất research memo**. R3 thêm bước xem model/calibration và prediction trên eligible population. Một dashboard chỉ có chart mà không truy được mẫu số, run hoặc lưu findings chưa đạt hành trình này.

Private loan drill-down chỉ mở từ local/private data service có controls. Nếu chỉ dùng static aggregate frontend, drill-down là segment/cell evidence; không bundle loan panel vào browser. Public-safe demo chỉ hiện nguồn/data có thể xuất và aggregates đã rà soát; source rights có thể hạn chế cả derived output nên aggregate không tự đồng nghĩa public.

Filters gồm snapshot/run, origination vintage, report/entry month, Relief segment, product, metric basis và horizon khi phù hợp. URL/state lưu lựa chọn không chứa raw loan IDs. Export giữ filter state, definitions, code/data versions và excluded/missing counts. Review states ban đầu là draft → reviewed → archived, có lịch sử; đó là review nghiên cứu, không certification hay approval cho vay.

Lỗi người dùng cần thấy: snapshot unavailable; field unavailable ở vintage; cohort ít support; outcome chưa mature; model chưa qualified; export không được phép. Mỗi trạng thái nói rõ nguyên nhân và dữ liệu còn dùng được. UI không cần hiện internal parser/SQL details ngoài evidence view dành cho analyst/reviewer.

<a id="chuong-47-18"></a>

### 47.18. Backlog triển khai: 30 công việc với dependencies và nghiệm thu

Các ID dưới đây là backlog triển khai, **chưa là task đã thực hiện**. R1 dùng snapshot 2012 đã qualified/rebuilt; cùng task labels/marts tiếp tục chạy cho multiple vintages ở R2. Dependencies là evidence đầu vào, không yêu cầu viết lại những component đã có và đạt audit.

| Task | Đợt / phụ thuộc chính | Công việc và artifact bàn giao | Nghiệm thu |
|---|---|---|---|
| M01-001 | R0; đầu tiên | Inventory repo/commit, local raw/artifacts, website và docs; capability-gap map | Phân biệt code có, result có, status claimed và result tái chạy; tìm đúng loan-performance data |
| M01-002 | R0; 001, 004 | Clean rebuild 2012 từ immutable source; environment/run receipts | Pipeline chạy theo dependencies; output totals/hashes đối chiếu và differences được giải thích |
| M01-003 | R0; 001–002 | Audit semantics/code và meaningful regression checks | Status/sentinels/percentage/age/terminal/loss boundaries đúng official contract; failures không lọt downstream |
| M01-004 | R0; 001 | Source manifest, private paths/ignore rules, footprint benchmark | Raw/private artifacts trên D:, không trong bundle/git; resource budget có measurement |
| M01-005 | R2 có thể bắt đầu sớm; 001, 004 | Acquire/pilot official additional annual samples khi access/terms hợp lệ | Đúng annual sample/release/hash; parser profile và disk/RAM receipt từng batch |
| M01-006 | R2; 003, 005 | Multi-vintage canonical tables và source-layout compatibility report | Key/row/parent/fanout checks; structural availability theo vintage |
| M01-007 | R2; 006, 009 | Support matrix và source/target qualification memo | Positive/negative/unknown/censored/Relief support theo cohorts; kết luận purpose readiness có căn cứ |
| M01-008 | R1/R2; 002–003 | Freeze target/entry/exit/censor/tie contract và version history | Giữ early-entry estimand; mọi edge case có lý do kết quả |
| M01-009 | R1/R2; 008, 002 hoặc 006 | Label/exclusion ledger trên canonical run | Population/outcome totals reconcile; immature/unknown không thành good; release differences có trace |
| M01-010 | R1/R2; 002, 009 | Portfolio anatomy/stock mart và findings memo | Counts/UPB, monthly states và cohort filters đối chiếu độc lập |
| M01-011 | R1/R2; 003, 002 hoặc 006 | Adjacent transition marts theo count/balance/Relief/time | Chỉ adjacent valid months; matrix totals/denominators/missing balance khớp |
| M01-012 | R1/R2; 008, 011 | Cure/redefault episode ledger và summaries | Third-current confirmation không backdate; gaps/terminal phá continuity; follow-up rõ |
| M01-013 | R1/R2; 009–010 | Vintage competing-event curves 6/12/24m và uncertainty | Risk sets, maturity, exits và first events reconcile; loan clustering đúng |
| M01-014 | R1/R2; 003, 002 hoặc 006 | Observed loss bridge, unresolved/component coverage | Signed formulas từ raw đối chiếu; một terminal/loan; missing và negative values đúng nghĩa |
| M01-015 | R2; 007, 009 | Research split/protocol revision, maturity exclusions, final-test access log | Required vintages/support/timing đủ; no loan overlap; freeze/access workflow thực thi |
| M01-016 | R2; 003, 015 | Feature allowlist/encoder audit và ablation plan | Train-only fit, missing/unseen buckets, no future features; feature coverage chốt |
| M01-017 | R3; 015–016 và research gates | Actual constant/logistic development runs | Frozen included loans và train/calibration/validation receipts; fitted artifacts reproducible |
| M01-018 | R3; 017 | Bounded boosting challenger và persistence/parity audit | Same target/cohort/features; reviewed library version; native/loaded inference reconcile |
| M01-019 | R3; 017–018 | Calibration, reliability/uncertainty và segment/time metrics | Raw/calibrated results cùng cohorts; no calibration fit trên validation/test; sparse support hiển thị |
| M01-020 | R3; 019 | Apply predeclared rubric; freeze model/thresholds/study | Không auto champion theo AUC; inferior candidates/limits được giữ; final-test chưa dùng selection |
| M01-021 | R3; 020 | Final OOT scoring và evaluation report | Access/run log; model/config frozen; kết quả giữ nguyên cả khi không tốt |
| M01-022 | R1/R3; relevant 010–014, model outputs sau 021 | CreditAtlas adapter và typed aggregate/evidence/export contract | Cùng run/schema/definitions; không raw IDs; unsupported PD/ECL/CF uses bị từ chối |
| M01-023 | R1; 022 | Workspace navigation, snapshot/filter state và status views | Một flow dùng được; selection không trộn artifacts; snapshot unavailable có lý do rõ |
| M01-024 | R1/R3; 023 và relevant marts | Portfolio/vintage/transition/loss/model screens | Denominators/support đi cùng charts; displayed totals khớp contract; model gates đúng |
| M01-025 | R1/R4; 023 | Persist findings/review notes/history và report context | Tạo/lưu/mở lại finding; evidence refs và selected filters giữ đúng run |
| M01-026 | R1/R3; 022, mature model inputs sau 021 | Freshness/missingness/support monitoring và investigation runbook | Distinguish source lag/structural missing/drift; chưa có mature labels không sinh calibration alarms giả |
| M01-027 | R3; 021–022 | Frozen model batch/query scoring interface nếu UI cần | Scores match validated artifacts; correct feature order; unknown model/source/run fails clearly |
| M01-028 | R1 subset, R4 full; 024–027 theo scope | Browser/user-flow/export/privacy QA | Empty/missing/low-support/gated states; private/public modes đúng; no private payload in bundle |
| M01-029 | R4; 028 | Final clean reproduction từ source manifests tới final report | Numeric outputs/lineage cùng frozen study; credentials không cần nằm trong repository |
| M01-030 | R4; 029 | Case study, methods/model/data cards, demo và handoff checklist | Người đọc hiểu question/data/target/results/limits; artifact links/run versions đầy đủ |

Critical path model: **001–004 → 005–009 → 007/015/016 → 017–021 → 022/027 → 028–030**. Critical path descriptive: **001–004 → 008–014 → 022–025 → R1 browser/reconciliation checks**. Một số công việc dùng cùng artifacts nên có thể xen kẽ; bảng không yêu cầu chờ xong model mới hoàn thiện giao diện descriptive.

Khi access annual data bổ sung chưa sẵn, tiếp tục R0/R1, source-independent contracts, regression checks, UI/review và protocol audit. Chỉ việc phụ thuộc source mới cần chờ. Không bypass login, nhận password trong chat, tự chấp nhận agreements hoặc coi việc đọc documentation là đã được dataset access.

<a id="chuong-47-19"></a>

### 47.19. Extensions được tách khỏi critical path

| ID | Extension / mục đích | Dependencies tối thiểu | Đầu ra và quyết định dừng |
|---|---|---|---|
| M01-X01 | Real macro vintages và revision sensitivity | Actual official API access, series definitions/rights, landmark calendar | Coverage/as-of join và revised-vs-known example; missing access giữ unavailable, không latest fallback |
| M01-X02 | Behavioral landmark risk | Audit existing contract, multi-vintage data, loan-group protocol, eligible histories và event support | Baseline/challenger cho target riêng; thiếu support thì giữ descriptive current-state evidence |
| M01-X03 | Forecast/stress/reverse stress | Qualified mature inputs, rolling-origin backtest, coherent scenario mapping | Scenario report có baseline/assumptions; forecast chưa đủ evidence thì không diễn giải actual stress loss |
| M01-X04 | Severity/LGD model | Multi-vintage terminal/recovery completion; balance/selection/censoring contract | Model card/evaluation cho đúng resolved population; unresolved bias chưa xử lý thì bridge là output chính |
| M01-X05 | Fannie external-source validation | Authorized snapshot, separate dictionary, semantic/selection harmonization | Transferability report; incompatible target/features thì làm descriptive parallel case |
| M01-X06 | D08/D09 mở breadth P2 | HMDA hoặc MF data pilot, source-specific contracts | Origination-market hoặc DSCR/maturity workspace; không nối Freddie borrower identities giả |
| M01-X07 | Ginnie Mae MBS loan-performance parallel case | User-acknowledged Terms of Use, official file dictionary/layout, quarterly pilot, separate population/target contract | Ginnie-only descriptive/model readiness decision; không tính là Freddie vintage; giữ descriptive-only nếu history/event/selection gates không đạt |

Không dùng các extensions để trì hoãn handoff D01 chính. Sau R4, chọn extension theo câu hỏi cần chứng minh; nếu muốn P2 hoàn thiện cả residential/CRE thì D09 là case tiếp theo, còn nếu muốn suite cover nhiều domain thì chuyển D02/P1 để kiểm chứng shared core.

<a id="chuong-47-20"></a>

### 47.20. Effort và lịch làm: gate quyết định chất lượng, lịch giúp tổ chức công việc

Ước lượng dưới đây là **planning range cho một builder**, đã tận dụng code hiện có; chưa đo runtime/rework và chưa tính thời gian chờ bên ngoài. Giả định bạn dành 20–30 giờ/tuần, repo/raw snapshot tìm được, và những chức năng được README ghi nhận tái tạo được sau audit.

| Đợt | Effort dự kiến | Kết quả để review |
|---|---|---|
| R0 | 16–24 giờ | Inventory, rebuild, semantic/resource receipts, gap report |
| R1 | 40–56 giờ | Descriptive module với core views, review và report snapshot |
| R2 | 32–48 giờ, ngoài thời gian chờ access | Multi-vintage canonical/labels, support/split/features qualified |
| R3 | 56–80 giờ | Actual model comparison/calibration/OOT, model card và scoring evidence |
| R4 | 16–24 giờ | Final browser/export/privacy QA, reproduction và case package |
| Tổng scope chính | **160–232 giờ; khoảng 6–12 tuần làm chủ động** | D01 hoàn chỉnh trong đúng scope nghiên cứu nếu gates đạt |

R1 cùng R0 khoảng 56–80 giờ, thường 2–4 tuần với giả định trên. Source expansion có thể xen kẽ R1; không có bảo đảm final R3 date khi access, event support hoặc protocol chưa đạt. Nếu audit phát hiện parser/model/website phải sửa đáng kể, cập nhật estimate sau R0 bằng observed work, không cố giữ lịch rồi bỏ validation.

Một extension macro+forecast/stress có thể thêm khoảng 40–80 giờ khi đủ dependencies; behavioral/severity/Fannie/CRE cần estimate sau pilot riêng. Portfolio project này cũng có learning time: mỗi milestone dành thời gian đọc contract, tự giải thích và viết findings, không chỉ chạy commands.

<a id="chuong-47-21"></a>

### 47.21. Verification plan: checks cần thiết cho risk results và user flow

Không viết lại mọi tests đã có. R0 đọc suite hiện tại, chạy relevant checks, xác định semantics/gates nào thiếu coverage. Test mới ưu tiên lỗi có thể làm thay target, rò thời gian, sai mẫu số, sai loss hoặc trộn artifacts.

| Nhóm | Kiểm tra có ý nghĩa | Evidence khi đạt |
|---|---|---|
| Source/schema | Wrong release/layout, duplicate keys, orphan records, new enum, conditional sentinels, valid zero/negative | Parse/contract receipts và failure reports; no dependent-stage run khi contract fail |
| Target | Window t+1…t+12, early-entry age, modified/terminal entry, prepay negative theo estimand, other exits, gaps và censoring | Edge-case outcomes đúng contract; independent full-table reconciliation trên frozen sample |
| Temporal leakage | Future outcome appended không đổi predictors; label-known/cutoff checks; train-only encoder; same loan không xuyên partitions | Feature/split manifests và regression checks với deliberate future contamination |
| Episodes/transitions | Gap adjacency, REO/termination axis, third-current cure, redefault after confirmation | Independent pairs/episode ledger đối chiếu aggregate matrices |
| Loss | Signed components, terminal uniqueness, missing components, unresolved/negative cases | Raw-versus-derived bridge, documented residual/tolerance theo precision nguồn |
| Model comparison | Same IDs/target/cohort; calibration isolation; raw/calibrated retention; native/JSON/load score parity | Frozen assessment tables/digests; incorrect model/config bị từ chối |
| Scenario, nếu mở | Mass conservation, probability bounds, invalid macro vintage/unit, origin leakage | Naive/backtest/scenario receipts; assumed và observed outputs phân biệt |
| UI/report | Selected run/filter persistence; chart/Excel/export totals; empty/low-support/gated states; save/reopen finding | Browser acceptance memo/screenshots riêng tư phù hợp, reproducible export refs |
| Privacy/export | Raw IDs/loan panel/private workbook không ở deployable bundle; source rights/output type gates | Bundle/data-package scan và allowed export inventory |
| Reproduction | Clean run từ immutable source tới report; không hardcode upstream run ID; missing/tampered artifact | Rebuild receipt, explained differences, new run dùng đúng actual upstream paths |

Counts/keys đòi hỏi exact reconciliation. Dollar amounts, probabilities và statistical summaries có tolerance riêng được ghi trong contract theo source precision/method; không dùng một tolerance lớn để bỏ qua mọi mismatches. Source UPB có rounding nên reconciliation khớp source không thành exact contractual cash flow.

Performance targets đề xuất để pilot: aggregate filters/chart requests khoảng p95 ≤2 giây khi phục vụ frozen marts; private single-loan timeline khoảng ≤3 giây trên máy local. Đây là UX goals, chưa là measurements. Sau benchmark R0/R1 sẽ chốt budget và query limits; bulk processing hiển thị progress/receipt, không hứa ingestion tức thời.

Repo ghi 375 tests và reproduction checkpoints là baseline evidence để so sánh. Lượt lập plan này **không chạy tests đó**, nên final plan không gọi chúng là kết quả verification mới.

<a id="chuong-47-22"></a>

### 47.22. Definition of Done theo từng release

**R0 hoàn thành khi:** tìm được đúng source/snapshot, pin code/dependencies, clean pipeline chạy lại, inventory/gap/resource report lưu được, và nghĩa dữ liệu quan trọng khớp contract. Nếu raw snapshot chưa tìm được thì chỉ inventory/tài liệu đạt; R0 rebuild vẫn ghi unmet.

**R1 hoàn thành khi:** core descriptive views dùng cùng frozen dataset; labels/population/stock/transitions/episodes/loss reconcile; charts có denominator/support; unavailable khác zero; reviewer lưu/mở lại finding; allowed export giữ run/filter/methodology; browser QA cho descriptive flow đạt. Model readiness chưa đủ không làm R1 giả thành modeling project đã validated.

**R2 hoàn thành khi:** source access/release/coverage cho required vintages đạt; multi-vintage canonical và label audit xong; support/uncertainty review phù hợp mục đích; split/feature protocol đóng băng và được kiểm tra; loan overlap/cutoff/leakage/final-test logs đúng. Chỉ nhiều file hoặc nhiều rows không đủ.

**R3 hoàn thành khi:** actual baseline/challenger trên cùng study được fit/calibrate/validate; selection history/rubric và freezes đầy đủ; OOT đã đánh giá theo protocol; model card nói đúng target/population/horizon/support; serving parity nếu có interface. Outcome hợp lệ có thể là giữ logistic, không có model thắng rõ, hoặc không đủ empirical performance cho permitted use dự kiến. Negative research result vẫn bàn giao được nếu study được làm đúng và tên trạng thái phản ánh kết luận.

**R4 hoàn thành khi:** final pipeline/report/UI tái tạo, browser/export/privacy checks đạt, findings/limitations nhất quán với evidence, case study và run instructions đủ cho người khác review. Public deployment chỉ là bước riêng nếu được yêu cầu và output rights đã đáp ứng; một local/private final case có thể hoàn thành scope hiện tại.

**D01 scope chính hoàn thành** khi R0–R4 đạt các điều kiện này. Nếu R2 source/support vẫn thiếu, R1 có thể được bàn giao là descriptive case, nhưng backlog modeling của D01 giữ unmet và không báo toàn bộ dự án đã hoàn tất.

<a id="chuong-47-23"></a>

### 47.23. Kế hoạch 10 ngày làm việc đầu: làm gì ngay khi bắt đầu implementation?

Ngày trong bảng là **ngày làm việc thực tế**, không lịch deadline đã cam kết. Mỗi ngày khoảng 4–6 giờ theo giả định effort; điều chỉnh sau inventory. Ưu tiên đoạn descriptive hữu ích, trong lúc xác định access cho multi-vintage. Không fit mortgage model trong mười ngày đầu nếu R2 chưa đủ gates.

| Ngày | Công việc | Artifact cụ thể cuối ngày |
|---|---|---|
| 1 | M01-001: tìm repo/data chính xác; pin commit; đọc charter/status/code entry points | Inventory và checklist claimed/reproduced/unmet; không nhầm corporate warehouse-funding data với mortgage loan performance |
| 2 | M01-004: source hashes, D: private paths, dependency/website audit | Environment/source/paths manifest; phương án reuse engine và UI |
| 3 | M01-002: clean foundation run 2012; đo time/RAM/temp/disk | Pipeline receipt mới và resource benchmark; upstream run IDs lấy từ output thật |
| 4 | M01-003: xử lý differences; kiểm tra semantics và meaningful tests | Reconciliation delta report; R0 reviewable checkpoint |
| 5 | M01-008/009: target, exclusions, event-support review | Label contract version; totals 50.000/48.066/102 đối chiếu nếu cùng snapshot; limitations theo Relief |
| 6 | M01-010/013: stock/cohort/vintage metrics đã có | Frozen metrics/denominator catalogue và hai–ba findings descriptive có evidence |
| 7 | M01-011/012: adjacent matrices và sustained-cure paths | Reconciled transition/episode evidence, selected edge-case traces |
| 8 | M01-014: loss bridge và missing/unresolved audit | Signed loss memo; chưa có expected-loss dollar forecast |
| 9 | M01-022/023: adapter, source/run navigation, core views | Private demo đầu với filters và lineage cùng run; unavailable states rõ |
| 10 | M01-024/025 và R1 subset QA: user journey, persist finding, allowed report | Reviewable descriptive slice, remaining R1 list và measured estimate cho các đợt sau |

Từ ngày 2 có thể xác định source-access readiness và chuẩn bị M01-005; acquisition thực chỉ khi điều kiện source đã đáp ứng. Đích ngày 10 là **vertical slice có bằng chứng và gap list**, không bảo đảm mọi R1 screen đã polish hoặc multi-vintage study đã đủ. Các phần R1 còn lại được hoàn thiện trong budget 56–80 giờ bao gồm R0.

<a id="chuong-47-24"></a>

### 47.24. Output giao cho P4/P5 và phần shared core thực sự được xây

| Consumer | D01 có thể giao trong scope chính | Check bắt buộc / phần chưa có |
|---|---|---|
| P4 portfolio analytics | Sample exposure/UPB, states/events, loss components, cohort summaries và methodology | Currency/balance/sample scope/snapshot rõ; không gọi public acquired-loan sample là book của một ngân hàng |
| P4 finance/ECL extension | Research event-risk outputs sau R3, kèm target/horizon/limits | Early-entry D3 risk không là regulatory-default PD/ECL input trực tiếp; cần default mapping, term structure, EAD/LGD/discounting/scenario/use validation |
| P5 collateral surveillance | Loan attributes/events, aggregate collateral context với namespaces | Chưa có deal holdings/waterfall/complete contractual schedules để định giá chứng khoán |
| P5 cash-flow projection extension | Chỉ future modeled schedules/scenario cash flows nếu đã tạo và kiểm định | Current UPB rounding/performance snapshots không tự là observed full cash flow; assumptions và CF engine còn riêng |
| Shared core | Source/run/snapshot registry, evidence refs, typed exports, filter/report context, findings/review history | Domain math ở `crsl`; abstraction mới phải qua D02 hoặc case khác để chứng minh dùng chung |

Header và permitted-use checks theo [38.3](D:/data/Codex/research/credit-risk-master/2026-10-08/CREDIT_RISK_MASTER_RESEARCH.md#chuong-38-3). Unknown/unsupported output type có error rõ; không truyền một cột `pd` chung rồi để consumers tự đoán nghĩa. Workspaces chung UI/registry không đòi loan IDs hoặc populations giữa sources giống nhau.

<a id="chuong-47-25"></a>

### 47.25. Những điểm chưa chắc chắn và quyết định xử lý

| Điểm cần xác minh | Ảnh hưởng | Cách giải quyết và công việc vẫn làm được |
|---|---|---|
| Repo/data local chưa được định vị và chạy lại trong lượt này | Chưa bảo đảm foundation rebuild được trên D: | M01-001/002; trước đó vẫn có target/data/protocol specification reviewable |
| Additional annual access hiện tại chưa kiểm chứng | R2 acquisition có thể phải chờ | Chuẩn bị manifest/config và hoàn thiện R1; không bypass access hoặc yêu cầu credentials trong chat |
| 2012 event count ít và Relief-dominated | Model/support/generalization chưa được chứng minh | Multi-vintage audit; segment/uncertainty report; chưa suy ra modern/vietnamese unsecured performance |
| Missingness và source layouts thay theo giai đoạn | Features/panel giữa vintage có thể không comparable | Availability matrix, versioned adapters/allowlists và documented ablations |
| Protocol 2006–2018 hiện là candidate | Có thể thiếu support hoặc không đáp ứng mục đích mới | Independent timing/support review, revision trước fitting; không sửa bằng random split |
| Latest mortgage release có revisions | Chưa strict historical public-PIT | Retrospective temporal claim; archival availability review là extension nếu cần |
| Severity resolution/source coverage thiếu | LGD/ECL có thể biased hoặc unavailable | Descriptive bridge và unresolved report trước; severity gate riêng |
| Local website framework/adapter chưa code-audited | Effort UI/port có thể khác estimate | R0 inventory rồi reuse/port quyết định bằng parity và effort, không rewrite mặc định |
| Resource footprint nhiều vintage chưa đo | Full run có thể vượt D:/RAM budget | Bounded pilots, projected disk/temp, preserve originals, revise storage plan khi cần |
| Xuất công khai/series rights chưa hoàn tất | Public release có thể cần scope khác | Local/private output và allowed source-backed reports; kiểm tra cụ thể trước publish khi có yêu cầu |

Decision log khởi điểm: **D01 trước; kế thừa `crsl`; 2012 descriptive trước; existing early-entry target giữ nguyên; multiple vintages trước fitting; model champion theo evidence; CRE/macro/stress/severity tách extension; mọi artifacts mới trên D:.** Khi một giả định thay đổi, ghi decision/version mới và cập nhật backlog liên quan, không đổi nghĩa của kết quả đã frozen.

<a id="chuong-47-26"></a>

### 47.26. Nguồn được đọc và độ chắc chắn của plan

Nguồn repo đọc trực tiếp qua kết nối GitHub ngày 08/10/2026. SHAs dưới đây là **file blob SHAs**, không phải một commit pin của toàn repo; implementation phải lấy và pin commit thực ở M01-001. Cùng ngày đọc nhánh `master` không bảo đảm tuyệt đối các files đến từ một commit nếu repo có concurrent changes.

| Tài liệu | Blob SHA lúc đọc | Dùng để chốt |
|---|---|---|
| [README](https://github.com/susayold/credit-risk-strategy-lab/blob/master/README.md) | `4a71aeed526387c8020b2653adc4870276b583a2` | Foundation, data/model/UI/reproduction evidence status |
| [Block status](https://github.com/susayold/credit-risk-strategy-lab/blob/master/block-status.md) | `4f291b5afd406dbdb3477a6f91af7587b03f6b3e` | B01–B35 gaps và current split/support |
| [Charter](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/charter.md) | `b5f192c4527a6d30a3ecc5eaa5a45e443fdb3f22` | Mortgage scope, audience và permitted claims |
| [Canonical dictionary](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/data_dictionary/canonical.md) | `5dbac9a5b869e9843ec0ce3431149cb96835a6b5` | Grain, types, source sentinels, unit/state semantics |
| [Observation/censoring](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/methodology/observation-and-censoring.md) | `ba56337d26ad6f6ba7760ff8306aa76f63cee6a5` | Target, attrition, prepay/exits, episodes |
| [Source semantics ADR](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/decisions/ADR-002-source-semantics.md) | `2268aa2f8de6bb4456e1c932e72d4c4e3b7f6a43` | Origination/entry correction, missingness, loss references |
| [Validation protocol](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/methodology/validation-protocol.md) | `8aca49889345084ec257eb5505e1bbdc43698357` | Candidate schedule/cutoffs, class support, PIT/freeze limitations |
| [Feature catalogue](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/feature-catalogue.md) | `405a6ba3d362fb86be1e93a76dd550042d67bf94` | Baseline allowlist, train-only transform và exclusions |
| [Model comparison](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/model-comparison.md) | `61efcedf30951cc803e865a725d9b7cca7720acb` | Same-cohort runner, challenger persistence, outstanding validation |
| [Macro availability](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/methodology/macro-availability.md) | `5bfe98527179f09f4a8ead9c68efa104f7834145` | As-of conventions, real-data/access gaps và units/revisions |
| [Source access](https://github.com/susayold/credit-risk-strategy-lab/blob/master/docs/source-access.md) | `64fea848f15d5097ff8147397b2f7bc9e8f4f7d9` | Annual sample 2012, format-example boundary và Clarity route |
| [Dependencies](https://github.com/susayold/credit-risk-strategy-lab/blob/master/pyproject.toml) | `ee9128a18ff93a03144ad7d4d51ef79cd7b3a107` | Existing Python/DuckDB/PyArrow/model pins |

Official source documentation được đối chiếu thêm: [Freddie SFLLD](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset), [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [FHFA HPI datasets](https://www.fhfa.gov/data/hpi/datasets). Chúng xác nhận source routes/calendar/data types cần xét, chưa thay cho payload profiling.

Effort, screen design, backlog, release sequencing và resource budgets là **đề xuất triển khai**. Counts/tests/artifacts của repo được dẫn với status đúng; chưa có bằng chứng mới về model performance từ lượt này. Plan này giữ research gốc, 32-source catalog và 11 case charters làm nền; chương 47 là đường tra cụ thể cho việc bắt đầu D01.
