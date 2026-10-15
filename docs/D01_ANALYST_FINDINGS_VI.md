# D01 — Findings analyst trên sample mortgage 2012

**Ngày:** 15/10/2026. **Phạm vi:** portfolio/cohort/loss mô tả của một origination vintage Freddie Mac 2012, frozen case `d01-a24484b21a21`, pipeline `pipeline-307c354f3d74`. Đây là findings memo cho sample nghiên cứu, không đại diện toàn danh mục Freddie Mac hay toàn thị trường mortgage Mỹ.

## Cơ sở và cách đọc

Nguồn hiện được tích hợp có 50.000 khoản và 4.510.559 loan-month observations từ tháng 01/2012 đến 03/2026. Các reporting months thuộc cùng origination vintage, không phải 15 vintages độc lập. File hiện hành là latest-revised retrospective source; ngày quan sát không chứng minh dữ liệu đã sẵn có tại thời điểm dự báo lịch sử. Target event là first-observed source delinquency state numeric 03–99 trong 12 tháng t+1…t+12, với prepayment/maturity và các exits khác được giữ thành competing outcomes. Target này không đồng nghĩa regulatory default hoặc 30/60/90 DPD chuẩn hóa.

Các phát hiện dưới đây được tính lại từ frozen `report.json` sau khi kiểm SHA với `case-complete.json`; panel, label, stock, transition, episode và vintage artifacts có lineage về cùng pipeline. Audit không materialize loan IDs. Tái tạo bằng `scripts/audit_d01_analyst_findings.py`; [audit JSON](../artifacts/private/d01-analyst-findings-a9579df23a87/audit.json) và [receipt](../artifacts/private/d01-analyst-findings-a9579df23a87/receipt.json).

## 1. Tồn kho D3 trong sample tăng rất mạnh vào giữa năm 2020

Định nghĩa ở đây là stock quan sát trong tháng: số khoản active có trạng thái source D3+ chia số khoản active có trạng thái dùng được. Đây không phải incidence khoản mới chuyển D3 trong tháng và cũng không phải xác suất vỡ nợ.

| Tháng | Khoản active có trạng thái | D3+ khoản | D3+ count share | D3+ balance share |
|---|---:|---:|---:|---:|
| 03/2020 | 24.779 | 67 | 0,270% | 0,319% |
| 05/2020 | 24.081 | 93 | 0,386% | 0,484% |
| 06/2020 | 23.602 | 409 | 1,733% | 2,250% |
| 07/2020 | 23.070 | 505 | 2,189% | 2,896% |

Tháng 07/2020 là đỉnh cao nhất trong 171 reporting months của panel: D3+ UPB khoảng **$92,34 triệu** trên active UPB **$3,188 tỷ**. Đây là thay đổi lớn về trạng thái tồn kho nên đáng mở drilldown theo source code, episode và segment. Bản thân chuỗi không chứng minh nguyên nhân, không tách được nguyên nhân macro với thay đổi payment/forbearance/reporting và không đo số event mới nếu không dùng event ledger. App vì vậy giữ chart là monthly stock share và không gọi là default rate.

## 2. Incidence 12 tháng khác đáng kể giữa hai nhóm Relief trong sample

Trong early-entry cohort 2012, 48.066 khoản đủ điều kiện; 47.984 có binary target khả dụng. Target có 102 D3 events, 2.641 prepayment/maturity negatives theo event-before-prepayment estimand, 82 other exits không được gán negative và 1.934 khoản không đủ điều kiện.

Competing-risk cumulative incidence 12 tháng của D3 là **0,212%** (102 events; bootstrap interval 95%: 0,173%–0,252%). Theo segment quan sát, Relief có CIF **0,520%** (89 D3; 17.117 eligible), còn non-Relief là **0,042%** (13 D3; 30.949 eligible). Tỷ số mô tả hai CIF khoảng 12,4 lần, nhưng nhóm non-Relief chỉ có 13 events và các nhóm không được phân bổ ngẫu nhiên.

Kết quả cho thấy program/segment composition và target support cần được đưa vào mọi cohort review. Nó **không** chứng minh Relief gây ra tăng rủi ro: selection vào program, vintage/time mix, eligibility và biến cố lịch sử có thể khác giữa nhóm. Không dùng chênh lệch này để đặt policy, làm treatment effect hoặc làm performance estimate cho model. Trước nghiên cứu hiệu chỉnh cần nhiều origination vintages, protocol temporal đã đóng băng, support review theo từng nhóm và feature availability hợp lệ.

## 3. Loss bridge hữu ích để điều tra nhưng chưa đủ để gọi LGD

Panel có **381 terminal loans**; 374 có reported loss và 7 chưa có resolved loss component. Tổng reported loss là **$18,66 triệu**, mean khoảng **$49.893/khoản được báo cáo**. Trên 374 khoản có severity denominator hợp lệ theo removal UPB, mean uncapped severity là **33,10%** và lớn nhất **145,60%**. Source giữ loss có dấu âm/dương và bridge component theo nguồn; không ép giá trị vượt 100% về 100%.

Các số này có điều kiện trên terminal records và dữ liệu loss đã được báo cáo. Sáu hồ sơ bị withheld defect và một hồ sơ recent disposition nằm trong availability states cần phân biệt; thiếu dữ liệu không được đổi thành zero. Gate của report còn `blocked` do resolved support dưới 1.000, denominator support thấp hơn yêu cầu và một phần component coverage chưa đầy đủ. Do đó dashboard chỉ trình bày observed loss reconciliation; không phát hành LGD, expected loss hay ECL.

## Hành động theo plan

1. Giữ M01-010/P2.03 làm descriptive finding cho đúng sample 2012; không nâng thành kết luận cho các vintage khác.
2. Với spike 2020, tra những code/episodes và segment cùng kỳ trong timeline; thêm source-level explanation trước khi diễn giải cause.
3. Giữ split cohort theo Relief và non-Relief trong evidence, nhưng không chọn champion/threshold từ 102 events.
4. Giữ observed-loss bridge và coverage statuses làm kết quả; chờ resolved loss support/mature terminal cohorts trước khi mở LGD.
5. Tiếp tục chuẩn bị protocol và source adapter cho M01-005/M01-015/M01-016. Freddie Mac yêu cầu đăng nhập Clarity để tải annual loan-level samples; Release 47 example ZIP đã kiểm thử layout nhưng không bổ sung vintage.

## Giới hạn nghiệm thu

Finding memo này đóng phần analyst interpretation cho frozen descriptive sample, nhưng không đóng R0/R1 toàn module, R2 multi-vintage, R3 model hoặc R4 handoff. Không model nào được fit trong audit này. Tổng sổ CreditAtlas vẫn **26/50 = 52%** cho đến khi các yêu cầu khác có evidence riêng.
