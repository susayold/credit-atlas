# SEC annual trends: financial ratios qua từng kỳ báo cáo

Mở **P3 Issuer financials → Annual trends**, hoặc từ **Risk monitor → P3 → issuer Annual trends**. Nguồn là SEC view `sec-view-b92d9914f1dc` đã verify; không tải lại dữ liệu và không thay các frozen source/model artifacts.

## Câu hỏi phân tích

Liquidity, consolidated liabilities share, profitability và operating cash generation thay đổi thế nào qua annual reports của cùng issuer? Chọn 3, 5 hoặc 10 **report periods**, issuer và filing-date cutoff. Số report periods không cam kết đủ từng calendar year; annual filing selector dùng cho single-filing evidence, không thay selection rule của trend.

Bốn ratios dùng lại source definitions đã có: current assets/current liabilities, liabilities/assets, net income/revenue và operating cashflow/revenue. Actual, input support, baseline period/actual, absolute delta, relative delta và comparison status hiển thị từng kỳ. Share deltas đọc bằng điểm phần trăm; current-ratio delta dùng ratio units.

## Selection và comparability

- Mỗi report date cần đúng một original 10-K. Các 10-K/A vẫn nằm trong filing evidence nhưng không tự ghi đè original. Nếu thiếu hoặc có nhiều originals, statement unavailable và linkage của kỳ kế tiếp bị ngắt.
- Hai report dates phải cách nhau 330–400 ngày. Không bỏ qua gap để chọn năm cũ hơn cho comparison.
- Cả hai ratios phải supported; numerator/denominator có cùng concept mapping, units và field kinds qua hai kỳ. Đây là conservative comparability screen, không chứng nhận accounting equivalence.
- Annual-duration facts dùng cùng source period rules; chênh duration giữa kỳ tối đa 7 ngày. Chênh lớn hơn giữ unavailable.
- Absolute delta = actual − baseline, tính Decimal precision 60. Relative delta = delta/baseline, chỉ khi baseline dương. Zero hoặc negative baseline giữ relative unavailable; không gán growth rate cho sự đảo dấu margin.
- Baseline của dòng đầu có thể nằm ngoài cửa sổ hiển thị. JSON giữ full baseline statement và app hiển thị exact baseline fields trong evidence.

## Cách investigate

### Phân rã biến động theo tử số và mẫu số

App có **Phân rã biến động chỉ số** cho cả bốn ratios. Đặt N0/D0 là kỳ trước,
N1/D1 là kỳ hiện tại. Giữ cùng original-filing/comparability gates; không skip
kỳ không supported để tìm baseline đẹp hơn.

| Bước | Công thức | Diễn giải |
|---|---|---|
| Tử số trước | N1/D0 − N0/D0 | Đổi tử số, giữ mẫu số kỳ trước |
| Mẫu số sau | N1/D1 − N1/D0 | Sau đó đổi mẫu số, giữ tử số hiện tại |
| Tổng thay đổi | N1/D1 − N0/D0 | Tổng đóng góp của hai bước, cộng rounding residual |

Share ratios hiển thị effects bằng điểm phần trăm; current ratio dùng lần.
Có prior/current numerator/denominator USD, baseline/counterfactual/current
ratios, exact formulas và residual trong JSON. Precision60 có thể tạo residual
rất nhỏ; app không làm tròn residual thành trạng thái reconcile tuyệt đối.

Ví dụ N0=10, D0=100, N1=20, D1=200: tỷ lệ giữ10%, nhưng tử số đóng góp
+10 điểm phần trăm và mẫu số −10 điểm phần trăm. Chỉ đọc total delta0 sẽ bỏ
qua hai biến động lớn bù trừ nhau. Numerator âm/zero vẫn được giữ nếu inputs
supported và denominators dương; relative growth có gate riêng.

Thứ tự phân rã ảnh hưởng attribution; đổi thứ tự sẽ cho effects khác, dù total
không đổi. Đây là identity số học, chưa chứng minh causal drivers, chất lượng
doanh thu, recurring earnings, sức khỏe doanh nghiệp hoặc covenant compliance.

1. Kiểm tra CIK, report date, filing date, selected accession và số supported ratios.
2. Đọc levels và changes của cùng issuer. Không dùng bảng này làm same-period peer ranking giữa AAPL/MSFT/F/GM vì fiscal calendars và consolidated scope khác nhau.
3. Khi thấy biến động, mở **Filings, amendments và exact source inputs**. Đối chiếu numerator/denominator và concept evidence trong selected filing.
4. Khi comparison bị chặn, đọc gate cụ thể trước kết luận deterioration/improvement. Missing/ambiguous facts không phải zero.
5. Bấm **Xuất SEC trend JSON** để giữ filters, original/baseline statements, exact deltas, comparison mappings và source digests.

Latest five-period exports có 20 period rows và 80 ratio cells trên bốn issuers. **67 ratios supported** được kiểm tra số học từ exact financial fields; các cells còn lại giữ unavailable. GM có revenue ambiguity nên net margin và OCF/revenue không được tính. Đây là coverage của saved API snapshot tại cutoff 2026-10-10.

## Verification và giới hạn

Checkpoint driver bridge: backend receipt
`artifacts/private/sec-bridge-tests-20261010.xml`: **46 tests PASS** gồm
bridge10, trends13, memo10 và coverage13. Independent Fraction arithmetic
kiểm tra identities, offsetting effects, negative/zero numerator, recurring
division, gap/concept/duration/missing gates và ambiguous-original linkage.
Các captures memo cũ giữ nguyên; memo mới chứa bridge/source-method digest
trong annual trend được server tạo.

Browser `artifacts/private/sec-trends-qa-3cf29a711bdc/receipt.json`:
**6 groups PASS**, four issuer UI/private exports, 67 supported ratio cells
và65 supported bridge cells kiểm tra với independent rational arithmetic,
comparison statuses trong tables,3/5/10 selector/reload/mobile/outage recovery
và unchanged frozen holdout ledger. Residual trong bảng hiển thị compact
(zero hoặc scientific notation); exact decimal nằm trong bridge evidence/JSON.

`artifacts/private/sec-trends-qa-cc887f418aa3/receipt.json`: 6 nhóm PASS, gồm actual UI/export của bốn issuers, selector/reload, mobile, outage/recovery và pre-source cutoff empty. Exact supported ratios và comparable deltas đối chiếu source-field arithmetic. Holdout access ledger không đổi.

Backend có 41 distinct tests trong SEC financials/views/trends, gồm comparability boundaries, concept changes, gap, ambiguous originals/amendments, positive/zero/negative baseline, invalid filters và real HTTP origin/attachment guards. Receipts: `sec-trends-tests-20261010.xml` và `sec-trend-http-tests-20261010.xml` (12 trend tests overlap, không cộng hai totals trực tiếp).

Current SEC API snapshot và filing-date cutoff chưa đủ chứng nhận point-in-time backtest. Trend không cung cấp default labels/issuer PD, debt-service schedule, DSCR, covenant legal terms hoặc compliance assessment. Những inputs này tiếp tục là dependencies C4 trong [plan](PLAN_KPI_ANALYTICS_NEXT_VI.md).
