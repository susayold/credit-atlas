# Case study D01 — mortgage lifecycle, competing outcomes, transitions và observed loss

**Checkpoint:** descriptive research, 15/10/2026  
**Frozen case:** `d01-a24484b21a21` · **pipeline:** `pipeline-307c354f3d74`  
**Trạng thái model:** chưa fit; R2/R3 chưa đạt gate.

## Câu hỏi nghiên cứu

Một Freddie Mac Single-Family Loan-Level Dataset origination sample có thể cho thấy điều gì về quy mô sample, diễn biến delinquency theo tháng, competing exits sau first observed entry, chuyển trạng thái liền kề, cure/redefault, và loss components? Mục tiêu hiện tại là xây bằng chứng mô tả có denominator và lineage kiểm tra được. Nghiên cứu chưa trả lời “model nào dự báo tốt”, “Relief có gây ra rủi ro cao hơn không”, hoặc “expected loss là bao nhiêu”.

## Dataset và population

- Một annual sample cho origination vintage 2012: 50.000 loans, 4.510.559 loan-month rows, reporting 01/2012–03/2026.
- Một loan có thể xuất hiện trong nhiều tháng; loan-month totals không phải unique-loan counts.
- Các reporting periods dài không tạo thành nhiều origination vintages. Sample là retrospective/latest-revised; lịch sử timestamp không chứng minh biến đó đã được biết ở ngày landmark.
- Sample không được xem là toàn bộ book Freddie Mac hay thị trường mortgage Mỹ. Bằng chứng source, method, rights và reproduction nằm trong các hồ sơ private của case.

## Estimand và metric contracts

Target hiện hữu giữ nguyên version `d01-early-entry-d3-before-prepay-12m-v1`. Landmark là tháng đầu tiên quan sát được; horizon gồm t+1 đến t+12. Numeric delinquency 03–99 là first-observed D3 event. Prepaid/matured trước D3 là competing outcome theo event-before-prepayment convention; other exits, censored và unknown không tự động thành negative. Đây không phải regulatory default PD hay số ngày quá hạn chính xác.

| Analysis | Grain và mẫu số | Đọc kết quả |
|---|---|---|
| Active stock | Loan × reporting month; D3 loans / state-usable active loans, hoặc D3 UPB / state-usable active UPB | Stock share tại thời điểm quan sát, không phải default incidence/probability |
| Early-entry target | Một dòng trên mỗi source loan; source 50.000, eligible 48.066 | 102 positive; 47.882 negative theo target; 2.016 unavailable/ineligible |
| Competing incidence | Eligible first-observed entry cohort, 6/12/24m | CIF giữ D3, prepayment/maturity và other exit riêng; không là monthly prediction |
| Transitions | Adjacent observed calendar-month pair, theo origin/segment/reporting year | Pair-weighted descriptive probability; cùng loan có thể đóng góp nhiều lần |
| Episodes | Confirmed source event | Event occurrences khác distinct-loan support; follow-up bắt đầu tại actual confirmation |
| Loss | Resolved terminal-loan components | Signed observed reconciliation, không phải LGD/ECL; unresolved tách khỏi resolved |

## Kết quả chính trên đúng sample này

**D3 stock thay đổi mạnh giữa tháng 05–07/2020.** Count share tăng từ 0,386% tháng 05 lên 1,733% tháng 06 và đạt 2,189% tháng 07; tháng 07 có 505 active D3 loans, khoảng $92,34 triệu D3 UPB trên $3,188 tỷ active UPB. Đây là quan sát tồn kho. Nó không nhận dạng được nguyên nhân macro, forbearance, payment hoặc reporting và không cho biết số event mới nếu không dùng event ledger.

**12-month D3 CIF khác theo Relief segment, nhưng support nhỏ và không ngẫu nhiên.** Toàn cohort có 102 events; CIF 0,212%, bootstrap interval 95% 0,173%–0,252%. Relief: 89 events / 17.117 eligible, CIF 0,520%. Non-Relief: 13 / 30.949, CIF 0,042%. Chênh lệch mô tả có thể phản ánh selection, eligibility, composition và historical timing; không được diễn giải causal hoặc dùng để đặt policy/model threshold.

**Loss bridge hỗ trợ điều tra; chưa hỗ trợ severity model.** Có 381 terminal loans, 374 resolved reported-loss loans và 7 unresolved; resolved reported-loss sum $18.659.957,55, mean $49.893 trên loan có reported loss. Trên 374 khoản có denominator removal UPB hợp lệ, uncapped severity mean 33,10%, max 145,60%. Gate hiện `blocked`: support dưới 1.000, denominator support thấp, partial component coverage. Expected loss giữ unavailable.

**Transitions và episodes là lịch sử quan sát có lặp.** 4.460.559 adjacent pairs; 1.091 reporting-year segment cells và 94 lifetime segment cells reconcile với frozen engine. Có 4.902 confirmed episode rows thuộc 1.713 distinct loans; cùng loan có thể có nhiều cure/redefault events. Không gọi pair percentages là fixed-horizon PD hoặc episode counts là cure probability.

## Những gì ứng dụng hiện cung cấp

Workspace có source/quality, portfolio stock/profile, competing-outcome cohort, transition matrix, private lifecycle timeline, model-readiness/feature audit, signed loss bridge và evidence/findings. Browser QA gần nhất kiểm tra 39 flows; stale/missing/unlisted run, mất kết nối và JSON lỗi đều fail closed; chart/support audit đối chiếu sáu nhóm dữ liệu; report schema-2 export đã qua 5 scope và privacy scan; clean eight-stage foundation reproduction có 13 tables và bốn stable summaries với zero differences. Mỗi artifact phải đọc cùng case ID, pipeline, target, scope note và receipt.

## Model/data status và điều kiện mở tiếp

Chưa có annual vintages bổ sung. Freddie Mac annual samples cần authorized Clarity access; public format examples không phải loan panel và không được tính là vintages. Fannie Mae loan performance qua Data Dynamics cũng yêu cầu account/registration; HMDA public LAR là origination/application grain, không phải monthly performance. Model page phải ở `BLOCKED_BEFORE_FIT`: class support cho temporal partitions không đủ, annual vintages bắt buộc còn thiếu và protocol chưa được review/freeze. Không công bố AUC, calibration, champion, loan scores hoặc expected-loss forecasts giả. Xem [data access check](D01_DATA_ACCESS_CHECK_2026-10-15_VI.md).

Để mở R2/R3: acquire authorized vintages; audit release/layout semantics qua từng năm; reconcile unique loans và loan-month grain; đóng temporal protocol/availability cutoff; tái audit labels, attrition và segment support; sau đó mới fit constant/logistic/boosting trên cùng cohort, calibrate riêng, đánh giá out-of-time và ghi uncertainty/model card. Nếu support hoặc vintage không đủ, kết luận nghiên cứu là chưa thể qualification.

## Handoff checklist

- [x] Người review có case ID, pipeline, target version và source scope.
- [x] Metric grains, mẫu số, competing outcomes, unknown và missingness được mô tả.
- [x] Findings có giới hạn; Relief không là causal claim và loss không là LGD/ECL.
- [x] Reproduction, chart/support, browser, export và test evidence có liên kết.
- [ ] Authorized multi-vintage data và cross-vintage semantic acceptance.
- [ ] Frozen temporal protocol, actual model comparison, calibration/OOT và final model card.
- [ ] Final end-to-end report/research-release reproduction sau khi model/data gates đạt.

## Evidence

- [Data and method card](D01_DATA_AND_METHOD_CARD.md)
- [Analyst findings](D01_ANALYST_FINDINGS_VI.md)
- [Chart/support audit](D01_CHART_SUPPORT_AUDIT_VI.md)
- [Reproduction audit](D01_REPRODUCTION_AUDIT_VI.md)
- [Data access check](D01_DATA_ACCESS_CHECK_2026-10-15_VI.md)
- [Export contract audit](D01_EXPORT_CONTRACT_AUDIT_VI.md)
- [Current D01 backlog](BACKLOG_STATUS.md)
