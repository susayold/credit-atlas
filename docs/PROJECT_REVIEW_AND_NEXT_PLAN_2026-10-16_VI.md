# CreditAtlas — Đánh giá hiện trạng và kế hoạch phát triển tiếp theo

Ngày nghiên cứu gốc: **16/10/2026**; trạng thái được cập nhật **17/10/2026**, múi giờ Asia/Bangkok. Baseline code của vòng rà soát gốc: `b997c204c88a2773efac57137cf0b2ba5401e1b8`. Báo cáo này là đầu mối đọc hiện trạng và quyết định công việc tiếp theo; các kế hoạch và receipt cũ vẫn là bằng chứng lịch sử.

## Cập nhật trạng thái ngày 17/10/2026

Plan gốc đã rà soát ledger 50 capability, D01/D02, các workflow trọng yếu, inventory code/test và nguồn nghiên cứu chính thức. Kết quả rà soát **không có nghĩa là đã đọc lại từng dòng của toàn bộ repo hoặc profile lại mọi raw dataset**; phạm vi, cách đếm và giới hạn đã nêu ở mục 2. Các kết quả mới sau baseline được cập nhật như sau:

| Hạng mục | Trạng thái mới | Tác động lên plan |
|---|---|---|
| N02 — source-to-KPI trace | Đã rà 27 parent groups, 20 ID trong `public_sources.catalog()` và receipt local khớp 20/20. Source register có **91 records**: 20 public-suite và 71 supplemental objects thuộc 16 broad families. Đã bind 12 HMDA LAR/TS/MSAMD, 9 FHFA PUDB/NMDB/NSMO, 5 LendingClub/Bondora, 2 Treasury HAMP, 22 World Bank WDI và 12 BoC–BoE Sovereign Archive objects. Thời điểm tải, kỳ tham chiếu, edition, hash prefix và consumer được tách theo object. | **16/27 parent groups** có source-level binding; 11 nhóm còn lại cần object hoặc trạng thái no-data/access-pending. 7 FRED IDs vẫn chưa có parent group. WDI có 122.892 annual rows /64.452 source NULL; HAMP có 9.872.074 dòng nhưng 14 activity dates và thiếu xác minh coverage 2018–2021. Sovereign Archive có bốn edition, 42.519 entity-year rows, 680.304 vị trí của 16 metric chọn; 515.678 missing, 72.509 zero, 1.341 source markers, 9.954 schema absence và 68 count conflicts giữ nguyên. Ba nguồn này là bối cảnh aggregate/macro/sovereign, không tạo borrower PD. Còn route/API/UI/Excel parity, PUDB Excel, N03 formula linkage, quyền third-party, và các source group có label outcome; Freddie/Ginnie chỉ theo publisher access/terms. |
| N09 — ABS surveillance | Acceptance của N09 đạt và đã phát hành; ba comparator vẫn giữ riêng theo hợp đồng. 83 recovery residual còn unresolved. | Đóng đầu ra surveillance của N09; giữ recovery/LGD qualification và mọi root-cause claim ở trạng thái mở. Không đổi 26/50 capability completion. |
| N14 — Bondora label/maturity | Audit đầy đủ snapshot 789.144 dòng và companion Excel aggregate đã dựng; 10.860 nhãn NULL nằm trước maturity-date proxy nhưng không có action evidence tại/sau anniversary. | N14 chỉ partial. Giữ NULL, không fit model; cần lịch quan sát theo từng khoản và định nghĩa lịch sử từ publisher trước khi chốt maturity/target. |
| N10 — Freddie annual sample | Downloader giới hạn theo manifest, kiểm host/archive/resource và receipt/hash đã có; chưa có phiên Clarity để tải annual sample. | Đây vẫn là đường găng R2/R3. Không giả lập dữ liệu và không tăng số Freddie vintage. |
| N05/N06 — NMDB | Mart, API và query-scoped workbook đã được kiểm runtime; browser visual và mở/recalculate Excel desktop chưa nghiệm thu. | Giữ acceptance mở cho đến khi hoàn thành hai kiểm tra người dùng này. |
| Tổng capability ledger | 26/50 (52%) theo định nghĩa 50 capability; các action N09/N14 không tự nâng tỷ lệ. | Không dùng số action/release mới để đổi mẫu số hay phần trăm completion. |

**Thứ tự tác vụ được làm mới:** (1) Ưu tiên source có thể tạo borrower/loan outcome mới: kiểm tra local authenticated Freddie/Ginnie access và tải đúng một pilot mỗi publisher khi session/terms cho phép; kiểm layout, status definition, loan-month grain, release cutoff, key, missingness và exact receipt trước khi mở rộng. Không mô phỏng hoặc ghép hai publisher. (2) Với nguồn đã bind, hoàn tất API/UI/filtered-export parity theo route; thêm analyst-facing PUDB Excel, kiểm HMDA denominator và N03 method links cho các KPI được hiển thị. (3) Ghi rõ status cho 11 parent groups còn lại: bind receipt/source object hoặc nêu endpoint, access, terms và điều kiện dừng; không mở thêm nguồn chỉ để tăng row count. (4) Tìm cách xác minh HAMP activity trước 2022 và rights/provider metadata WDI; nếu publisher không cấp được thì giữ gap và không dự phóng. (5) Hoàn tất Sovereign Archive route/export parity, per-edition lineage, source-marker/missing/zero display và third-party rights review; dùng làm bối cảnh P4, không PD/LGD. (6) Đóng N05/N06 bằng Excel desktop/query parity; resolve hoặc fence FRED/ALFRED/ICE trước software/model/public use; direct-source migration chỉ sau definition/date parity. (7) Giữ N14 partial cho tới khi publisher giải thích observation cutoff và 10.860 NULL; chọn corporate facility có executed terms cho N16/N17. HMDA/NMDB aggregate không thay performance label; ABS residual không thành LGD.

## 1. Kết luận để quyết định hướng đi

CreditAtlas đã là một ứng dụng nghiên cứu tín dụng có dữ liệu thật, bộ máy phân tích, hai nghiên cứu model benchmark, workflow lưu bằng chứng và Excel. Điểm mạnh là khả năng truy nguyên con số và giữ rõ giới hạn sử dụng. Điểm đang làm dự án chậm đạt đích là nhiều nhánh acquisition/analysis được mở nhưng chưa đóng trọn chuỗi **dữ liệu phù hợp → định nghĩa outcome → kiểm định → sử dụng → nghiệm thu**.

**Đề xuất giữ một codebase và năm workspace.** Đóng gói các case study độc lập để trình bày như năm dự án nghiệp vụ, dùng chung catalog, quality, lineage, Excel, review và test infrastructure. Không cần tách năm repository hoặc ép năm domain dùng một model/target/schema duy nhất.

Đợt tiếp theo nên hoàn thành ba việc: (1) hợp nhất trạng thái dữ liệu, giả định và nghiệm thu; (2) biến dữ liệu đang có thành một sản phẩm surveillance/điều tra sai lệch hoàn chỉnh, ưu tiên ABS Toyota/Nissan và NMDB; (3) mở R2/R3 mortgage khi có thêm dữ liệu Freddie hợp lệ. Trong lúc chờ truy cập, tiếp tục nghiên cứu Bondora booked-loan cohorts và một case corporate debt/covenant có tài liệu thật. Không tiếp tục thêm nguồn aggregate chỉ để tăng số dòng.

## 2. Phương pháp rà soát và giới hạn của bằng chứng

Đã đọc kế hoạch 50 capabilities, kế hoạch D01 30 công việc/R0–R4, kế hoạch KPI và D02; đối chiếu completion ledger, báo cáo nghiệm thu, model cards, nghiên cứu dữ liệu và các module triển khai liên quan. Kiểm tra trực tiếp code server, study preparation, feature controls, source verification và cấu trúc repo. Nghiên cứu ngoài repo dùng nguồn cơ quan phát hành, tài liệu chính thức và bài nghiên cứu gốc.

Kiểm tra mới trong lượt này:

- Đếm trực tiếp 50 requirements trong `COMPLETION_REQUIREMENTS_50.json`, không suy từ nhãn UI.
- **138/138 tham chiếu hash trong completion evidence tồn tại và khớp** với các file private được tham chiếu. Cả 26 mục `full_completion_proven=true` đều có hash evidence. Đây là kiểm tra tính toàn vẹn file, không phải chạy lại toàn bộ nghiệm thu hay xác nhận chất lượng khoa học của mọi kết luận.
- Inventory code có 149 module Python trong `src/credit_atlas`, 174 file `test_*.py` ở thư mục tests cấp gốc và 200 file tài liệu tại baseline. Có 208 chuỗi đường dẫn `/api/…` theo phép quét nguồn; đây không phải số route được nghiệm thu. Không có `.github/workflows` trong checkout này.
- Cập nhật sau baseline: thêm 12 source records cho BoC–BoE Sovereign Archive sau khi size/SHA của cả 12 file trong hai private receipts khớp; nối tới `country_observatory.py`, `country_views.py` và `/api/sovereign-defaults`. Các thống kê bốn edition là revision/context, không dùng làm retail/corporate PD.
- Ranh giới câu hỏi “đã đọc hết code/data chưa”: **chưa đọc từng dòng mọi file code và chưa profile lại mọi raw row của toàn repo**. Đã lập inventory repo, đọc ledger/kiến trúc và trace các module trọng yếu cho workflow ưu tiên, kiểm receipt/hash và actual-data audit tại các tranche được liệt kê. Plan có bằng chứng trong phạm vi audit đã nêu, không phải chứng nhận exhaustive code/data review.
- Smoke HTTP read-only ngày 16/10: health, runs, NSMO dictionary và NMDB performance trả 200. `/api/suite-views` vượt timeout 15 giây khi test suite đang chạy đồng thời. Sau khi suite hoàn tất, health trả 200 trong 0,048 giây và hai lượt suite-views trả 200 trong 0,838/0,201 giây. Chưa đủ để tính p95 hoặc kết luận nguyên nhân/regression; cần profile cold/warm và tải đồng thời riêng.
- Kết quả chạy mới toàn bộ public app/vendor suite được ghi ở phần kiểm chứng cuối báo cáo. Không mở lại production final holdout để chọn model.

Các số lượng dataset và kết quả khoa học dưới đây lấy từ hồ sơ acquisition/audit/model card đã lưu; lượt này không đọc và profile lại toàn bộ hàng chục triệu raw rows. Phân biệt rõ **kiểm chứng mới**, **bằng chứng lịch sử còn nguyên hash**, và **đề xuất chưa triển khai**. Xem [audit metadata](data/project-review-evidence-2026-10-16.json).

## 3. Tiến độ đúng nghĩa: 52% thuộc phạm vi nào?

| Workspace | Hoàn thành theo ledger hiện tại | Còn mở | Ý nghĩa thực tế |
|---|---:|---:|---|
| P1 Retail | 6/10 — 60% | 4 | Behavioral benchmark và review có bằng chứng; application underwriting, affordability thực, pricing và collections chưa đầy đủ |
| P2 Mortgage | 9/10 — 90% | 1 | Chín capability đã nghiệm thu trong scope được ghi, chủ yếu descriptive; P2.08 horizon model chưa đạt |
| P3 Business/corporate | 8/10 — 80% | 2 | Có SBA, financial ratios, bankruptcy benchmark và memo; covenant/debt service đầy đủ còn thiếu |
| P4 Portfolio/observatory | 3/10 — 30% | 7 | Actual exposure intake, concentration và movement đã có; EL/ECL/stress/tail còn assumptions và governance gaps |
| P5 Structured/market | 0/10 — 0% | 10 | Đã có rất nhiều implementation và data; chưa capability nào đóng đủ toàn bộ acceptance rộng trong ledger |
| **Toàn CreditAtlas** | **26/50 — 52%** | **24** | Đếm đều từng yêu cầu, không phải tỷ lệ giờ công, giá trị kinh doanh hay production readiness |

42/50 có một mức triển khai/conditional coverage theo hệ nhãn checkpoint cũ. **84% coverage không phải 84% hoàn tất.** P5 0/10 cũng không có nghĩa là chưa xây gì. Mọi tỷ lệ phụ thuộc scope; không thu hẹp acceptance chỉ để nâng số phần trăm.

**Đính chính cách báo trước:** một số tài liệu và cập nhật gọi 26/50 là “D01 52%”. Mẫu số 50 thuộc cả P1–P5. D01 có 30 backlog items và các release sau; không dùng 9/10 của P2 để kết luận D01 đã xong 90% modeling.

| Release D01 | Hiện trạng | Điều kiện còn lại |
|---|---|---|
| R0 Foundation | Partial | Rebuild/semantic evidence đã có; resource/package/distribution sign-off cuối còn mở |
| R1 Descriptive | Đạt cho Freddie 2012 frozen sample | Chỉ scope mô tả một vintage |
| R2 Multi-vintage study | Chưa đạt | Annual samples hợp lệ, layout compatibility, support, timing và feature protocol |
| R3 Modeling | Chưa đạt, chưa fit model thật | Baseline/challenger, calibration, validation, freeze, OOT |
| R4 Handoff đầy đủ | Partial | Final reproduction và bàn giao bao gồm study đã đạt R2/R3 |

Nguồn local: [ledger 50 mục](COMPLETION_REQUIREMENTS_50.json), [kế hoạch D01 §47.18/47.22](PLAN_MODULE_01.md), [D01 progress](D01_PROGRESS_AND_DATA_PRIORITY_2026-10-16_VI.md). Các trạng thái trên không được nâng trong lượt nghiên cứu này.

## 4. Từng domain đã làm được gì, cần làm gì tiếp?

### 4.1. P1 — Retail: benchmark tốt, thiếu dữ liệu quyết định cấp tín dụng

Đã có UCI350 với 30.000 khách hàng và 180.000 hàng lịch sử tháng, target tháng kế tiếp, train-only preprocessing, constant/logistic/boosting, tập calibration riêng, model freeze và holdout access ledger. Model boosting/raw có final ROC AUC 0,777878, AP 0,543521, Brier 0,136377 trên 3.001 khách hàng/664 positives. Đây là kết quả đã lưu, không chạy lại trong lượt này. Split là random client-disjoint trên cohort Đài Loan 2005; chưa chứng minh OOT hoặc khả năng áp dụng tại Việt Nam. [Model card](RETAIL_FROZEN_HOLDOUT_AND_MODEL_CARD.md).

Đã có policy cost/capacity, explanation, subgroup, saved reviews, LendingClub explorer và affordability form/Excel. LendingClub có hai nguồn accepted tách biệt: Kaggle v3 2.260.701×151 (2007–2018Q4) và Mendeley expired-loan subset 1.055.054×90 (2016Q1–2020Q2), cùng Kaggle rejected 27.648.741×9 và dictionary 280 definitions checked. Hai snapshot accepted không được gộp; accepted funded loans và rejected applications không tạo mẫu số approval tương thích. Bondora/Go & Grow đã có 789.144 loans/31 fields, 86.618 cờ default-12M true, 520.246 false, 182.280 NULL. NULL phải giữ là chưa đo được; dữ liệu đã giải ngân không tự cung cấp requested amount, application decision time hay counterfactual của hồ sơ bị từ chối. [Bondora research](BONDORA_PUBLIC_DATASET_RESEARCH_VI.md).

**Bước nên làm:** xây study contract riêng cho booked-loan cohort Bondora: maturity, source-defined default, country/vintage, availability từng feature, duplicate/repeat-borrower limitations. Trước tiên tạo descriptive risk/coverage tables; chỉ fit sau khi protocol đủ. P1.02 application underwriting vẫn mở nếu chỉ có booked loans. Affordability cần chứng từ thu nhập/nghĩa vụ có thời điểm và người xác minh. Pricing cần funding/operating/capital cost, take-up và thực nghiệm policy; collections cần action/contact/payment/recovery log. Không có nguồn public generic nào tự đóng được các yêu cầu nội bộ này.

### 4.2. P2 — Mortgage: sản phẩm descriptive mạnh nhất, đường găng vẫn là R2

Freddie 2012 có 50.000 loans và 4.510.559 loan-months. App đã có portfolio/cohort, private lifecycle, adjacent transitions, cure/redefault episodes, competing outcomes, observed-loss bridge, findings và export. Actual prepare-study có 43.327 train loans, 100 positives; calibration/validation/test hiện không có rows. Do đó chưa thể chứng minh hiệu năng thời gian bằng dữ liệu hiện tại. DTI train thiếu 15.758/43.327 và sentinel 999 có ý nghĩa nguồn cần giữ; không được nội suy như một khoảng trống số học thông thường. [Support audit](D01_R2_CURRENT_SUPPORT_AUDIT_2026-10-16_VI.md).

**Bước nên làm:** khi có phiên Clarity hợp lệ, tải đúng candidate vintages trong protocol hiện tại: train 2006–2012, calibration 2014, validation 2016, final 2018. Đây là thiết kế ứng viên cần review lại timing/support; không tự phê duyệt vì đủ tên năm. Pilot một annual archive trước, đối chiếu release/schema/R47 rồi mở batch. Freeze final-test access policy trước khi phân tích nhãn OOT. Nguồn Freddie chính thức vẫn yêu cầu đăng ký và sign-in. [Freddie SFLLD](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset).

NSMO D02 đã có 62.359 loans × 587 fields, 51 quý, dictionary/wave coverage và descriptive app. Earliest-current landmark có 156 observed 90+ outcomes ở 12 tháng; dynamic first-entry có 695 first observed exits nhưng là estimand khác. Không tăng sample size hữu hiệu bằng cách đếm nhiều landmark của cùng loan như người vay độc lập. Giữ D02 ở descriptive/feasibility, hoàn thành routing/weights/censoring review có phạm vi; không liên tục mở thêm thang target để tìm ra outcome “đẹp”. [D02 plan](NSMO_D02_CASE_BUILD_PLAN_VI.md), [risk-set research](D02_NSMO_RISK_SET_FEASIBILITY_2026-10-16_VI.md).

HMDA 2018–2025, NSMO và NMDB bổ sung câu hỏi application/borrower/market. Chúng không tạo payment/default labels cho Freddie. HMDA cần release/year/cohort comparability; tách Dynamic, Snapshot, One-Year và Three-Year, giữ 1.961 source rows bất thường của 2018 ngoài KPI cho đến khi có giải thích.

### 4.3. P3 — Business/corporate: gần một workflow analyst dùng được

SBA adapter xử lý 2.190.504 source records, giữ duplicate/cancelled/unknown, cohort/state/industry và exact amounts. SEC có source facts, filings, annual financial statements, ratio inputs, trends, debt maturities, source notes và memo version history. UCI365 có 43.405 statements theo năm horizon; one-year benchmark dùng 5.910 statements, final 591 rows/41 positives. Boosting/Platt final AUC 0,962793792, Brier 0,021610995 có uncertainty đã lưu. Thiếu firm IDs/publication timestamps nên không gọi entity-disjoint OOT hoặc deployed SME PD. [Final model card](BANKRUPTCY_FINAL_MODEL_CARD.md).

Còn có Apple note schedule/facility clauses và EBMUD debt-service/covenant evidence. Đây là nguồn thật có thể đóng một case nghiệp vụ sâu. Cần nối từ tài liệu hợp đồng đến instrument, ngày hiệu lực, dòng tiền, định nghĩa covenant, adjustments, headroom và analyst review. Principal maturity bucket không đủ để suy lịch trả nợ ngày cụ thể hay DSCR.

**Bước nên làm:** chọn đúng một issuer/facility để hoàn thiện vòng phân tích. Dùng Apple cho note schedule hoặc EBMUD cho revenue-bond DSCR; không lấy covenant utility áp cho doanh nghiệp công nghiệp. Giữ draft/proposed/executed/amended terms riêng. Sau case đầu mới mở peer/sector hoặc pilot báo cáo Việt Nam; không xây thêm bankruptcy ML chỉ để tăng số thuật toán.

### 4.4. P4 — Portfolio: tính toán có kiểm tra, inputs kinh tế chưa đủ

Actual March 2026 exposure import có 9.698 observations, 141 số dư zero và UPB USD 915.208.989,12. Có Excel intake, concentration theo currency/region, movement bridge Feb–Mar, scenario, ECL, Monte Carlo và reviews. FDIC 42 quý/214.809 bank-quarter reports, WDI 122.892 observations và sovereign archives là observatory data; không phải borrower loan book.

**Điểm cần nói thẳng:** toàn bộ project không phải “không có imputation/giả định”. Bankruptcy benchmark dùng median imputation học trên train; NSMO có một số giá trị nhà phát hành impute; P4 có declared PD/LGD/EAD, 36-month bullet, monthly EIR 0,004 và scenario weights 0,7/0,3. Các báo cáo hiện đã ghi giới hạn, nhưng nên có một màn hình/sổ duy nhất để người dùng nhận ra ngay. Câu “không dự phóng” trước đây chỉ đúng cho lượt acquisition được nói tới. [ECL workflow](EXPOSURE_ECL_WORKFLOW.md), [scenario workflow](EXPOSURE_SCENARIO_WORKFLOW.md).

**Bước nên làm:** chuẩn hóa contract/exposure/obligor mapping, evidence cho actual EIR/schedule/recovery và registry assumptions. Khi chưa đủ, scenario vẫn là bài nghiên cứu sensitivity, actual EL/ECL giữ unavailable. Không nhập xác suất D3 early-entry ở D01 vào ECL cho dư nợ đang sống tháng 03/2026; population, time origin, horizon và default definition chưa khớp.

### 4.5. P5 — Structured: đã có data phong phú, ưu tiên giải quyết exception

Ngoài World Omni 2025-A reported certificates/waterfall, SOFR và legal exhibits, project đã có original XML/certificate panels:

| Panel | Tháng ghép đồng kỳ | Asset row-months | Asset keys trong deal | Bằng chứng quan trọng |
|---|---:|---:|---:|---|
| Toyota 2022-B | 51 | 2.508.991 | 77.626 | 1.122 charge-off event assets; pool/count và nhiều bucket tie-out đạt |
| Toyota 2024-B | 29 | 1.518.106 | 70.254 | 761 charge-off event assets; pool/count/gross liquidation 29/29 exact, DPD 232/232 exact |
| Nissan 2024-B | 23 | 1.154.259 | 63.688 | Pool/count 23/23 exact; event/recovery/DPD có exceptions theo kỳ |

Asset keys theo deal không đồng nghĩa unique borrowers giữa các deal. Hai Toyota là kiểm tra chuyển giao cùng issuer/servicer family, không phải hai issuer độc lập. “External issuer validation” Nissan hiện xác minh source/parser/reconciliation; chưa là external model validation.

Toyota 2024-B recovery khớp certificate chỉ 1/29 kỳ, signed residual tổng +USD 1.764.558,08. Nissan recovery 17/23 exact; tháng 07/2025 ABS-EE charge-off sum USD 655.185,56 trong khi certificate principal trên defaulted receivables là −USD 59.000,49. Đổi ranh DPD để giải thích một tháng lại làm toàn bộ panel khớp kém hơn. Những điểm này là câu hỏi nghiên cứu thực, có giá trị hơn thêm một chart. [Toyota audit](TOYOTA_2024B_VALIDATION_RESEARCH_VI.md), [Nissan audit](NISSAN_2024B_EXTERNAL_VALIDATION_VI.md).

**Bước nên làm:** xây exception ledger và recovery component bridge theo issuer, giữ raw sign, prior-period corrections, event count và cash amount độc lập. Bắt đầu nghiên cứu PD/event trên phần target đã qualify nếu đủ support; không bắt recovery phải đạt trước mọi nghiên cứu event, nhưng LGD/cashflow phải chờ recovery qualification. World Omni cần xác định Conversion Date/effectiveness và legal regimes trước khi đóng full waterfall. Nếu tài liệu công khai không giải thích được, ghi unresolved và loại scope liên quan; không tạo một số bù để residual thành zero.

## 5. Nghiên cứu ngoài repo thay đổi ưu tiên ra sao?

| Căn cứ chính thức/nghiên cứu | Điều xác nhận | Áp dụng đề xuất cho CreditAtlas |
|---|---|---|
| [Federal Reserve SR 26-2, 17/04/2026](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm) | Guidance mới thay SR 11-7 và SR 21-8, nhấn mạnh cách quản lý theo mức rủi ro và quy mô/sự phức tạp | Dossier ghi intended use, materiality, limits, owner và validation; không gọi dùng checklist là đạt chuẩn ngân hàng |
| [Revised model risk guidance](https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm) | Mức kiểm soát tùy loại model và cách sử dụng; guidance không phải một danh sách tiêu chí pháp lý cứng cho mọi tổ chức | Tách benchmark/simulation/production candidates; ưu tiên kiểm tra theo hậu quả sử dụng, không theo số test |
| [BCBS 239 implementation update, 06/01/2026](https://www.bis.org/publications/implementation-principles-effective-risk-data-aggregation-and-risk-reporting-bcbs-239-principles) | Lineage, governance, completeness và báo cáo kịp thời vẫn là vấn đề trọng tâm; đây là newsletter, không tạo yêu cầu mới | Một registry và quality/exception queue xuyên domains; đo cả latency và source freshness |
| [Moody’s Lending Suite](https://www.moodys.com/web/en/us/solutions/lending.html) | Mô tả sản phẩm nối spreading, memo, covenant và monitoring | Hoàn thiện một borrower/facility workflow đầu-cuối trước khi mở thêm model; đây là tham khảo tính năng vendor, không kiểm chứng hiệu năng sản phẩm |
| [SAS PD validation documentation](https://support.sas.com/documentation/cdl/en/edmug/67015/HTML/default/p01hsa5yl8hhm4n1jwsg3nx2uvon.htm) | Tách stability, discrimination và calibration | Model dashboard phải có cả ba cùng support, sample period và response khi không đủ dữ liệu; tài liệu phiên bản cũ chỉ làm tham khảo nghiệp vụ |
| [FICO Decision Modeler overview](https://community.fico.com/FICOCommunity/s/decision-modeler-overview?tabset-ba374=f1ada) | Tách quy tắc quyết định, analytics và optimization | Giữ model score riêng khỏi policy/cost/capacity; policy version phải được lưu độc lập |
| [CFPB HMDA limitations](https://www.consumerfinance.gov/data-research/hmda/summary-of-2022-data-on-mortgage-lending/) | So sánh năm bị ảnh hưởng bởi thay đổi định nghĩa/geography; HMDA thiếu một số thông tin underwriting | Denied share là descriptive; không dùng một disparity để kết luận phân biệt đối xử hoặc default risk |
| [SEC EDGAR API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Frames căn theo calendar; fiscal dates có thể khác, Companyfacts giữ thông tin từng fact | Dùng issuer/filing/period/unit evidence, không cộng quarterly/YTD hoặc lấy revised fact như đã biết ở quá khứ |
| [Riley et al., BMJ 2020](https://www.bmj.com/content/368/bmj.m441) | Sample size cần xét số parameters, events, prevalence và kỳ vọng performance; quy tắc EPV đơn giản chưa đủ | Lập support/precision memo trước model NSMO/D01; đây là chuyển dụng phương pháp thống kê, không phải chuẩn tín dụng bắt buộc |
| [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) và [calibration](https://scikit-learn.org/stable/modules/calibration.html) | Transform học trên train; calibration cần dữ liệu phù hợp, tách khỏi fitting | Giữ fitted preprocessing; đánh giá probability bằng Brier/log loss/reliability cùng AUC/AP; không upgrade package/model chỉ vì docs mới |
| [scikit-survival competing risks](https://scikit-survival.readthedocs.io/en/stable/user_guide/competing-risks.html) | Competing events làm thay đổi diễn giải cumulative incidence | Chỉ chọn estimator sau khi xác định event/termination/censoring và estimand; không mặc định 1−KM là xác suất default khi có payoff |
| [BIS IFRS 9 summary](https://www.bis.org/publications/fsi-summary-ifrs-9-and-expected-loss-provisioning-executive-summary) | 12-month ECL xét lifetime shortfalls do default có thể xảy ra trong 12 tháng | Cần contract/EIR/recovery timing và staging evidence trước actual ECL; formula PD×LGD×EAD đơn giản không chứng minh đầy đủ |
| [Microsoft Power Query limits](https://support.microsoft.com/en-us/excel/power-query-specifications-and-limits-in-excel?ad=us&rs=en-us&ui=en-us) | Worksheet tối đa 1.048.576 hàng; xử lý Power Query còn phụ thuộc bộ nhớ | Raw lớn giữ CSV/Parquet/DuckDB; Excel chứa dictionary, filtered extracts, aggregates và phân tích có thể refresh |

Các dòng “áp dụng” là đề xuất kỹ thuật từ việc đối chiếu với repo, không phải yêu cầu nguyên văn của tổ chức nguồn.

## 6. Chiến lược dữ liệu: lấy gì tiếp và dùng ở đâu?

| Ưu tiên | Nguồn / dữ liệu cần | Dùng cho | Trạng thái và quyết định |
|---|---|---|---|
| 1 | Freddie annual vintages theo protocol | D01 R2/R3 | Giá trị mở gate cao nhất; chờ authenticated session, pilot schema rồi batch |
| 1 | Toyota/Nissan recovery/certificate components, EX-103 versions, amendments | P5.02/P5.10, sau đó LGD | Dữ liệu chính đã có; điều tra sâu và chỉ tải tài liệu/kỳ thiếu có câu hỏi rõ |
| 1 | Instrument/covenant terms và effective dates của một issuer/facility | P3.07/P3.08 | Có tài liệu một phần; hoàn thiện chain và reconcile trước headroom |
| 2 | FHFA NMDB New/Outstanding đã tải | Market mix; mortgage context | 3.038.100 annual rows + 535.464 quarterly rows; cần tích hợp analytical mart/app/Excel, không cần tải lại |
| 2 | Bondora dated booked-loan snapshot/dictionary/changelog | P1 temporal cohort research | Đã có 789.144 rows; kiểm tra label maturity/feature timing trước fit. [Publisher](https://goandgrow.eu/en/public-statistics/) |
| 2 | Ginnie quarterly pilot + payment history/removals đúng scope | Case mortgage/MBS độc lập | Terms đã chấp thuận, chưa có session-file path; không lặp hỏi quyền đã được cấp |
| 3 | HMDA thêm release chỉ khi đóng gap comparability | D08/application monitoring | 2018–2025 đã phong phú; ưu tiên thống nhất release/cohort/geography thay vì bulk download thêm |
| 3 | NSMO questionnaire/routing/design evidence còn thiếu | D02 descriptive validity | Target/model không tự mở chỉ vì thêm questionnaire; cần quyết định estimand và support |
| 3 | Fannie annual data | Mortgage external source nghiên cứu riêng | Chỉ sau access/terms và crosswalk; không gọi là Freddie vintage |
| Phụ thuộc nghiệp vụ | Income verification, collections actions, funding cost, take-up, actual loan terms, obligor groups | P1.05/06/08, P4.03–07 | Cần dữ liệu nghiệp vụ được phép dùng. Nếu chưa có, ghi scope thiếu hoặc dùng scenario được gắn nhãn |

**Quy tắc chọn batch mới:** phải ghi câu hỏi, requirement nào hưởng lợi, missing field/kỳ nào cần bổ sung, ước lượng storage, điều kiện truy cập, parser/dictionary, expected controls và tiêu chí dừng. Source publication time, observation time, extraction time và availability time là các trường khác nhau. Không cộng số rows của các HMDA release thành số hồ sơ unique, không fuzzy-join borrowers xuyên nguồn để tạo labels.

**Excel theo đúng quy mô:** workbook cần source inventory, field dictionary, codebook, KPI/denominators, exceptions và review. Dataset hàng triệu rows không được cắt ngầm để vừa sheet. Xuất một filtered slice có manifest, hoặc Power Query lấy dữ liệu aggregate đã kiểm chứng. IDs/LEI/FIPS là text, số tiền exact có text gốc bên cạnh nếu precision Excel không đủ. Giữ raw source immutable.

## 7. Các chỉ số phân tích nên bổ sung cụ thể

| Nhóm | Phân tích tiếp theo | Công thức / grain | Điều kiện kiểm tra |
|---|---|---|---|
| Data readiness | Coverage cho chính use case | Eligible rows / candidate rows; known-label count; thời gian theo dõi; reasons | Phân hoạch exclusion, không chỉ đếm file đã tải |
| HMDA | Denial/mix theo cohort ổn định | Action 3 / actions 1–3; count-weighted với cùng activity year/release/cohort | Purchased loans/withdrawn/incomplete nằm ngoài mẫu số này; geography và threshold changes có caveat |
| Mortgage transitions | DPD migration/cure/redefault theo thời gian | Transition count / eligible adjacent pairs xuất phát cùng state | Không coi pair share là PD12; count và opening-UPB basis riêng |
| Mortgage outcomes | Event incidence theo vintage và horizon | Target đã freeze + risk-set/event/censor contract | Chỉ hiển thị uncertainty khi estimator và support hợp lệ |
| NMDB | New vs outstanding mix: rate, LTV/DTI, score, stock/flow | Chọn VALUE1 count-weight hoặc VALUE2 amount/UPB-weight | Không cộng stock với flow, không lấy trung bình tỷ lệ giữa các nhóm chồng lấn |
| ABS surveillance | DPD, gross charge-off, recoveries, net loss, reserves | Issuer-specific flow/stock definitions và source denominator | Asset aggregate ↔ certificate tie-out; residual có classification/owner |
| Corporate | Liquidity/leverage/cash conversion/debt service/headroom | Filing-specific inputs, instrument terms và covenant adjustments | DSCR/interest coverage phải đúng contract; missing input giữ unavailable |
| Model | Calibration intercept/slope, O/E, Brier/log loss, AUC/AP, subgroup/time support | Frozen scores trên cohort đã khai báo | O/E = observed events / sum predicted probability; không tính khi horizon/outcome thiếu hoặc expected events = 0 |
| Portfolio | Exposure movement, borrower/group concentration, term/maturity ladders | Same currency/as-of/ownership, đúng stock và cashflow grain | Cần actual borrower/group identity và FX policy trước global total |
| Workflow | Source freshness, unresolved exceptions, review aging | Source release/receipt/review timestamps | Review aging là operational metric, không phải credit risk score |

88 KPI và 22 quality controls đã có là catalog hiện tại. Đợt mới cần tăng tỷ lệ KPI có input hợp lệ, lineage và action, không đặt mục tiêu một số lượng KPI lớn hơn tùy ý. Một màn hình KPI tốt phải trả lời: giá trị là gì; nguồn nào; mẫu số nào; biến động do phép phân rã nào; có đủ support không; ai xử lý tiếp.

## 8. Quy tắc bắt buộc trước mọi imputation, forecast hoặc scenario mới

Tạo một `method_id` với tám phần trước khi đưa kết quả vào app: mục đích/biến/horizon; source và availability; loại missing; nghiên cứu phương pháp/baseline; công thức và parameters; validation design; uncertainty/failure cases; phạm vi sử dụng và version history. Không có phương pháp nào “chứng minh đúng” tuyệt đối từ dữ liệu quá khứ; bằng chứng cần cho thấy độ phù hợp, sai số và giới hạn ngoài mẫu.

| Loại giá trị | Ví dụ hiện có | Yêu cầu |
|---|---|---|
| Reported | Source UPB, certificate net losses | Giữ sign, unit, date và source reference |
| Derived | Count shares, ratios, movement | Ghi numerator/denominator/filter/formula và reconcile |
| Publisher-imputed / mixed provenance | Một số NSMO X fields | Ghi technical method nguồn; PUF thiếu item-level J flags nên không gán chắc trạng thái từng cell |
| Model preprocessing imputed | Bankruptcy train-median | Fit train-only, giữ missing indicators và original values; không gọi median là income/ratio quan sát |
| Model prediction | Frozen UCI benchmark probabilities | Target/population/horizon/model version/calibration rõ |
| Declared scenario | P4 PD/LGD/EAD, recovery lag, EIR, weights | Ghi ai đặt, lý do hoặc “chưa có empirical calibration”, sensitivity và intended use |
| Forecast | Chưa có forecast mới trong lượt này | Time-ordered backtest, naive benchmark, horizon-specific errors và intervals |

Không impute nhãn chưa mature/censored thành 0; không fill DTI sentinel bằng median trước semantic review; không suy PD từ denied share. Nếu nghiên cứu macro forecast, dùng dữ liệu theo thời điểm thực sự sẵn có và rolling/expanding-origin evaluation. Nếu giả định MAR/independent censoring không kiểm chứng được, phải mô tả sensitivity và selection risk. Bảng này cần áp dụng hồi tố để tập hợp assumptions hiện có, không refit benchmark hoặc mở lại final holdout.

## 9. Backlog tiếp theo, thứ tự và tiêu chí đóng

Các mã N01–N24 dưới đây là **công việc mới đề xuất**, không thay 50 requirement IDs. Thứ tự là ưu tiên thực thi, không phải lời hứa đã triển khai. Chỉ đóng khi có output và evidence tương ứng.

| ID | Ưu tiên / phạm vi | Công việc và đầu ra | Phụ thuộc | Điều kiện nghiệm thu |
|---|---|---|---|---|
| N01 | Ngay / shared | Hợp nhất completion, D01 release, data readiness vào một trạng thái nguồn | Ledger hiện tại | Tổng 26/50 tái tạo từ ledger; UI/docs không gọi 52% là D01; historical labels được giữ |
| N02 | Ngay / shared | Nối 27 parent groups tới source, release/partition, receipt, publisher/distributor, observed/as-of/retrieved time, grain, rights gate, current route/KPI/method. Đã bind HMDA 12, FHFA 9, LendingClub/Bondora 5, Treasury HAMP 2, WDI 22, Sovereign Archive 12 objects; rà 11 nhóm còn thiếu, Freddie/Ginnie theo access gate, HAMP coverage trước 2022 và provider/third-party terms. | Receipts/code map đã có; direct-source candidates researched for BLS/FHFA/Freddie/Fed/Treasury; 12 BoC–BoE edition/source objects have hash/size-verified private receipts | 27/27 groups có trạng thái kể cả no-data/access-pending; từng object có release/version, receipt/hash, source row/field/missingness evidence; mọi KPI trace tới consumer và N03 formula; API/UI/export parity; rights resolved hoặc source fenced. Hiện 16/27 groups có source-level binding, 11 còn lại. Không gộp LendingClub vintages, không biến aggregate/application/sovereign stocks thành borrower PD. |
| N03 | Ngay / shared/P4 | Registry phương pháp/giả định; gắn nhãn actual/derived/imputed/model/scenario | N02, model/scenario artifacts | Từng output số đi tới method/input; phân biệt publisher-imputed với app-imputed; không sửa frozen studies |
| N04 | Ngay / engineering | Public regression receipt, route inventory, runtime profiling | Public checkout | Pass/fail/skip theo môi trường; đo cold/warm p50/p95 riêng; giải thích suite-view timeout |
| N05 | Tiếp theo / market | NMDB New/Outstanding canonical aggregate mart | Raw FHFA đã audited | Unique source key, count/amount weighting và units đúng; suppression/null giữ nguyên |
| N06 | Tiếp theo / market | NMDB app + workbook theo geography/market/period/measure | N05 | Filter parity API/Excel; denominator/units hiện cạnh KPI; không xuất raw vượt worksheet limit |
| N07 | Cao / P5 | Toyota recovery components và exception ledger | Panels/certificates/EX-103 đã có | 51+29 kỳ có bridge; residual mỗi kỳ giải thích hoặc unresolved có bằng chứng; không ép zero |
| N08 | Cao / P5 | Nissan event/DPD/recovery exceptions theo thời gian | Nissan 23 kỳ, N07 pattern | Tái tạo ngoại lệ 07/2025 và DPD 06/2025; rule không được chọn chỉ vì khớp một kỳ |
| N09 | Cao / P5 | Surveillance release gộp các deal bằng contract riêng | N07/N08 | KPI source-backed, exception drilldown, source links, Excel và analyst finding; không gọi unresolved recovery là LGD |
| N10 | Đường găng / D01 | Freddie access, pilot annual sample, release/layout audit | Authenticated access | Official receipt/hash, parser/source counts, observed cutoff và resource budget đạt |
| N11 | Đường găng / D01 | Multi-vintage source/labels/support/temporal protocol | N10 | M01-006/007/015/016 đủ; final-access policy trước phân tích OOT; maturity và overlap audits |
| N12 | Sau R2 / D01 | Constant + logistic, then bounded boosting; calibration/freeze/OOT | N11 | Cùng target/cohort, train-only features, metrics/uncertainty, frozen selection; có thể kết luận không đạt performance |
| N13 | Có điều kiện / Ginnie | Quarterly pilot và joint key/removal semantics | Session-file path do user cung cấp | File thật/hash/layout/totals; source case riêng; không tăng Freddie vintage count |
| N14 | Song song / P1 | Bondora label/maturity/as-of qualification | Snapshot/dictionary đã có | 3-way true/false/NULL giữ đúng, country/time support; no post-booking predictors |
| N15 | Sau qualify / P1 | Booked-loan descriptive cohort và candidate temporal benchmark | N14 | Target và availability được chốt trước fit; repeat-borrower caveat; không đóng application underwriting chỉ bằng booked data |
| N16 | Cao / P3 | Một complete facility/debt-service case | Executed terms, payment/EIR evidence | Cash schedule + term lineage, amendment dates, source reconciliation, unavailable inputs có lý do |
| N17 | Sau N16 / P3 | Covenant definitions/adjustments/headroom + Excel memo | N16 | Test date/threshold/adjustments đúng scope; unknown legal applicability không trả breach badge |
| N18 | Có điều kiện / P4 | Actual contract/exposure/obligor adapter | N16 hoặc loan contracts hợp lệ | Actual schedule/EIR/group IDs và reconciled balance; no cross-currency sums |
| N19 | Sau N18 / P4 | Research EL/ECL qualification pilot | N18 + compatible PD/recovery evidence | Matching target/horizon/population, calibrated inputs hoặc assumptions rõ; staging policy và timing audit |
| N20 | Shared / delivery | Excel package conventions và filtered export parity | N02/N03 | Dictionary/KPI/exceptions/review consistent; no truncation, formula/number precision và native-engine checks |
| N21 | Shared / engineering | CI source-only, private-data test runner, incremental route modularization | N04 | Public CI không cần private data; declared skips; dependencies pinned; existing export contracts giữ nguyên |
| N22 | Shared / review | Review ownership, exception lifecycle và audit trail | N01/N03 | Assigned/reviewed/closed có evidence; authentication chỉ khi mở multi-user scope, không đổi local review thành bank approval |
| N23 | Đóng gói | Năm case-study deliverables cùng một app | Các slice đã nghiệm thu | Mỗi case có business question, data, methods, results, limitations, reproduction, analyst Excel |
| N24 | Mở rộng sau | Vietnam financial-report pilot hoặc loan-data partner | Mục tiêu sử dụng/data rights rõ | Hạch toán/đơn vị/thời điểm hợp lệ; không áp nguyên PD benchmark nước ngoài; giữ separate acceptance |

### Kế hoạch dữ liệu N02 sau khi đọc receipt, code và nguồn chính thức

| Tranche | Phạm vi và câu hỏi | Đầu ra phải ghi | Tiêu chí dừng/nghiệm thu |
|---|---|---|---|
| A — HMDA, đã bind source objects | 2018 Three-Year; 2019–2024 One-Year; 2025 Snapshot LAR/TS/MSAMD; 2025 Dynamic LAR/TS. Phục vụ application/decision mix và mô tả denied share, không phải repayment risk. | 12 receipt-backed rows, source URL, release family/as-of, row/field/LEI count đã profile, 2018 quarantine, timestamp retrieval chỉ khi receipt ghi. Giữ TS/MSAMD là QA/reference. | Hoàn tất object-level mapping. Còn kiểm API/UI/Excel parity theo release đại diện, xác nhận denominator từ source aggregation, privacy fence cho TS, và N03 method card; không cộng các release thành unique applications.
| B — FHFA PUDB/NMDB/NSMO (source bind đã làm) | Ba PUDB objects; NMDB New annual flow, Outstanding quarterly stock; performance all-geographies, national/census-areas, states; NSMO PUF v7. Giữ riêng archive, release, geography, route và estimand. | Đã ghi 9 receipt/hash records; PUDB 2,093,767 × 66; New 3,038,100 × 14; Outstanding 535,464 × 14; performance 261,856 / 25,088 / 79,968 × 13; NSMO 62,359 × 587. | Đã đối chiếu hash/count/profile và gọi reader/report trên actual data. Còn PUDB Excel, route-specific browser + Excel desktop checks, N03 method/input formula links, missingness/rights details. No cross-market sum, no fill/forecast, no aggregate-to-loan-level PD.
| C — LendingClub / Bondora (source binding done; qualification open) | Tách accepted/rejected applications, booked cohorts, outcome definitions, vintage and observation cutoff; kiểm tra feature có đúng thời điểm quyết định và target đã matured chưa. | Đã ghi 5 object: Kaggle accepted/rejected v3, Mendeley expired-loan v1, issuer dictionary và Bondora workbook; counts, periods, hash prefixes, grain, labels, rights gates và code routes. | Source binding đạt; không gộp hai accepted snapshots; vẫn cần qualify repeated borrowers, issuer fidelity, feature timing, label/event maturity, snapshot cutoff và reuse rights. 10,860 Bondora NULL giữ nguyên; no train until target, availability and OOT split are frozen. Bondora cannot substitute Freddie R2. |
| D — Freddie / Ginnie | Freddie R2/R3 sample is critical mortgage-performance work; Ginnie is a separate product and access/terms case. | Authenticate/access only through publisher workflow; exact sample/year/layout, file hash, vintage/availability, loan-month grain, status/default definition, match keys, missingness, use terms and resource estimate. Keep raw data private. | No synthetic replacement or cross-publisher fuzzy match. Start a model only after label/feature timing, sample design, rights, parser and time-split support are documented. Ginnie does not increase Freddie vintage count.
| E — Treasury HAMP and World Bank WDI | Verify HAMP coverage before 2022 and indicator-specific WDI provider/rights metadata. Keep HAMP’s selected modified-loan cohort and WDI’s latest-revised macro observations separate. | HAMP source endpoint result, available months, source profile and missing-period statement; WDI per-series provider, API update date, NULL counts, attribution and reuse status. | No substituting mirrors or interpolating missing months/values. Use HAMP only for its source-defined cohort; WDI only as macro/banking-system context, not borrower PD. |
| F — BoC–BoE Sovereign Archive, bound | Preserve four editions and revision semantics; complete route, export and analyst review. | 12 receipt-bound source objects; 42,519 entity-year rows, 16 selected metrics, per-edition as-of and row count, missing/zero/source-marker/schema-absence diagnostics, revision and conflict outputs. | Values reconcile to the selected edition; missing stays missing, zero stays zero, source markers stay visible; rights/attribution status recorded. Do not use annual stocks as retail/corporate PD/LGD or causal macro sensitivity. |
| G — finish N02/N03 & rights | Resolve route-to-source and formula trace across all 27 parent groups; separate latest/revised, point-in-time and scenario data. | Each material KPI links source release → source field → transformation → filter → numerator/denominator → unit/period → output/API/Excel; explicit rights decision or fence. | Every group has a concrete source or explicit no-data/access status; measured missingness only when receipt supports it; every forecast/scenario has a cited method, inputs, uncertainty/sensitivity and validation. Unverified values remain unavailable, not estimated. |

**Data admission rule:** before each new download, state the question and requirement it supports, the missing period/field, official endpoint and access/terms, expected size, parser/dictionary, validation totals, and stop condition. If the publisher provides no value, keep it missing. Any later estimate must have a separate documented method, source evidence, assumptions, uncertainty/sensitivity and a backtest or external comparison; do not quietly fill a gap inside a reported-data KPI.

## 10. Cách thực hiện để không lan rộng scope

**Đợt A — đóng nền tảng và dữ liệu đang có:** N01–N06, N20. Đích bàn giao: status thống nhất, data/method inventory và NMDB phân tích được trong app/Excel. Không tăng completion chỉ vì có thêm registry. Ước lượng thiết kế: 5–8 ngày làm việc một người nếu không có bug lớn; đây là giả định kế hoạch, chưa đo velocity.

**Đợt B — hoàn thiện một case nghiệp vụ sâu:** ưu tiên N07–N09 ABS, rồi N16–N17 corporate. Đích: một analyst có thể lấy KPI, xem sai lệch, đọc nguồn, ghi finding và xuất workbook cùng evidence. Đặt timebox 2–3 phiên cho mỗi source exception; nếu thiếu chứng cứ công khai thì ghi unresolved và tiếp tục phần đủ điều kiện. Ước lượng ban đầu 8–15 ngày, phụ thuộc độ rõ của hợp đồng/servicer evidence.

**Đợt C — nghiên cứu model có đủ dữ liệu:** N10–N12 là ưu tiên mortgage khi access sẵn sàng. Trong thời gian chờ, N14/N15 có thể kiểm tra dữ liệu Bondora mà không fit vội. N13 là separate case. Không đặt deadline R3 khi chưa qua N11; thời gian authenticate và chờ nguồn không nằm trong ước lượng engineering.

**Đợt D — qualification và handoff:** N18–N23 theo inputs thực có. N24 là phần mở rộng phục vụ thị trường Việt Nam, không nằm trên critical path D01. Chỉ thêm identity/roles/multi-user deployment khi có nhu cầu triển khai nhóm; giữ loopback local cho scope hiện tại.

Mười phiên làm việc đầu đề xuất: phiên 1 chốt ledger và data inventory; 2 audit assumptions; 3 đo runtime/regression; 4 NMDB mart; 5 workbook; 6 API/UI/parity; 7 Toyota recovery bridge; 8 Nissan exceptions; 9 surveillance finding/export; 10 nghiệm thu slice và cập nhật remaining gates. Nếu Freddie access đến trong thời gian này, dùng phiên chuyên biệt cho pilot N10 rồi điều chỉnh ưu tiên dựa trên support; không tự bỏ các criteria đã chốt.

Các việc hoãn: thêm deep learning/LLM scoring, SHAP dashboard cho model chưa qualify, generalized IFRS9/CECL engine, CDS curve từ OAS index, scrape toàn bộ EDGAR, public raw-data dump, viết lại toàn frontend, hoặc tăng KPI bằng các số thiếu input. Đây là lựa chọn ưu tiên, không phải loại khỏi tầm nhìn dài hạn.

## 11. Khi nào có thể tăng tỷ lệ hoàn thành?

Chỉ cập nhật một requirement sau khi source, tính toán, app/API/export và giới hạn sử dụng thỏa đúng acceptance của nó. Data acquisition mới là một bước; synthetic tests chỉ chứng minh hành vi kỹ thuật đã kiểm tra. Có thể nghiệm thu một research result âm nếu nghiên cứu đúng protocol, nhưng không gọi model không đạt là qualified scoring.

Không hứa “xong N01–N09 thì đạt 70%”: nhiều task củng cố yêu cầu đã đạt hoặc tiến thêm trong yêu cầu vẫn mở. Dùng ba bảng riêng: (a) 50 capability acceptance; (b) D01 R0–R4; (c) dataset/use readiness. Báo progress bằng việc đóng cụ thể, ví dụ recovery delta đã giải thích, một source trở thành usable, một OOT study được đánh giá, thay vì chỉ % duy nhất.

## 12. Kiểm chứng cuối và cách dùng tài liệu

Public checkout tại baseline đã chạy toàn bộ app/vendor suite: **1.670 passed, 196 skipped, 0 failed, 0 errors**, 551,26 giây. 196 skips được khai báo vì cần excluded private inputs/machine-local evidence; không tính là tests pass hoặc chứng nhận private integration. JUnit và log ở `D:\data\Codex\scratch\credit-atlas-review-20261016\`. Lượt này không chạy lại browser visual acceptance hoặc native Excel app cho toàn ứng dụng. HTTP smoke và follow-up ở §2 không thay browser QA.

Workbook đi kèm có 4 sheet: 24 nhiệm vụ, 50 acceptance items, 24 nhóm dữ liệu trọng tâm và 7 loại provenance/phương pháp. Đây là inventory phục vụ quyết định ưu tiên, không phải census toàn bộ file/dataset trong workspace. Workbook không chứa raw loan rows, credentials hay kết quả forecast mới. Các trạng thái task là đề xuất cho bước tiếp theo, không đổi completion ledger gốc. Formula totals 26/50 giữ nguyên; cập nhật N02 và Sovereign Archive không tự nâng tỷ lệ. Đã recalculate, quét không có formula error, kiểm tra sheet thay đổi trực quan và xác nhận các sheet/công thức/bảng không liên quan giữ nguyên. Chưa kiểm tra native Microsoft Excel trong lượt này.

Điểm bắt đầu được khuyến nghị: **N01–N03 trước; N05/N06 để sử dụng dữ liệu đã tải; N07–N09 để biến bộ ABS hiện có thành case surveillance sâu; mở N10/N11 ngay khi có authenticated Freddie access.** Như vậy dự án tiến về các câu hỏi tín dụng có bằng chứng và hạn chế phụ thuộc vào một cổng dữ liệu duy nhất.

## 13. Phụ lục — đủ 50 yêu cầu và điều kiện nghiệm thu

Bảng dưới trích trực tiếp ledger tại baseline. “Đạt” chỉ áp dụng phạm vi đã ghi; các giới hạn và hướng phát triển ở §4 vẫn còn hiệu lực. “Mở” không có nghĩa là chưa triển khai.

| ID | Chức năng | Trạng thái | Điều kiện nghiệm thu trong ledger |
|---|---|---|---|
| P1.01 | Dữ liệu & target | Đạt trong scope | Client/history counts reconcile; source ID không là predictor; tháng và missing sentinels có nghĩa rõ. |
| P1.02 | Application underwriting | Mở | Không dùng bill/status sau booking làm approval-time feature; có OOT và intended-use review. |
| P1.03 | Behavioral model & validation | Đạt trong scope | Không tune trên final test; random split được ghi rõ; bin rỗng không vẽ thành zero. |
| P1.04 | Decision policy | Đạt trong scope | Không tự reassignment khi vượt capacity; cost units không tự gọi là cash loss; validation comparisons là exploratory. |
| P1.05 | Affordability | Mở | Không suy income từ credit limit; DTI phải ghi denominator, kỳ và policy threshold. |
| P1.06 | Limit & pricing | Mở | Không gọi price tối ưu khi thiếu cost/take-up evidence; không mượn PD khác target. |
| P1.07 | Giải thích từng hồ sơ | Đạt trong scope | Contributions cộng về prediction đúng tolerance; references/source pinned; không gọi là nguyên nhân hoặc adverse-action reason. |
| P1.08 | Collections workflow | Mở | Behavioral score không chứng minh uplift; không tạo SLA/contact events giả. |
| P1.09 | Subgroup & monitoring | Đạt trong scope | Bỏ demographic predictors không chứng minh fairness; small groups không được gán ranking metrics; chưa có temporal drift. |
| P1.10 | Model evidence & governance | Đạt trong scope | Không refit/rescore khi mở màn; benchmark Taiwan không trở thành Vietnam PD; chưa có authenticated sign-off. |
| P2.01 | Source & run explorer | Đạt trong scope | Không gọi sample50k là toàn thị trường; không thay extraction time bằng publication time. |
| P2.02 | Panel quality | Đạt trong scope | Unknown/gap không trở thành current; không nối qua khoảng thiếu dữ liệu. |
| P2.03 | Portfolio & cohorts | Đạt trong scope | Zero UPB giữ riêng; count và balance có denominator khác; không cộng duplicate loan-months thành unique loans. |
| P2.04 | Private loan lifecycle | Đạt trong scope | Không lộ raw loan ID; không coi observed timeline là forecast; không backdate confirmation. |
| P2.05 | Transition matrix | Đạt trong scope | Không nối gaps/terminal pairs sai; năm không có pairs giữ unavailable; lifetime comparator ghi rõ scope. |
| P2.06 | Cure & redefault | Đạt trong scope | Gap/unknown phá linkage; terminal CURRENT không thành cure; follow-up thiếu không thành no-event. |
| P2.07 | Competing outcomes | Đạt trong scope | Không gọi horizon connector là monthly prediction; censored/unknown không thành negative. |
| P2.08 | Horizon risk models | Mở | Một vintage2012 chưa đủ temporal evaluation; readiness screen không là qualified score. |
| P2.09 | Observed loss bridge | Đạt trong scope | Không fill missing bằng zero; sample không representative LGD calibration; UPB không tự là economic loss. |
| P2.10 | Evidence & review | Đạt trong scope | Không sửa source bằng memo; reviewed không là authenticated bank approval. |
| P3.01 | SME source explorer | Đạt trong scope | Không cộng files thành unique borrowers nếu chưa có identity; giữ EXEMPT/unknown/cancelled. |
| P3.02 | Financial normalization | Đạt trong scope | Không ghép quarterly/YTD thành annual theo fiscal-year label; conflicts không chọn alias đẹp hơn. |
| P3.03 | Financial ratio analysis | Đạt trong scope | Amendments giữ riêng; không skip gaps/concept changes; không đổi cash interest thành expense; operating-income/OCF proxies chưa là EBIT ICR, DSCR hoặc covenant. |
| P3.04 | Bankruptcy benchmark | Đạt trong scope | Không pool five horizons thành một PD; thiếu firm IDs/publication dates nên chưa entity-disjoint/OOT. |
| P3.05 | SBA outcomes & cohorts | Đạt trong scope | Terminal snapshot không là fixed-horizon PD; post-outcome fields không làm approval predictors. |
| P3.06 | Corporate credit memo | Đạt trong scope | Reviewed là self-declared analyst status; không issuer PD hoặc credit approval; thiếu source mới không ghi đè capture cũ. |
| P3.07 | Covenant workbench | Mở | Thiếu terms thì không gắn actual breach badge; SEC generic ratios không thay contract definitions. |
| P3.08 | Debt & cash-flow schedule | Mở | Principal buckets không là exact payment dates, carrying debt, EAD hoặc DSCR; after-year-five open ended; debt/lease families không cộng overlap. |
| P3.09 | Sector & concentration | Đạt trong scope | Booked SBA program không đại diện toàn bộ SME economy; approval amount không tự là EAD. |
| P3.10 | Business review/export | Đạt trong scope | Không fuzzy-match SBA name với SEC để tạo labels; không trộn reporting grains; owner chưa authenticated. |
| P4.01 | Typed exposure & Excel intake | Đạt trong scope | File≤20MB/50000positions; formula inputs/unsafe numeric precision bị reject; missing risk không thành zero. |
| P4.02 | Reconcile & concentration | Đạt trong scope | Không cộng cross-currency; source observations không tự là borrower concentration; reported amount khác EAD. |
| P4.03 | Research expected loss | Mở | Không mượn PD khác target; actual source import vẫn EL unavailable nếu không có risk inputs. |
| P4.04 | ECL & staging | Mở | Bullet/EIR/recovery terms hiện minh họa; stage3/POCI/revolving policies không mặc định supported; chưa accounting compliance. |
| P4.05 | Scenario & stress | Mở | Không gọi macro-calibrated stress khi chỉ có assumptions; excluded positions không bị gán zero loss. |
| P4.06 | Movement bridge | Đạt trong scope | Missing record không là default/payoff; currency migration không là FX P&L; residual phải giữ rõ. |
| P4.07 | Tail risk & concentration | Mở | Correlation/recovery chưa calibrated; thiếu obligor linkage; finite tails/CI unavailable giữ đúng; chưa capital approval. |
| P4.08 | Bank observatory | Mở | USD thousand giữ đúng; institution event không là borrower default; reporting date không tự là availability date. |
| P4.09 | Country observatory | Mở | Không thay missing bằng latest; ratio không cộng thành tổng; current region/income labels không historical classification. |
| P4.10 | Finance review package | Mở | Reviewed không là human-authenticated sign-off; Excel notes không ghi ngược app; source values không bị sửa bởi memo. |
| P5.01 | Deal & terms catalog | Mở | Chưa xác minh đầy đủ agreements/amendments/legal state; terms không mặc định full contractual waterfall. |
| P5.02 | Collateral pool | Mở | Aggregate pool reports không là asset-level persistent panel; Ginnie/ABS-EE loan-level tracks còn thiếu. |
| P5.03 | Cash-flow projection | Mở | Reported history không được gọi là projection; chưa có complete collateral contracts. |
| P5.04 | Sequential waterfall | Mở | Cash/balance conservation; reviewer prior obligations có giả định; không gọi unconditional legal compliance. |
| P5.05 | Tranche & triggers | Mở | Stage shortfalls không cộng thành credit loss; không prorate pool loss thành tranche loss; unsupported triggers giữ gap. |
| P5.06 | Scenario valuation | Mở | Treasury/index OAS không là deal quote; không gọi market-calibrated ABS price. |
| P5.07 | Bond sensitivity | Mở | Scope coupon-date benchmark; chưa dirty/clean/accrued/spread curve của mọi actual security. |
| P5.08 | CDS credit curve | Mở | Index OAS không thay CDS quotes; risk-neutral probability không thay borrower real-world PD. |
| P5.09 | Position & scenario comparison | Mở | Index không là executable price; actual exposure representations không double-count cùng underlying risk. |
| P5.10 | Surveillance & numerical evidence | Mở | Không bỏ dropped amendments/unsupported triggers; chưa live surveillance event feed. |

[Excel kế hoạch và inventory](reviews/CreditAtlas-Review-Next-Plan-2026-10-16.xlsx) — có bộ lọc, trạng thái công việc có thể chỉnh và công thức tổng hợp tiến độ.
