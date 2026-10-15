# Nissan Auto Receivables 2024-B: kiểm định external issuer cho ABS-EE

Ngày chốt: 15/10/2026. Nguồn raw XML và Parquet chứa asset identifier nằm trong thư mục private trên D:. App chỉ nhận audit tổng hợp đã pin SHA-256.

## 1. Mục tiêu và nguồn

Nissan 2024-B được chọn làm bộ kiểm tra khác issuer/servicer family sau hai deal Toyota. SEC EDGAR xác nhận Form 10-D kỳ báo cáo 31/10/2024 của Nissan Auto Receivables 2024-B Owner Trust, accession `0001193125-24-264295`, gồm EX-99.1 Servicer’s Certificate; [SEC filing detail](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). Nissan ABS-EE có EX-102 và EX-103; ví dụ SEC filing 2026 kỳ 05/2026 được đăng dưới Nissan Auto Receivables filing group [SEC ABS-EE detail](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).

Acquisition ghép đúng report month của ABS-EE và 10-D trong 23 kỳ liên tục **31/10/2024–31/08/2026**. 09/2024 có hai filing ABS-EE nhưng không tìm được 10-D đồng kỳ đủ căn cứ nên bị loại khỏi khoảng liên tục. EX-99.1 có ngày collection period khớp kỳ certificate; acquisition receipt lưu URL, accession, metadata HTTP, kích thước và SHA-256 từng attachment.

## 2. Dataset và schema

- EX-102: 4.158.197.033 byte XML không nén; lưu gzip lossless 128.532.667 byte.
- Panel riêng: 1.154.259 asset row-months, 63.688 asset keys và 63 trường trên 23 partition tháng; có 22 transitions liền kỳ.
- Union schema đã kiểm tra trên toàn bộ EX-102. Nissan có `originalInterestOnlyTermNumber` và `servicerAdvancedAmount`, không có `repossessedProceedsAmount` trong panel này; không dùng nguyên schema 62 trường của Toyota.
- Hash/byte count của mọi XML, certificate và Parquet được đối chiếu manifest. Asset keys duy nhất trong từng tháng; reporting-period date đúng kỳ. Raw string, null, giá trị âm và mã được giữ nguyên; DPD thêm cột số ngày theo XSD.
- Không resolve asset key thành borrower ID và không gán disappearance thành default, prepayment hoặc payoff.

EX-103 giữ cùng SHA trong 21 kỳ đầu, rồi thay bản mô tả ở 07/2026–08/2026. Diff 06→07/2026 đổi tên sponsor/servicer trong Item 3(a)(1) từ Nissan Motor Acceptance Corporation sang Nissan Motor Acceptance Company LLC; Item 3(f)(12) cập nhật ví dụ supplemental servicing fees, thêm prepayment charges/admin expenses và bỏ ví dụ NSF/title fees. Đây là thay đổi narrative cần lưu trong lineage, chưa chứng minh field values hay định nghĩa loss đã thay đổi.

Các mô tả quan trọng trong Nissan EX-103 khác Toyota:

- Item 3(i)(1) `chargedoffPrincipalAmount`: phần principal chưa thu được bị charge-off trong kỳ báo cáo.
- Item 3(i)(2) `recoveredAmount`: số tiền servicer thu được đối với receivable đã từng được phản ánh là charge-off.
- Item 3(k)(1) `repossessedProceedsAmount`: tiền bán xe chỉ được báo tại trường này nếu bán trong cùng kỳ repossession; nếu bán ở kỳ khác thì ghi thành recovered amount.

Vì vậy mapping từ Toyota không được tái sử dụng mặc định cho Nissan. Positive recovery không nhất thiết nằm ở row có code 4, và repeated charge-off months cần rule riêng.

## 3. Đối soát với certificate theo từng kỳ

| Kiểm tra | Kết quả |
|---|---:|
| Asset ending pool balance ↔ certificate Pool Balance | 23/23 exact |
| Asset có ending balance dương ↔ contract count | 23/23 exact |
| Tổng `chargedoffPrincipalAmount` ↔ Principal on Defaulted Receivables | 21/23 exact |
| Số asset row có charge-off dương ↔ defaulted receivable count | 20/23 exact |
| Asset có code 4 lần đầu ↔ defaulted receivable count | 21/23 exact |
| Charge-off amount trên code-4 lần đầu ↔ gross defaulted principal | 20/23 exact |
| DPD buckets × count và balance | 178/184 exact |
| `recoveredAmount` ↔ current / principal certificate recoveries | 17/23 exact |

Mỗi định nghĩa event có kết quả khác nhau. Count asset rows có charge-off dương khớp certificate 20/23; số asset bắt đầu code 4 lần đầu khớp 21/23. Ví dụ 01/2025 có 31 code-4 first rows, nhưng một row có charge-off amount bằng zero; certificate báo 31 receivables và gross principal khớp. 02/2025 có 37 first code-4 rows so với 37 receivables, nhưng ABS-EE amount cao hơn $44,66. Do đó code4 count có thể là đối chiếu hữu ích hơn positive-amount count trong một số kỳ, nhưng chưa thống nhất toàn chuỗi.

Ngoại lệ lớn 07/2025: 33 asset keys có code 4 lần đầu và 3 row lặp code 4/charge-off từ tháng trước; asset sum $655.185,56. Trong đó first-code-4 rows cộng $577.420,34, còn ba repeated rows cộng $77.765,22. Certificate lại báo **1 receivable** và principal **−$59.000,49**. Submission census của CIK trust không có 10-D/A hoặc ABS-EE/A cho report date này. Không có mapping/correction giải thích; tháng này bị giữ là exception, không dùng làm event truth.

Tháng 08/2025 cho thấy một cách khác có thể khớp: 54 positive charge-off rows và gross principal đều khớp certificate 54/$860.007,75; chỉ 24 rows là lần đầu code 4. Vì vậy không thể chọn một event anchor chung cho mọi kỳ trước khi truy nguyên receivable-level records và certificate math.

Trong 06/2025, số dư các DPD buckets trên asset rows và certificate vẫn tổng hợp bằng nhau, nhưng phân loại bucket lệch:

| Bucket | Count delta (asset − certificate) | Balance delta |
|---|---:|---:|
| 31–60 ngày | +2 | +$50.837,98 |
| 61–90 ngày | −1 | −$28.108,10 |
| 91–120 ngày | −1 | −$22.729,88 |
| Trên 120 ngày | 0 | $0 |

Ba balance deltas đầu cộng bằng zero. Không kết luận đây là biên ngày, mapping status hay lỗi extract cho tới khi kiểm tra loan rows và bucket convention riêng của servicer.

Drilldown xác nhận hai source rows ở đúng 60 DPD cộng $50.837,98 và một row ở 90 DPD là $22.729,88; các số này khớp chính xác cấu trúc bucket residual tháng 06. Dịch ranh giới source days một ngày sớm hơn làm tháng 06 khớp 8/8 checks, nhưng trên toàn 23 kỳ lại giảm exact checks từ 178/184 xuống 86/184. Vì vậy đây là giải thích số học cục bộ, chưa chứng minh certificate dùng boundary đó và không áp dụng làm rule chung.

Recovery khớp 17/23 kỳ với cả certificate dòng `Recoveries of Defaulted Receivables` và `Principal Recoveries of Defaulted Receivables`; hai dòng certificate có cùng số trong các kỳ được audit. Sáu kỳ còn lệch (12/2024–05/2025), tổng signed delta **+$8.859,23**. Drilldown cho thấy toàn bộ positive recovery row-months của sáu kỳ thuộc asset keys có code 4 đã xuất hiện ở một tháng trước trong panel; không có recovery âm hoặc positive recovery và positive charge-off trên cùng row. Các cash-collection fields khác đều zero trên những recovery-positive rows. Điều này hỗ trợ timing definition của Nissan, nhưng chưa giải thích amount delta; repossession/collection scope và certificate aggregation vẫn cần được xác nhận.

## 4. Độ ổn định event và code

- 649 row-months có `zeroBalanceCode=4`, đều có ending balance zero; 646 row-months trong đó cũng có charge-off dương.
- 613 asset keys có ít nhất một tháng charge-off dương; 616 asset keys từng có code 4.
- Chỉ **580/613** asset charge-off keys có đúng một tháng charge-off dương và tháng đầu đó trùng tháng code 4 đầu tiên. 33 keys có charge-off dương qua nhiều tháng hoặc không khớp event rule một lần.
- 1.626 row-months có recovery dương nhưng không có code 4 tại chính row đó; 9 recovery âm cũng không ở row code 4.
- **01/2025:** 31 first-code-4 keys gồm một key charge-off bằng zero; 30 charge-off dương cộng đúng $704.133,82 certificate principal.
- **02/2025:** 37 first-code-4 keys gồm hai key zero; 35 positive rows cộng $939.798,68, cao hơn certificate $939.754,02 đúng $44,66.
- **07/2025:** 33 first-code-4 rows cộng $577.420,34; 3 key đã có code 4/charge-off ở tháng 06 lặp lại $77.765,22; cả 36 row cộng $655.185,56. Trong khi đó 10-D báo 1 receivable và principal **−$59.000,49**. Certificate recovery $257.636,52 khớp ABS-EE; certificate monthly net loss **−$316.637,01** bằng −$59.000,49 − $257.636,52. 10-D cũng báo current net-loss ratio **−0,39%**.
- **08/2025:** đủ 54 positive charge-off rows và $860.007,75 khớp certificate, nhưng chỉ 24 là first code-4 keys; 30 repeated rows là $522.608,93. First-code-4 amount riêng là $337.398,82.

Mẫu tháng 07 phù hợp với khả năng certificate ghi một adjustment/reversal âm, nhưng audit không xác định được receivable nào hoặc lý do. Tháng 08 chứng minh rule first-code-4 không phải lúc nào cũng tái tạo count/principal certificate; ở tháng này positive charge-off rows mới khớp. Vì vậy phải giữ event logic theo issuer và phân kỳ, không chọn một rule chung cho mọi tháng. Audit drilldown lưu hashed asset IDs và adjacent-row values trong [exception artifact](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included); không chứa borrower IDs nguyên gốc.

## 5. KPI surveillance trong 10-D và phép bảo toàn số học

Tôi đã trích đủ các chỉ số performance trong 23 Servicer’s Certificate, không chỉ đối chiếu loan-level ABS-EE. Hai phép kiểm tra số học đúng chính xác 23/23 kỳ: `Monthly Net Losses = Principal on Defaulted Receivables − Principal Recoveries of Defaulted Receivables`; và `Cumulative Net Losses = tổng Monthly Net Losses từ đầu lịch sử`. Việc này xác nhận cấu trúc tính toán của certificate cho panel này, không chứng minh nguyên nhân của các mismatch ở cấp asset hay biến KPI thành label dự báo.

| Chỉ số certificate | Kỳ đầu 10/2024 | Kỳ cuối 08/2026 | Quan sát trong 23 kỳ |
|---|---:|---:|---:|
| Monthly net losses | $90.158,92 | $221.234,71 | −$316.637,01 đến $775.360,20 |
| Current net-loss ratio | 0,08% | 0,56% | −0,39%–0,86% |
| Four-month average net-loss ratio | 0,02% | 0,26% | −0,01%–0,53% |
| Cumulative net losses | $90.158,92 | $5.231.645,63 | Tăng ròng; có kỳ giảm khi monthly loss âm |
| Delinquency percentage | 0,00% | 0,18% | 0,00%–0,24% |
| Delinquency trigger | 4,90% · No | 4,90% · No | No trong 23/23 kỳ |
| Extension principal balance | $4.236.182,63 | $1.992.957,40 | Cần phân biệt balance với số khoản extension |
| Extension count | 161 | 115 | 86–219 khoản/kỳ |
| Ending reserve balance | $3.255.208,33 | $3.255.208,33 | Không đổi trong 23 kỳ quan sát |

Tháng 07/2025 monthly net loss là −$316.637,01 vì principal recoveries trong kỳ cao hơn principal trên defaulted receivables mới của tháng; số âm được giữ đúng như certificate. Cumulative net loss giảm từ $3.203.390,44 tháng 06/2025 xuống $2.886.753,43 tháng 07/2025, rồi tiếp tục được cộng các tháng sau. Current ratio và four-month average là tỷ lệ được báo cáo trong 10-D; parser giữ nguyên dấu âm (tháng 07/2025 lần lượt −0,39% current và net loss −$316.637,01); không tự annualize hoặc thay denominator. Trigger “No” là kết quả do certificate công bố, không suy ra lại từ delinquency percentage bằng một công thức chưa được xác nhận.

App hiển thị các chuỗi time-series và bảng đầy đủ 23 kỳ cho monthly/cumulative loss, current/four-month ratios, delinquency/trigger, extension balance/count và reserve. Mục đích là surveillance, tie-out và điều tra exception. Không dùng các KPI tổng hợp này làm outcome loan-level hoặc gọi chúng là PD/LGD.

## 6. Ý nghĩa cho module credit-risk

Nissan là external issuer evidence có giá trị vì app/pipeline đã phải xử lý schema và certificate conventions khác Toyota. Pool balance và positive contract count là KPI collateral surveillance có thể tái tạo rất tốt. Gross default principal, event count, DPD bands và recovery cần Nissan-specific exceptions/mapping. Vì vậy bộ này **chưa** chứng minh transportability của PD label, model performance, calibration, LGD hoặc cohort economics; không fit model và không đưa các mismatch thành target labels.

Ưu tiên tiếp theo:

1. Xin/đối chiếu servicer-level explanation cho 07/2025 principal adjustment âm; submissions census hiện thời không có filing amendment cho report date này.
2. Xác nhận DPD bucket boundary theo EX-103/servicer; tháng 06 candidate boundary rows đã tìm thấy nhưng global boundary shift bị dữ liệu 23 kỳ bác bỏ.
3. Truy nguyên sáu recovery amount deltas còn lại theo receivable/cash category/repo-sale timing; timing charge-off đã được kiểm tra, nhưng amount scope chưa giải thích.
4. Chỉ sau đó khóa Nissan event contract và dựng availability/temporal split audit; external validation phải đo trên target đã qualify, không đánh giá model chưa fit.

## 7. Nguồn project và tái tạo

- Acquisition: `private evidence omitted from public release`
- Panel: `private evidence omitted from public release`
- Longitudinal audit: `private evidence omitted from public release`
- Certificate tie-out: `private evidence omitted from public release`
- Acquisition / panel builder / audits: `scripts/acquire_nissan_2024b_validation_panel.py`, `scripts/build_nissan_2024b_validation_panel.py`, `scripts/audit_nissan_2024b_absee_panel.py`, `scripts/audit_nissan_2024b_certificate_tieout.py`
- Live SEC submissions census refresh: `scripts/audit_nissan_2024b_submission_history.py`; [verified census audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), latest filing 2026-09-25, exact match with acquisition snapshot, no July 2025 amendments.
- Recovery timing and June 2025 DPD drilldown: [private diagnostic](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).
- Full-window comparison of literal vs candidate DPD boundaries: `scripts/audit_nissan_2024b_dpd_boundary_rules.py`; [audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).
- Reproducible certificate event drilldown: `scripts/audit_nissan_2024b_event_exception_detail.py`; [private exception audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).
- App API pin and external issuer card: `src/credit_atlas/absee_profile.py`, `apps/web/app.js`

Đây là checkpoint partial cho surveillance/collateral-history work. Tổng nghiệm thu vẫn **26/50 = 52%** vì các tiêu chí PD/LGD, event mapping và một số tie-out chưa đạt.
