# Cập nhật tiến độ Credit Atlas — 15/10/2026

## Cập nhật tiếp theo — 16/10/2026

### Target-feasibility panel trong app D02

Đã bổ sung API `/api/nsmo-target-feasibility` và panel trên `/nsmo`: chọn một C
landmark/khoản vay hoặc mọi C landmark theo quý, lọc vintage, xem outcome/censor
theo vintage và support theo quý. Endpoint chỉ phục vụ aggregate receipts đã xác
minh đúng SHA-256 PUF; không xuất ID, loan rows hay target labels. Warning giải
thích distinct support không phải PD, nhất là khi landmark lặp.

QA: **1.646/1.646 local tests PASS**, Edge headless **6/6 PASS** (desktop/mobile,
không có page errors); API route và hash mismatch được test. Private browser receipt:
`artifacts/private/nsmo-target-feasibility-browser-qa-20261016/receipt.json`.

Public mirror có source-only feasibility audit, API/UI và docs protocol.
Regression chạy trên bản mirror mới đạt **1.450 passed, 196 skipped** trong
284,84 giây; skip là các test cần private payload/evidence theo public skiplist.
`node --check` cho `app.js` và `nsmo.js` đều pass.

Đối chiếu Technical Documentation v7.0 mục 8–9: `Analysis_Weight` kết hợp
sampling weight với non-response adjustment; FHFA cảnh báo simple-random-sample
SE sẽ bị thấp và khuyến nghị survey procedure. PUF có 587 trường nhưng chỉ chứa
weight, không có PSU/strata/replicate-weight field. Vì vậy model thử nghiệm sau
này chỉ có thể báo hiệu năng nội bộ sample nếu chưa lấy được phương pháp variance
thích hợp; không thể gọi là population PD hay suy luận thống kê.

## D02-3/5 — kiểm tra feasibility target 12 tháng

Chạy audit aggregate-only trên toàn bộ PUF: 62.359 hồ sơ, 51 snapshot quý, tạo
147 hàng nhóm quý × trạng thái gốc, cộng 36 nhóm vintage × baseline state, không
xuất record/ID và không tạo nhãn target. Thử định nghĩa bốn quý tiếp theo với cohort C chính, cohort trạng thái
1/2 tách riêng; mã 3–6 là 90+ ngày, còn 7/8/9 giữ riêng. Trong các snapshot C
có đủ cửa sổ quý, 2.174 lần gặp trạng thái 90+ được quan sát, 738.773 snapshot
có đủ bốn quý không gặp 90+, 42.236 có đóng khoản vay trong cùng tháng với
snapshot nên thứ tự chưa biết, 83.092 bị cạnh tranh bởi khoản vay đóng trước
snapshot kế tiếp và 6.196 gặp trạng thái M/S mất quan sát. Đây là baseline
snapshots lặp lại theo một khoản vay, không phải số khoản vay độc lập hay tỷ lệ
default/PD. Khử trùng snapshot lặp cho thấy khoảng **59,7 nghìn khoản vay duy
nhất** từng có baseline C và full horizon; khoảng **750 khoản vay** có ít nhất
một C baseline cho kết quả 90+ trong bốn snapshot kế tiếp. Các kết quả theo class
không loại trừ nhau giữa nhiều baseline của cùng loan.

Tỷ trọng C baseline snapshot bị censor/ambiguous thay đổi theo vintage band:
2013–16 khoảng **15%**, 2017–19 **23%**, 2020–21 **8%**, 2022–24 **10%**. Đây là
tín hiệu selection/censoring khác nhau, chưa xác định nguyên nhân; complete-case
training có thể làm đổi thành phần vintage. Feasibility synthetic tests: **10/10
PASS**; private
receipt: `artifacts/private/nsmo-target-unique-vintage-20261016/receipt.json`.

Kiểm tra anchor một-dòng-mỗi-khoản-vay làm lộ độ nhạy của target: chọn C snapshot
đầu tiên có đủ horizon cho 59.703 khoản vay, nhưng chỉ có **156** outcome 90+;
dùng mọi C landmark tạo 2.174 positive snapshots và khoảng 750 distinct loans có
ít nhất một positive window. Đây là hai estimand khác nhau. First C cũng không
phải origination date/quarter, nên chỉ là sizing diagnostic; chưa tạo target.
Receipt mở rộng: `artifacts/private/nsmo-target-anchor-vintage-20261016/receipt.json`.

Kết luận: dữ liệu đủ để tiếp tục thiết kế một endpoint theo trạng thái snapshot,
nhưng chưa đủ để freeze target cho modeling. Cần giải quyết competing risks,
censoring/selection, cách xử lý cùng-tháng, và sample design/variance trước khi
ước lượng. Chi tiết và protocol còn mở:
[target feasibility](NSMO_TARGET_FEASIBILITY_VI.md).

## D02 tiếp tục — questionnaire và wave comparability

Đã tải riêng **22 questionnaire package FHFA** cho wave 1–46, lưu source hashes
và private receipts ngoài Git. Audit actual PUF×SAS đạt **14.674/14.674 ô**
(319 survey variables × 46 waves), **0 unmapped values**. **130/319** trường có
ít nhất một wave toàn bộ là mã `-3` not-asked; **188/319** có giá trị được gán
trong cả 46 wave; **76/319** có mã `-2` not-applicable. Coverage theo field được
thêm vào dictionary của `/nsmo`; đây là presence/missingness evidence, không
phải bằng chứng measurement invariance.

Đã phát hiện thang khác nhau rõ ở `x14a` / `x14a_1` (Important/Not important vs
Very/Somewhat/Not at all) nên không được gộp mã 1/2. `x20j` thể hiện giá trị của
đối chiếu PUF/SAS: câu trả lời xuất hiện ở waves 13–24, còn parser-derived range
trong field map có thể gán nhầm. 22 questionnaire PDF đã được lấy; phép tách
question-number tự động chỉ là locator vì numbering và PDF hai cột gây nhiễu.
Review wording, routing, respondent role và scales bằng tay vẫn còn mở.

Pilot credit-relevant item locator tìm thấy exact item phrases của `x05f`,
`x88d/e/f`, `x93b` và `x94a` trong **22/22 questionnaire packages**. SAS formats
nhất quán: PVERYFM cho credit familiarity/payment hardship/liquidity, PAGREEFM
cho late-payment/default attitudes. Đây là ứng viên cho mô tả trend sau review
sample/mode/routing/weights, không phải origination predictor; xem
`docs/data/nsmo-v70-wave-item-comparability.csv`.

Focused NSMO regressions: **16/16 PASS**. Full app/vendor suite sau thay đổi:
**1.634/1.634 PASS** trong 339,63 giây. Chưa định nghĩa target/PD hay chốt risk
set/variance; NSMO tiếp tục là D02 riêng, không ghép Freddie D01. Chi tiết:
[wave comparability audit](NSMO_WAVE_COMPARABILITY_AUDIT_VI.md).
Edge browser acceptance cho phần coverage mới đạt **4/4 PASS**, không có lỗi
JavaScript; xác nhận trường `x20j`, `x14a` và `x14a_1` hiển thị đúng observed /
not-asked ranges trong dictionary (`artifacts/private/nsmo-wave-coverage-browser-qa-20261015/receipt.json`).
Public source-only suite with key-item pilot: **1.438 pass, 196 skip**; skips
require excluded private inputs or machine-local evidence.
Raw questionnaire PDFs and exact field-wave counts remain private.

## D02 tiếp tục — domain analytics và field dictionary

Đã hoàn thành crosswalk chính thức **587/587** cột PUF ↔ Appendix C/SAS labels,
**59 SAS formats với 377 value labels**, và đưa tra cứu 587 trường
vào trang `/nsmo` (search theo tên cột, nhãn, family, question/use gate; xem wave,
timing, codebook page và nhãn giá trị). Thêm API `/api/nsmo-dictionary`, chỉ trả
metadata đã làm sạch; không có PUF rows hay IDs.

Tiếp tục đọc full PUF qua một audit streaming mới: **30 origination mortgage/
borrower attributes, 5 VantageScore-at-origination fields, 51 quarterly
respondent-score fields và 23 quarterly forbearance fields** — tổng 109 trường,
0 giá trị sai SAS domain. Thêm `/api/nsmo-domains` và UI cho borrower/mortgage
mix, score bins/coverage, forbearance, termination, và ma trận chuyển trạng thái
unweighted hoặc Analysis_Weight descriptive. Edge QA chạy với PUF local thật,
không có lỗi trình duyệt; xác nhận 46 survey waves và các denominator/selector.

Kết quả minh họa: `score_orig_r` có score category ở **61.897/62.359 mortgage
(99,26%)**. Q3/2025 forbearance có **110/26.222 câu trả lời mã 1/2 = 0,4195%**;
weighted descriptive share là 0,4987%, không có design-based variance. Đây không
phải tỷ lệ default. FHFA page hiện vẫn ghi bản mới nhất v7.0 cập nhật 27/05/2026;
không có PUF mới hơn để tải khi kiểm tra lại.

Audit trọng số Appendix D Table 1 độc lập với raw PUF đạt **462/462 ô khớp**
phần trăm đã công bố sau làm tròn (7 X05 fields × 11 cohort years × purchase/
refinance × 3 responses; sai khác lớn nhất trước làm tròn 0,4986 điểm phần
trăm). Đây là consistency check cho một bảng mô tả, không xác nhận variance
estimator hay target performance.

Public mirror regression (source-only checkout): **1.427 passed, 196 skipped**
as explicitly listed tests requiring excluded private files. NSMO public subset:
**33/33 PASS**. The sanitized dictionary/value-label CSVs are included publicly;
private PUF, rows, and audit receipts remain excluded.

State audit 51 quý: 0 mã ngoài domain; 26.357 khoản đang mở và 36.002 đã chấm
dứt theo `Close_Status`; mọi mã A trong panel thuộc khoản đã chấm dứt, B không
xuất hiện, và 678 khoản không có quý quan sát C/1–9. Codebook có chú giải close
status tham chiếu tên `close_status_1224` cũ; v7.0 PUF thực tế dùng
`Close_Status_0925` và sample chỉ có mã 1/2 (dù SAS format có cả 3/4). Không
được suy diễn risk set/PD từ các kết quả mô tả này. D02-2 mapping/benchmark đã
xong, review variants còn mở; D02-3 state/transition profile xong nhưng formal
risk-set protocol còn mở; D02-4 domain views đã mở rộng, còn variance/target
design và remaining domain review. Regression toàn repository sau domain build:
**1.628/1.628 PASS** (361,97 giây), focused NSMO **38/38 PASS**, Edge browser QA
PASS. D01 không đổi **26/50 = 52%**.

Nguồn chi tiết và giới hạn tại [D02 build plan](NSMO_D02_CASE_BUILD_PLAN_VI.md)
và [NSMO source review](D01_NSMO_SOURCE_REVIEW_VI.md); PDF FHFA đã được tải và
đối chiếu từ Appendix C/D, Technical Report, SAS Labels/Formats.

## NSMO D02 workspace — first descriptive slice

Sau khi người dùng cho phép hoàn tất acknowledgement Notice/Terms của FHFA,
đã tải riêng NSMO v7.0 và hoàn thành audit cấu trúc/code domain. Trang `/nsmo`
và API `/api/nsmo-profile` hiện phục vụ hồ sơ tổng hợp đã ràng buộc với hash,
receipt tải xuống và audit; giao diện xem trạng thái theo quý, mix vintage và
chất lượng `analysis_weight`. API không trả row hoặc ID. Không dựng at-risk
denominator, event rate, PD hay target và không gộp với Freddie D01. UI/API
acceptance cho lát cắt ban đầu đạt; coverage đầy đủ, field-by-field codebook,
risk-set/censoring rules và target protocol vẫn còn mở. Full suite hiện tại
**1.606/1.606 PASS**, focused NSMO **16/16 PASS**; D01 vẫn **26/50 = 52%**.
Chi tiết: [D02 build plan](NSMO_D02_CASE_BUILD_PLAN_VI.md),
[NSMO source review](D01_NSMO_SOURCE_REVIEW_VI.md) và
[test suite](TEST_SUITE_2026-10-15_VI.md).

## Mức hoàn thành theo sổ nghiệm thu

**26/50 yêu cầu đã có bằng chứng nghiệm thu đầy đủ: 52%.** Tỷ lệ đếm theo yêu cầu, không phải ước lượng giờ công hay mức độ sẵn sàng ngân hàng. Các module:

| Module | Đã nghiệm thu | Còn mở |
|---|---:|---:|
| P1 — Tín dụng cá nhân | 6/10 | P1.02, P1.05, P1.06, P1.08 |
| P2 — Mortgage | 9/10 | P2.08 |
| P3 — Tín dụng doanh nghiệp | 8/10 | P3.07, P3.08 |
| P4 — Danh mục tín dụng | 3/10 | P4.03–P4.05, P4.07–P4.10 |
| P5 — Chứng khoán hóa / thị trường | 0/10 | P5.01–P5.10 |
| **Tổng** | **26/50** | **24 yêu cầu** |

## Công việc mới trong lượt này

Tải và profile workbook Loan Dataset do trang Go & Grow công khai: 789.144 khoản vay, 31 cột, dictionary 31 trường, 789.144 ID duy nhất. Nhãn `has_default_within_12_months` có 86.618 true, 520.246 false và 182.280 NULL; nguồn định nghĩa NULL là chưa đo đủ. Ngày phát hành mới nhất là 30/06/2026; ngày hành động mới nhất trong workbook là 20/07/2026.

Kết quả này được ghi làm **partial evidence cho P1.02**, không nâng trạng thái nghiệm thu. File có performance sau giải ngân nhưng thiếu decision timestamp, requested amount, bureau và population đơn từ chối. Thu nhập tổng hợp cũng chưa có timestamp chứng minh đã sẵn sàng tại lúc quyết định. Prosper có schema loan/listing-time nhiều trường hơn, nhưng dữ liệu loan-level qua API cần tài khoản và file hiệu suất tháng cần Data License Agreement; chưa nhập dữ liệu vào workspace.

Chi tiết: [nghiên cứu Bondora/Go & Grow và Prosper](BONDORA_PUBLIC_DATASET_RESEARCH_VI.md). Bản gốc, profile và receipt chỉ lưu trong thư mục private. Sổ 50 yêu cầu cập nhật mốc ngày và giữ trạng thái P1.02 mở: [COMPLETION_REQUIREMENTS_50.json](COMPLETION_REQUIREMENTS_50.json).

Với P2.08, Fannie Mae thông báo bản primary dataset mới nhất bao phủ acquisition/performance đến Q1 2026; dữ liệu loan-level được tải qua Data Dynamics sau đăng ký và chấp thuận terms. File sample công khai hiện có chỉ hỗ trợ định dạng/thiết lập cơ sở dữ liệu, không thay thế các vintage đủ lớn để kiểm chứng horizon. Nguồn: [Fannie Mae Single-Family Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data).

P5: đã tải bộ agreement closing ngày 29/01/2025 và Omnibus SSA Amendment đề ngày 13/01/2026 từ EDGAR; 9 văn bản/index được hash, filing indexes khớp và 19 mệnh đề điều khoản đã được kiểm tra trên bản gốc. Amendment đổi cách xác định delinquent/defaulted receivables: ngưỡng là 40 USD trước `Conversion Date`, 10% khoản phải trả từ ngày đó; ngày chuyển đổi chưa được ghi trong amendment. Kết quả là partial evidence P5.01/P5.04/P5.05/P5.10; chưa nâng acceptance vì Conversion Date/effectiveness package chưa rõ và điều khoản chưa tích hợp vào app.

Chi tiết: [nghiên cứu executed agreements và amendment World Omni 2025-A](WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md).

Tiếp tục P5, đã tải trực tiếp 20 filing ABS-EE liên tục từ SEC (01/2025–08/2026): 880.773 asset rows, XML gốc 3,21 GB lưu gzip lossless 100,8 MB. Tổng dư nợ XML khớp đến cent với `Pool Balance + YSOA` ở 20/20 kỳ. XSD cho thấy một số asset có ending balance âm; tính cả chúng thì account count khớp 16/20 kỳ, còn 4 kỳ lệch -1, trong đó tháng 08/2026 khớp tuyệt đối. 11 kỳ trùng mirror có 8 trường cốt lõi khớp trên toàn bộ asset keys. Đã tạo panel Parquet theo 20 tháng và 19 bảng chuyển trạng thái mô tả; 937 key không còn xuất hiện sau 07/2026 chưa được gán nguyên nhân. **XSD/field profile và monthly aggregate KPI timeline đã được tích hợp vào ABS-EE profile trong app; individual-loan drilldown chưa tích hợp.** Tổng nghiệm thu vẫn **26/50 = 52%**.

Từ certificates, 31+ delinquency tăng 0,46% lên 2,45%; 61+ kết thúc 0,74% (đỉnh 0,76% tháng 12/2025); annualized current net-loss ratio tháng 08/2026 là 0,98%, four-month average là 0,72%; cumulative net loss là $10,74M/0,8228% original principal. Reported delinquency trigger là NO ở 20/20 kỳ. SEC XSD xác nhận `currentDelinquencyStatus` là số ngày quá hạn; audit ghép vào bốn bucket 31–60/61–90/91–120/121+ và khớp cả balance lẫn account count ở **200/200** phép đối chiếu. `Conversion Date` vẫn chưa xác định nên không tái tính delinquent/defaulted receivable theo dollar threshold trong amendment.

Chi tiết dữ liệu, KPI, exceptions và kế hoạch tiếp theo nằm trong [research note World Omni 2025-A](WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md), [official ABS-EE acquisition receipt](../data/private/structured/woart-absee-history-948a4d8e4f18/acquisition-complete.json), và [profile/đối soát receipt](../artifacts/private/woart-absee-official-profile-0c8de9d2359d/receipt.json).

Audit tiếp theo đã xác minh enum `zeroBalanceCode` theo Auto Loan XSD và kiểm tra toàn bộ 19 cặp tháng. Quan sát được code `1` prepaid/matured và code `4` charged-off; trên asset chuyển balance khác 0 sang 0 có 21.055 transition, gồm 20.108 code 1, 938 code 4, 9 transition thiếu code. Tổng 6.445 lượt key không xuất hiện ở filing kế tiếp đều đã có balance 0 nhưng code trống ở snapshot trước; riêng 07→08/2026 là 937 key. Không có bằng chứng để gán nguyên nhân biến mất. Audit vẫn là partial evidence cho P5.02/P5.05/P5.10, không đổi tổng **26/50 = 52%**. Chi tiết: [audit zero-balance và key bị thiếu](../artifacts/private/woart-absee-zero-balance-audit-75bdd262ce0b/audit.json).

Đã profile thêm 15 trường cash flow/credit theo XSD trên 880.773 dòng, không có lỗi parse decimal và cross-check cho thấy 939/939 code 4 đi cùng `chargedoffPrincipalAmount`. PTI có 3.090 NULL, 226 row-months lớn hơn 1; `recoveredAmount` có 561 giá trị âm; các khác biệt repo indicator/proceeds được giữ mô tả do có thể khác thời điểm ghi nhận. Đơn vị percentage chưa được ép thành percent display; cần xử lý outlier trước khi dùng trong model. Chi tiết: [audit field semantics và missingness](../artifacts/private/woart-absee-field-semantics-audit-fafadee77978/audit.json), định nghĩa nguồn [17 CFR Schedule AL](https://www.ecfr.gov/current/title-17/chapter-II/part-229/subpart-229.1100/section-229.1125).

Tiếp tục audit feature: 226 quan sát PTI > 1 đến từ 12 khoản duy nhất, cả 12 lặp qua nhiều filing; raw `9.9999` chiếm 111 row-month. Có 561 recovery âm trên 466 khoản, trong đó 71 khoản lặp âm qua nhiều kỳ; signed sum `-553,976.89` source units. Đã thêm script tái tạo audit và đưa summary, theo dõi theo tháng, cảnh báo giữ nguyên scale/dấu vào ABS-EE coverage UI. Bốn kỳ account count thấp hơn certificate đúng một khoản; balance vẫn tie-out 20/20, số dòng dư nợ âm không giải thích trực tiếp được ngoại lệ. Không có yêu cầu nào được nâng nghiệm thu chỉ nhờ phần phân tích này; tổng vẫn **26/50 = 52%**.

Artifact và cách dựng lại: [feature anomaly audit](../artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/audit.json), [receipt](../artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/receipt.json), [audit script](../scripts/audit_woart_absee_feature_anomalies.py).

**Cập nhật tiếp theo:** đã tải đủ 51 filing ABS-EE tháng liên tiếp của Toyota 2022-B (04/2022–06/2026), dựng panel **2.508.991 row-months / 77.626 asset keys / 62 trường**, và kiểm tra hash 51 partition cùng 50 cặp tháng. Có 1.122 khoản có charge-off amount dương đúng một tháng; code 4 sau đó lặp lại, nên event được neo vào tháng đầu, không đếm snapshot lặp. 58.196 key rời filing kế tiếp đã có balance zero trước đó: 58.158 code 1, 38 code 3. EX-103 định nghĩa ổn định 32/32 qua 51 filing; recovery trong kỳ bao gồm proceeds bán xe và giữ dấu âm/dương. Dựng feasibility cho rolling servicing target: 2.419.178 at-risk row-months; horizon 6/12/24 tháng có event, competing exit và right-censoring tách riêng. Receipt vẫn đánh dấu nhãn **chưa đủ điều kiện train**, không phải origination PD. UI đã có timeline, event definitions, risk-set table và 51 tháng chi tiết. [Toyota panel audit](../artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/audit.json), [target feasibility](../artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/audit.json), [EX-103 profile](../artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/profile.json). Nghiệm thu vẫn **26/50 = 52%**.

**Bước validation trước khi model:** audit split OOT có embargo để outcome train kết thúc trước feature test. H6: train 04/2022–06/2024, embargo 07–12/2024, test feature 01–12/2025 (400.930 row-months; 1.189 event). H12: train 04/2022–06/2023, embargo 07/2023–06/2024, test 07/2024–06/2025 (486.182 row-months; 2.735 event). Cùng asset xuất hiện qua thời gian (40.093/46.269 khoản overlap), vì vậy cần cluster uncertainty theo loan; chưa có validation/calibration window thứ ba và H24 thiếu history cho test 12 tháng trung thực. **Chưa fit model, chưa có kết quả AUC/calibration**. [Temporal split audit](../artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/audit.json), [script](../scripts/audit_toyota_2022b_temporal_split_feasibility.py).

**Đã thêm certificate độc lập:** lấy 51 SEC Form 10-D EX-99.1 Servicer’s Certificate cho đúng 51 tháng ABS-EE. Pool balance và số hợp đồng dương exact 51/51; event count và tổng `chargedoffPrincipalAmount` exact với số liquidated contracts/gross principal 51/51; 4 bucket delinquency đối soát cả count/balance **408/408**. Đây xác nhận khả năng dùng loan-level event và DPD cho surveillance của Toyota 2022-B. `recoveredAmount` chỉ exact với aggregate net liquidation proceeds 2/51; ở 49 tháng còn lại asset sum cao hơn, signed tổng delta +$2.058.647,06, chưa rõ nguyên nhân nên giữ riêng, không làm LGD. UI đã thêm chart cặp asset/certificate và bảng delta từng tháng. [10-D acquisition](../data/private/structured/toyota-2022b-10d-certificates-941fa44791c8/acquisition-complete.json), [tie-out audit](../artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/audit.json), [receipt](../artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/receipt.json).

**Feature/prediction-clock audit:** 8 feature candidates đều present trên H12 train (999.342) và test (486.182) at-risk rows. Credit score, PTI, original amount và vehicle value ổn định theo loan trong panel; geographic field đổi ở 2.870 khoản/55.558 later row-month values, cần provenance review. SEC filing lag là 20–30 ngày, median 27; OOT prediction clock phải là filing availability date hoặc internal feed có timestamp chứng minh sẵn sàng trước đó. [Feature availability audit](../artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/audit.json), [script](../scripts/audit_toyota_2022b_feature_availability.py).

## Hàng đợi theo plan

1. **P1.02:** tiếp tục tìm/đánh giá application-level có decision timestamp, requested terms, decision/reject outcomes, feature timestamps và performance; không tính score/reject inference từ các population không khớp.
2. **P2.08:** cần thêm mortgage vintages có quyền truy cập và maturity/censoring đủ cho horizon; Clarity vẫn cần đăng nhập.
3. **P3.07/P3.08:** cần amendment chain, effective dates, payment calendars, facility utilization và cash-flow evidence đủ để đối chiếu covenant/debt schedule.
4. **P4.03–P4.10:** bổ sung liên kết khoản vay/dữ liệu tổn thất và inputs PD–LGD–EAD, ECL, staging, stress, tail risk và review package.
5. **P5.01–P5.10:** tiếp theo truy nguyên bốn sai khác account count của WOART, hoàn thiện individual-loan drilldown có kiểm soát, giải thích recovery deltas Toyota bằng cash/classification/reversal definitions, xác minh vì sao geography đổi và khóa prediction timestamp/ingestion policy; rồi tìm thêm issuer/deal cho validation/calibration độc lập trước khi huấn luyện rolling servicing target. Conversion Date/legal trigger, recovery tail/LGD, H24 holdout và valuation/CDS data vẫn mở. Panel/certificate/feature audits mới chỉ thêm evidence, chưa đổi trạng thái nghiệm thu.

Chỉ đóng từng yêu cầu khi evidence thỏa đúng acceptance nguyên gốc trong sổ. Không tính việc tải thêm dữ liệu là phần trăm nghiệm thu nếu chưa lấp được các điều kiện đó.

**Checkpoint tiếp theo — Toyota 2024-B:** thêm một deal SEC 10-D + ABS-EE để thử tái lập pipeline. Thu được 29 kỳ ghép liên tục (04/2024–08/2026), 1.518.106 row-months / 70.254 asset keys / 62 fields. Certificate tie-out exact 29/29 pool balance, positive contract count, liquidation count và gross principal; 232/232 DPD bucket count/balance. Có 761 unique assets với charge-off dương, mỗi event chỉ ở một tháng và tháng đầu code 4 khớp 761/761. Recovery chỉ exact 1/29; 28 kỳ còn lại delta asset `recoveredAmount` trừ certificate net proceeds đều dương, tổng +$1.764.558,08. EX-103 nói recovery bao gồm repossession proceeds trong khi certificate công bố nhiều proceeds/recovery rows; nguyên nhân chênh lệch vẫn chưa được chứng minh. App ABS-EE coverage hiện có card Toyota 2024-B, chart và bảng 29 kỳ; browser QA pass. Đây là trust thứ hai nhưng cùng Toyota issuer/servicer family, nên chỉ là transfer validation nội bộ, chưa nâng phần trăm hoàn thành và không cho phép fit/claim PD hoặc LGD. Xem [research note](TOYOTA_2024B_VALIDATION_RESEARCH_VI.md), [panel audit](../artifacts/private/toyota-2024b-absee-panel-audit-148e4a9f9a76/audit.json), [certificate tie-out](../artifacts/private/toyota-2024b-certificate-tieout-6223784d25dd/audit.json), [browser QA](../artifacts/private/toyota-2024b-validation-ui-qa-7188d1df7c2a/receipt.json). Sổ giữ **26/50 = 52%**; P5 partial evidence được ghi mới, chưa pass requirement.


**External issuer checkpoint — Nissan 2024-B:** ghép 23 tháng ABS-EE + 10-D (10/2024–08/2026), dựng panel 1.154.259 row-months / 63.688 asset keys / 63 fields; union schema giữ hai trường Nissan-only. Pool/count exact 23/23; positive charge-off count 20/23; first code-4 count 21/23; gross principal 21/23; first-code-4 amount 20/23; DPD count+balance 178/184; recovery exact 17/23, signed delta +$8.859,23. Đã bổ sung toàn bộ 10-D surveillance KPIs: monthly net loss identity và cumulative-loss sum khớp chính xác 23/23; current ratio 0,08%→0,56% (range −0,39%–0,86%), four-month average 0,02%→0,26% (range −0,01%–0,53%); delinquency trigger 4,90% báo No cả 23 kỳ; app có chuỗi 23 tháng cho loss ratios, cumulative loss, delinquency, extensions và reserve. Monthly loss thấp nhất −$316.637,01 (07/2025), cao nhất $775.360,20. 01/2025 có 1/31 code-4 zero-chargeoff nhưng principal exact; 02/2025 có 2/37 zero-chargeoff và principal lệch $44,66; 08/2025, 54 positive rows/principal exact dù chỉ 24 first code-4. 07/2025 còn mismatch: 33 first rows $577.420,34 + 3 repeated $77.765,22, nhưng certificate ghi 1 receivable/−$59.000,49; chưa xác định adjustment/reversal ở receivable nào. Negative 10-D ratios are retained and the chart renders them inside the axis; regression ABS browser/mobile QA pass. Xem [Nissan research](NISSAN_2024B_EXTERNAL_VALIDATION_VI.md), [panel audit](../artifacts/private/nissan-2024b-absee-panel-audit-8b5590abd3d5/audit.json), [certificate tie-out](../artifacts/private/nissan-2024b-certificate-tieout-d7a71f85c77c/audit.json), [live submissions audit](../artifacts/private/nissan-2024b-submission-refresh-a26fc17a6676/audit.json), [recovery/DPD audit](../artifacts/private/nissan-2024b-recovery-dpd-exceptions-71362b31b1c1/audit.json), [DPD boundary audit](../artifacts/private/nissan-2024b-dpd-boundary-audit-762c0a8bcdf2/audit.json), [browser QA](../artifacts/private/nissan-2024b-external-ui-qa-cbcdea438399/receipt.json). Sổ vẫn **26/50 = 52%**; evidence một phần cho P5.02/P5.10.

**Tiếp tục critical path D01 mortgage:** chạy lại browser QA với dữ liệu thật, mới nhất 25/25 checks PASS; screenshot desktop/mobile, lifecycle, loss, transitions và model gates được lưu trong [receipt](../artifacts/private/browser-qa-f35adbcaeddf/receipt.json). Tải từ Freddie Mac official page Release 47 Sample Files + File Layout tháng 07/2026 để kiểm thử ingestion: 31 trường origination/35 trường performance khớp layout; bộ ví dụ có 1.000 origination IDs và 12 performance IDs nhưng overlap bằng 0, vì vậy không ghép thành panel và không tính là annual vintage. Bằng chứng ở [research note](FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md), [audit](../artifacts/private/freddie-release47-reference-audit-c3ce87022b8b/audit.json). Số annual vintages mới vẫn **0** vì Freddie Mac yêu cầu đăng nhập Clarity; R2/R3 mortgage, fit/calibration/OOT model còn unmet. Không nâng tổng nghiệm thu dự án khỏi **26/50 = 52%**.

**Findings analyst cho D01:** hash-verify report của frozen sample rồi tái tính ba kết quả: D3 stock đạt đỉnh 505 khoản/2,19% tháng 07/2020; 12-month D3 CIF là 0,212% tổng, 0,520% Relief và 0,042% non-Relief (descriptive, không causal); 381 terminal loans gồm 374 reported-loss và 7 unresolved, severity chỉ là quan sát có điều kiện, gate LGD còn blocked. Xem [memo](D01_ANALYST_FINDINGS_VI.md), [reproducible audit](../artifacts/private/d01-analyst-findings-a9579df23a87/audit.json). M01-010 được verified cho sample 2012; source semantics, R2/R3 và R4 còn mở.

**Episode denominator và UI:** độc lập kiểm tra 4.902 confirmed event rows thuộc 1.713 loans; one-month cure gồm 1.694 occurrences/1.152 unique loans, còn redefault có 271/216. Follow-up status phân hoạch event rows chính xác ở 24/24 tổ hợp event type × segment × horizon. App giờ phân biệt event rows với distinct-loan support ở Toàn sample; 25/25 browser checks pass. Xem [denominator method note](D01_EPISODE_DENOMINATORS_VI.md), [audit](../artifacts/private/d01-episode-denominators-a3a3093f04b8/audit.json), [receipt](../artifacts/private/browser-qa-f35adbcaeddf/receipt.json). M01-012 verified cho descriptive sample; event probability/survival model vẫn mở.

**Transition denominator và diễn giải:** independent LAG audit 4.460.559 adjacent month pairs trên 1.185 year/segment/lifetime cells; 2.370 amount checks khớp, probability max error 2,22e−16, 68 export scopes khớp. Current→D3+ là 31/4.415.313 current-origin pairs (0,000702% count weight), còn D2→D3+ là 2.316/5.409 D2-origin pairs (42,818%). Đây là pair-weighted transition share, không phải fixed-horizon PD vì cùng loan xuất hiện nhiều tháng. Xem [denominator note](D01_TRANSITION_DENOMINATORS_VI.md), [P2.05 acceptance](P2_TRANSITION_ACCEPTANCE_VI.md). M01-011 verified cho sample 2012; multi-vintage comparison còn mở.

**Canonical semantics:** audit truy raw fields qua Release-47 dictionary, code canonical và tests: 17 sentinel mappings, 20 enum fields, sáu date conversions, HARP flags, năm numeric percentage-point fields và toàn bộ 4.510.559 monthly state/terminal rows đều khớp, không có transformation mismatch. M01-003 verified trên supplied 2012 corpus; release authentication và cross-vintage compatibility vẫn mở. Xem [semantic audit memo](D01_CANONICAL_SEMANTIC_AUDIT_VI.md), [receipt](../artifacts/private/d01-canonical-semantics-e2fe2cdc8cbf/receipt.json). Tổng nghiệm thu vẫn **26/50 = 52%**.

**R0 package/resource:** khóa runtime 19/19, hash 164 upstream engine files, D: storage và 0 private paths trong 969 Git candidates đã được kiểm tra. Package privacy audit mới quét byte-level cả 15 static assets sau khi phát hiện UI có ảnh PNG; không source loan ID nào trong 50.000 IDs xuất hiện trong bundle. Clean rebuild đo 192 giây/774,5 MiB peak. M01-004 vẫn Partial do upstream engine không kèm LICENSE, hai dependency thiếu license metadata, và chưa có expanded concurrent/full-model footprint review. Xem [release-readiness memo](D01_RELEASE_READINESS_VI.md), [release receipt](../artifacts/private/d01-release-readiness-89b0c5945a8f/receipt.json), [current package audit](../artifacts/private/package-audit-4dd8b231c83e/receipt.json).

**Tìm nguồn cho vintages:** Freddie yêu cầu Clarity sign-in; Fannie primary performance cấp qua Data Dynamics account được duyệt. HMDA API có dữ liệu public application/origination, nhưng không monthly post-booking performance. Mới xác định FHFA/CFPB NSMO là một PUF mortgage riêng (2013–2024 origination; quarterly performance đến 2025Q3); chưa tải microdata do FHFA yêu cầu acknowledgement monitoring/terms. NSMO không được gộp vào Freddie và không tính là Freddie vintage. Xem `D01_NSMO_SOURCE_REVIEW_VI.md`.

**Full test gate:** sau thay đổi reproduction receipt và test runner, chạy lại toàn bộ 1.568 test tuần tự qua 21 process mới; 1.568 pass, zero failures/errors/skips, không retry. Runner tự thêm import roots cho app/vendor; subprocess optimized-Python test pass. Xem [receipt và cách chạy lại](TEST_SUITE_2026-10-15_VI.md). Engineering changes gần đây gồm privacy scan binary assets, bankruptcy batched reads và reproduction receipt versioning.

**Bổ sung sau đó:** thêm CSV-streaming parser NSMO quarterly status dựa trên codebook FHFA và chín synthetic-fixture tests; `scripts/test.ps1` chạy lại toàn bộ app/vendor suite với **1.577/1.577 passed trong 341,4 giây**. Receipt mới: `artifacts/private/test-suite-direct-20261015-nsmo-stream/receipt.json`; requirement completion rate giữ 26/50.

**M01-022 export contract:** actual D01 schema-2 export được audit trên 5 filter scopes, bao gồm Relief/non-Relief, reporting-year và unavailable-year. Case/run/method hashes, supplements, null/visibility guards và deterministic repeat khớp; quét payload theo 50.000 loan IDs không thấy match. Audit phát hiện query key không nhận diện bị bỏ qua, nên API giờ whitelist filters và reject metric override PD12/ECL/cash-flow cùng run sai. Xem [contract audit memo](D01_EXPORT_CONTRACT_AUDIT_VI.md), [receipt](../artifacts/private/d01-export-contract-dc182aeaae7e/receipt.json), [25-check browser QA](../artifacts/private/browser-qa-d7e3d9425f14/receipt.json). Bốn regression test mới được thêm; full suite sau endpoint change đạt 1.566/1.566.

**M01-024/M01-028 chart, UX và error-mode audit:** sáu nhóm đối chiếu pass trên frozen D01 run: 513 monthly stock/share points; 9 vintage segment-horizon rows; 26 portfolio profile denominator groups; 1.091 annual và 94 lifetime transition rows; signed loss bridge của 374 resolved loans, tách 7 unresolved. Browser QA 39 checks xác nhận SVG series/support, sparse transition warning, năm màn ở 390px, stale-evidence 503, missing-run 404, unknown run, mất kết nối và JSON lỗi đều fail closed. Xem [audit memo](D01_CHART_SUPPORT_AUDIT_VI.md), [data receipt](../artifacts/private/d01-chart-support-a5a39d8e7acc/receipt.json), [browser receipt](../artifacts/private/browser-qa-7a281849bd29/receipt.json). M01-024 vẫn Partial vì chưa có multi-vintage comparison/model; M01-028 còn một số biến thể transport/serving. Tổng requirement giữ **26/50 = 52%**.

**M01-029 tái lập report/UI/model gate:** ngoài tám stage foundation, tạo case private hợp lệ mới từ foundation đã xác minh. `report.json` khớp từng byte; snapshot JSON khớp sau khi chuẩn hóa case ID. Study/feature audit/assessment chạy lại và dừng đúng tại `BLOCKED_BEFORE_FIT` (100 positive, 43.227 negative ở train; 0 calibration/validation/test), không fit model. Browser QA mới nhất 42/42 PASS trên đúng case mới; ba check bổ sung xác nhận HTTP 500 JSON, 502 HTML và 503 run catalog đều fail-closed, không để lại KPI cũ. M01-029 vẫn Partial vì chưa đủ multi-vintage để fit/calibrate và chạy final OOT. Xem [audit](D01_REPRODUCTION_AUDIT_VI.md), [receipt tổng hợp](../artifacts/private/d01-final-reproduction-qa42-20261015/receipt.json) và [browser receipt](../artifacts/private/browser-qa-8c77d535b638/receipt.json).

**M01-030 descriptive handoff:** soạn [case study D01](D01_CASE_STUDY_VI.md), nối research question với scope 2012, target/estimand, KPI denominators, findings 2020/Relief/loss, tình trạng gates và reviewer checklist. Tách rõ kết quả mô tả với causal/model claim; qualified model card và final R4 demo còn chờ annual vintages và R3.

**Acquisition check:** rà lại nguồn official 15/10/2026. Freddie SFLLD loan-level monthly data tới 31/03/2026 nhưng cần Clarity sign-in; Fannie Single-Family tới Q1 2026 và Multifamily performance/DSCR cũng cần Data Dynamics registration/terms. HMDA LAR là origination/application grain, không phải monthly performance. Không tìm được panel public tương đương để tải thay thế; annual vintage mới tiếp tục bằng 0. Chi tiết tại [data access check](D01_DATA_ACCESS_CHECK_2026-10-15_VI.md).


**M01-028 transport errors:** mở rộng browser QA real-data từ 39 lên 42 checks. Snapshot API trả 500/JSON hoặc 502/HTML đều hiện evidence unavailable, không hiển thị metric cũ; test run PASS trên case `d01-202610150931`. M01-028 vẫn Partial vì còn phải cân đối coverage cho các workspace API và delivery flows khác; xem receipt 42 checks trong phần M01-029 phía trên.

**Tiếp tục M01-028 + mortgage context data:** browser QA độc lập trên cùng valid case đạt **57/57 PASS**. Bổ sung xử lý JSON lỗi/HTTP non-JSON rõ ràng trong API client; kiểm tra lỗi 500/502/503 cho transition mart, episode follow-up, source monitoring, loan search/timeline, provenance, prepared studies, loss diagnostics, findings/history/save, report export và standalone NMDB JSON export. Tải trực tiếp từ FHFA bộ NMDB quarterly mortgage-performance aggregates (release 30/09/2026): **261.856 dòng**, 13 cột, 261.856 source keys duy nhất, bốn series, bốn thị trường, sáu geography levels, 98 quý từ 2002Q1 đến 2026Q2. App Sources có chart national all-mortgages cho delinquency/foreclosure-state categories và forbearance, kèm denominator/source caveats; không ghép panel, không predictor, không tính vintage. Parser tests 4/4 PASS, gồm bounds/period checks. Full repository suite chạy sau phần NMDB export đạt **1.581/1.581**. Receipt `artifacts/private/browser-qa-2d25ed161db0/receipt.json`; full test receipt `artifacts/private/test-suite-direct-20261015-nmdb-export/receipt.json`; latest source receipt `data/private/public-context/fhfa-nmdb-performance-e287056bb7cf/receipt.json`; research note [FHFA NMDB aggregate profile](FHFA_NMDB_AGGREGATE_PERFORMANCE_VI.md). Tổng nghiệm thu vẫn **26/50 = 52%**. Freddie annual loan-level vintages = 0; NSMO payload còn chờ FHFA monitoring acknowledgement; R2/R3 chưa mở.

**Ginnie Mae source candidate + parser gate:** xác minh nguồn loan-performance riêng qua catalog/layout/Terms of Use chính thức. `LoanPerf_202606.zip` được catalog niêm yết 782.688.297 bytes và `LoanPerfAnn_202512.zip` 2.302.624.988 bytes; file layout có delinquency status hiện tại, `LP-59` tối đa 24 tháng lịch sử, credit score, LTV/DTI, current UPB và removal reason. Thêm note phân tích riêng, extension M01-X07 và ZIP auditor streaming chỉ xuất aggregate diagnostics, không lộ loan keys. Sáu test synthetic và full suite **1.587/1.587** pass (336,22 giây). Chưa tải payload vì Ginnie yêu cầu người dùng chấp nhận Terms of Use loan-level; Ginnie không được gộp vào Freddie và không đổi acceptance 26/50. Chi tiết: [source review](GINNIE_MAE_LOAN_PERFORMANCE_SOURCE_REVIEW_VI.md), [receipt](../artifacts/private/ginnie-loanperf-source-review-20261015/receipt.json).

**M01-028 Market export continuation:** thêm kiểm tra dữ liệu thật cho export series và bond scenario. Hai luồng tải JSON hiện xác thực HTTP/JSON trước khi tạo file; browser QA xác nhận payload giữ đúng private scope, ngày lọc và trạng thái assumption-only, đồng thời lỗi HTTP 503/502 hiện thông báo mà không tạo file giả. Browser acceptance đạt **61/61 PASS** (`artifacts/private/browser-qa-12b9ce006825/receipt.json`); focused Market API suite đạt **9/9 PASS**. Đây là mở rộng error/delivery coverage, không thay đổi kết quả model hoặc completion **26/50 = 52%**. M01-028 vẫn Partial do các workspace khác còn route/export cần kiểm tra.

**S28 FHFA Enterprise PUDB acquisition/access track:** tải official 2025 Single-Family Census Tract ZIP + data dictionary + record-count workbook, release 24/09/2026. Streaming parser xác nhận **2.093.767 records × 66 fields**, 2.093.767 unique source keys, 0 malformed/duplicate rows; Enterprise totals khớp FHFA: Fannie 987.450, Freddie 1.106.317. Added aggregate-only profile service/API and Sources-page tables for purpose, guarantee, DTI, score-model, borrower/tract categories; counts `<30` are suppressed in display and exports contain no source keys. This is acquisition/access mix only: no monthly performance/default/loss, no denial denominator, no D01 joining or modeling. Parser/receipt tests **5/5 PASS**, combined with Market APIs **14/14 PASS**; latest real-data browser acceptance **64/64 PASS**, receipt `artifacts/private/browser-qa-ce65ee3cf106/receipt.json`. Source review: [FHFA PUDB credit-access assessment](FHFA_PUDB_CREDIT_ACCESS_REVIEW_VI.md). D01 remains **26/50 = 52%**; Freddie annual loan-level vintages remain 0, and R2/R3 still require authorized performance data.

**M01-028 shared attachment delivery:** rà soát các anchor download API thấy nhiều report Excel/JSON tải thẳng nên HTTP error có thể thành file lỗi. Thêm delegated handler kiểm tra HTTP, từ chối HTML/empty response, giữ filename từ server và báo lỗi trong UI. Browser acceptance hiện **66/66 PASS** (`artifacts/private/browser-qa-6477b486711c/receipt.json`): tải Excel template thật đúng filename; export giả lập HTTP 503 không tạo file. Focused Market API tests **9/9 PASS**. M01-028 vẫn Partial vì các workspace route khác cần scoped checks; D01 không đổi **26/50 = 52%**.

**S29 HUD FHA Insurance in Force by Tract:** dùng official HUD ArcGIS CSV endpoint vì monthly Portfolio Snapshot XLSX trả HTTP 403 cho cả browser fetch lẫn direct HTTP, nên không coi file đó là đã lấy. Đã tải/profile tract aggregate: **85.154 unique tracts × 20 fields**, 52 state/territory codes; sum trên ô nonblank, nonnegative-coded là **7.683.397** active insured-loan count, **$1.445.485.085.013** unpaid balance và **$1.637.527.581.865** original amount. `-4` xuất hiện **9.598 lần** ở mỗi amount field; metadata không định nghĩa nên giữ thành uninterpreted code và loại khỏi sum. Có discrepancy hiệu lực: Data.gov/item metadata ghi coverage 03/2025, REST layer description ghi 09/2021; app cảnh báo không dùng làm current exposure/time trend. Parser tests **4/4 PASS**; full mortgage-source browser acceptance **69/69 PASS**, receipt `artifacts/private/browser-qa-7a73963387de/receipt.json`. Source review: [HUD FHA tract review](HUD_FHA_IIF_TRACT_REVIEW_VI.md). Source chỉ bổ sung geography/exposure, không có performance/default/denial và không đổi D01 **26/50 = 52%**.

**Performance-source recheck:** rà soát lại nguồn chính thức cho thấy Fannie Q1 2026 performance data vẫn cần account/email confirmation và Terms; website Terms còn hạn chế automated scraping, third-party access và AI training/benchmarking nếu không được cho phép. Không tải thêm sample CSV hoặc performance payload trong lượt recheck này; Fannie sample-format audit đã có từ lần acquisition trước, vẫn tách khỏi performance data. HUD monthly portfolio snapshot cũng không có repayment history và file August 2026 bị 403; chỉ tải nguồn ArcGIS tract aggregate riêng đã nêu trên. Recheck không tìm được loan-level monthly performance source mới có thể lấy vô điều kiện và dùng làm Freddie-compatible panel. Kết luận/điều kiện ghi ở [data-access check](D01_DATA_ACCESS_CHECK_2026-10-15_VI.md); M01-005 và D01 model gates giữ nguyên.

**M01-028 cross-workspace attachment QA:** thêm Fannie sample-format audit JSON vào browser acceptance qua liên kết GET trực tiếp. Download thật giữ server filename và private-release flags; HTTP 503 hiển thị lỗi và không sinh file giả. Latest real-data browser suite **71/71 PASS** (`artifacts/private/browser-qa-f32396b0c1ff/receipt.json`), focused Fannie/HUD tests **10/10 PASS**. Đây chỉ tăng delivery coverage; payload Fannie performance chưa được lấy và D01 vẫn **26/50 = 52%**.

**M01-028 POST workbook delivery:** KPI Monitor, SEC và affordability POST export nay cùng xác thực HTTP, MIME type và payload rỗng trước khi tải. Browser acceptance trên monitor thật tải XLSX hợp lệ (ZIP integrity + workbook manifest) và xác nhận HTTP 503 JSON cùng HTTP 200 HTML giả danh workbook đều báo lỗi, không tạo file. Latest suite **74/74 PASS** (`artifacts/private/browser-qa-9b34beeb05fd/receipt.json`). SEC/affordability POST còn cần flow-specific QA; M01-028 Partial và D01 **26/50 = 52%** không đổi.

**M01-028 POST flow-specific acceptance:** SEC maturity và interest-coverage XLSX thật được tải từ verified SEC snapshots, kiểm tra ZIP/workbook manifest; affordability JSON thật giữ private scope và không tạo credit decision. Cả ba luồng đều qua HTTP 503 JSON và HTTP 200 HTML giả danh file mà không tạo download giả. Latest browser acceptance **83/83 PASS** (`artifacts/private/browser-qa-2d436bad58fc/receipt.json`); focused KPI/SEC/affordability tests **56/56 PASS**. M01-028 vẫn Partial do các workspace routes khác; D01 giữ **26/50 = 52%**.

**NSMO v7.0 acquisition (case D02 riêng):** đã hoàn tất hai bước xác nhận được cho phép trên cổng FHFA rồi tải CSV ZIP v7.0, 16.365.906 bytes; SHA-256 ZIP `d0c745be0284d1660b7973e31a6255a170dcd6ed8a26742c5d3720aafd284684`. Bản CSV 167.286.458 bytes, 62.359 dòng, 587 cột, 62.359 `nsmoid` duy nhất, 0 dòng lệch cột/ID trùng/ID rỗng; 51 quý liên tục 2013Q1–2025Q3; `analysis_weight` đủ, hữu hạn, dương; toàn bộ 3.180.309 status cells thuộc mã trong codebook. Parser nhận header lowercase thực tế; focused parser/auditor test **13/13 PASS** và full-file aggregate audit PASS. Toàn bộ app/vendor suite **1.601/1.601 PASS**. Raw PUF và receipts chỉ nằm private trên D:, không đưa lên GitHub. Chưa dựng target/PD hoặc gộp với Freddie; `D01` vẫn **26/50 = 52%**, `R2/R3` chưa đạt. Chi tiết: [NSMO source review](D01_NSMO_SOURCE_REVIEW_VI.md) và [D02 build plan](NSMO_D02_CASE_BUILD_PLAN_VI.md).

**Nguồn dữ liệu bổ sung:** tải bốn CSV chính thức từ CFPB Mortgage Performance Trends, theo tháng 2008-01–2025-12, delinquency 30–89 ngày và 90+ ngày theo 507 county equivalents và 51 state/district records. Nguồn đã tích hợp vào Mortgage Sources với National/State/County selector, hash/schema verification và aggregate JSON export. Parser tests **3/3**, real-data browser acceptance **86/86 PASS** (`artifacts/private/browser-qa-64d976250c71/receipt.json`). CFPB xác nhận nguồn là NMDB; đây là biểu diễn monthly geography bổ sung, không phải independent sample, Freddie vintage hay loan-level target. Research note: `CFPB_MORTGAGE_PERFORMANCE_TRENDS_REVIEW_VI.md`. D01 vẫn **26/50 = 52%**.

**M01-028 SEC GET attachment audit:** kiểm tra tải thật 5 report JSON của SEC: payment rules (5 rules), note schedule (42 dòng/4 notes), maturity (6 buckets), interest coverage (5 periods), annual trends (5 periods); server filenames và JSON content khớp. HTTP 503 ở coverage report hiển thị lỗi, không sinh download giả. Latest real-data browser acceptance **92/92 PASS** (`artifacts/private/browser-qa-ed3b90bff36c/receipt.json`). M01-028 vẫn Partial vì các workspace khác còn route cần QA; D01 **26/50 = 52%**.
