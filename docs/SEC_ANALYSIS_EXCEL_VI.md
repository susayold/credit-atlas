# Excel phân tích doanh nghiệp

Mở **P3 Issuer financials → Annual trends** hoặc **Interest coverage** rồi bấm
**Xuất SEC Excel**. Export lấy đúng view, CIK, cutoff,3/5/10 report periods và
expense concept hiện tại. Nếu chưa đổi concept, mặc định
InterestExpenseNonoperating. Nút chỉ xuất hiện khi scope đọc thành công và
được gỡ trong lúc đổi bộ lọc hoặc source outage.

## Nội dung

**Analysis** mở đầu bằng latest report date và sáu kết quả: current ratio,
liabilities/assets, net income/revenue, OCF/revenue, operating-income/selected
expense và reported-OCF/selected expense. Bốn ratios đầu có baseline/delta
khi qualified comparison; hai coverage proxies không thêm baseline giả.

Phần chi tiết theo kỳ có current/prior numerator/denominator USD, actual,
baseline, absolute delta, numerator effect, denominator effect, bridge residual,
counterfactual N1/D0, status gates, exact source results và accession. Numeric
inputs link trực tiếp sang Facts; các kết quả được tính bằng Excel formulas.
Annual bridge dùng numerator-first order; không suy causal drivers hoặc rating.

**Facts** giữ input numeric cạnh exact USD text, CIK/accession, report end,
start/end, filing date/form, concept mapping, candidate evidence và filing URL.
Có source/case IDs, source hashes, method hashes và selection/comparison rules.
Baseline ngoài cửa sổ vẫn có facts riêng, không ghép giá trị của năm khác.
InterestPaid/InterestPaidNet giữ làm observations riêng, không đổi expense
denominator hoặc cộng vào OCF. Ngày là typed Excel dates; identifiers/exact
values giữ text, gồm số0 đầu CIK.

## Công thức và missing

Actual = current numerator/current denominator khi source status supported,
numeric inputs có mặt và denominator dương. Baseline có gate tương tự.
Delta cần COMPARABLE status cùng hai ratios numeric. Counterfactual=N1/D0;
numerator effect=counterfactual−baseline; denominator effect=actual−counterfactual;
residual=delta−sum(effects).

Missing/ambiguous/concept change/gap/duration mismatch giữ Unavailable;
không biến text thành zero. Numerator zero/negative hợp lệ vẫn được giữ.
Summary share deltas hiển thị điểm phần trăm; detail share formulas giữ
fraction và Excel percent format. Percent difference ở đây không là relative
growth. Coverage dùng số lần, không là EBIT ICR, DSCR hay covenant test.

Excel numeric calculations dùng floating point; exact decimal60 source results
được giữ text để đối chiếu. Workbook không phải ledger hoặc công cụ sửa source
facts. Nếu analyst thay số liệu trong workbook, phải đánh giá lại chronology,
concepts và comparability gates; gates capture không tự xác nhận input sửa tay.
Refresh bằng cách export lại từ verified app scope.

## Capture và kiểm tra

API POST chỉ nhận source filters; không nhận actuals, source capture, output
path hay executable từ browser. Server verify SEC view và tự tạo annual trend
và coverage. Không có periods trước cutoff thì reject export. Same-origin/local
client, JSON content type và64KB body bound áp dụng. Saved report/XLSX riêng
trong private artifact folder; không công bố lên web.

Backend `sec-workbook-tests-20261010.xml`: **44 tests PASS**, gồm workbook
filter/capture contract, HTTP guards và existing trends/coverage behavior.
Browser `sec-workbook-qa-03d578d3b62d/receipt.json`: **3 groups PASS** gồm
actual UI download, server scope parity, mobile/outage và unchanged frozen
holdout ledger. Saved XLSX được audit bằng XML/Fraction/Decimal độc lập:
30 analysis rows,44 numeric results,20 bridges và328 formulas cho MSFT5 kỳ.
Exact text/leading-zero CIK, source links, formula caches và unavailable cells
được kiểm tra; không có error cells. Workbook render đã được xem trực quan.

Chưa chạy recalculation bằng Microsoft Excel desktop. Formula caches được
kiểm tra bằng Artifact Tool và saved XML; không coi đó là native Excel proof.
Các source/model/legal gates C1–C6 vẫn giữ; B5 workbook không đóng C4.
