# Phân tích chi phí lãi vay và coverage

Mở **P3 Issuer financials → Interest coverage**. Chọn issuer, cutoff, expense concept và cửa sổ 3/5/10 kỳ. Phần này dùng SEC companyfacts/submissions đã lưu và được verify; không thay bộ 88 KPI nghiệp vụ + 22 kiểm soát chất lượng trong KPI Monitor.

## Dữ liệu và công thức

| Nội dung | SEC concept / công thức | Cách đọc |
|---|---|---|
| Lợi nhuận hoạt động | OperatingIncomeLoss | Reported annual USD; giữ số âm |
| Dòng tiền hoạt động | NetCashProvidedByUsedInOperatingActivities | Reported OCF, chưa cộng lại lãi đã trả |
| Chi phí lãi | InterestExpenseNonoperating, InterestExpense hoặc InterestExpenseDebt | Chọn explicit một concept; không tự ghép/đổi tag |
| Operating-income coverage | OperatingIncomeLoss / selected expense | Đơn vị lần; proxy theo operating income |
| Reported-OCF coverage | Reported OCF / selected expense | Đơn vị lần; chưa là cash available for debt service |
| Lãi tiền mặt | InterestPaid và InterestPaidNet | Hai observations riêng; không thay expense denominator |

Không áp ngưỡng tốt/xấu tự động. Một ratio cao cần được xem cùng numerator, denominator, consolidated scope, hoạt động captive finance và thuyết minh filing. Operating income âm tạo ratio âm nếu expense dương; số âm được giữ nguyên để analyst điều tra.

[Federal Reserve](https://www.federalreserve.gov/econres/notes/feds-notes/information-in-interest-coverage-ratios-of-the-us-nonfinancial-corporate-sector-20190110.html) sử dụng EBIT/interest expense cho ICR. Workflow hiện tại chưa xác nhận reconciliation từ operating income sang EBIT theo mục đích sử dụng cụ thể; vì vậy app đặt tên operating-income coverage proxy. OCF cũng có thể đã phản ánh lãi đã trả; không suy DSCR từ tỷ lệ này.

## Quy tắc nguồn

1. Chọn một original 10-K cho mỗi report date trước cutoff. Amendment vẫn giữ riêng; nhiều originals không được tự chọn tùy ý.
2. Match exact CIK, accession, filing date, report end, form, us-gaap concept, USD và annual duration 330–400 ngày.
3. Các observations trùng đúng start/end/value được giữ làm candidates. Nhiều signatures khác nhau tạo ambiguous; không lấy một giá trị thuận tiện.
4. Tử và mẫu phải supported, có cùng start/end; expense phải dương. Mẫu bằng/nhỏ hơn zero, thiếu, ambiguous hoặc period mismatch giữ ratio unavailable.
5. Không fallback từ InterestExpenseNonoperating sang InterestExpenseDebt; không cộng aliases hoặc net interest income. Muốn dùng concept khác, analyst chọn rõ và export scope mới.

Mỗi kỳ hiển thị giá trị USD gốc, hai ratios, support status, ngày bắt đầu/kết thúc, số candidates và exact candidate evidence. Có link sang selected filing concepts. Source definitions lấy từ metadata nguồn; label/description thiếu hiển thị Not supplied. JSON export giữ source/method hashes, scope, exact values và limitations.

## Ví dụ trên snapshot hiện có

Với cutoff 2026-10-10 và default InterestExpenseNonoperating, dữ liệu latest annual của MSFT và Ford có denominator supported; Apple và GM thiếu selected concept trong cùng filing. Không dùng cash interest của GM để điền chỗ thiếu. Các kỳ cũ có thể dùng tag khác, nên support của cửa sổ 5 kỳ không đồng nghĩa đủ cả 5 kỳ.

Đây là mô tả snapshot đã lưu, không là market feed cập nhật liên tục hoặc issuer rating. Historical filing cutoff chưa chứng minh point-in-time availability của toàn bộ companyfacts được tải sau đó.

## Corporate memo

Memo mới capture thêm coverage với expense concept hiện đang chọn; mặc định InterestExpenseNonoperating nếu chưa đổi. Coverage trong memo dùng cutoff bằng filing date của selected filing và cửa sổ annual hiện tại. Source capture được tạo phía server; revisions narrative giữ nguyên evidence. Memo cũ không bị backfill hoặc recalculate.

## Các phần cần thêm

Debt schedules, principal repayments, facility terms, permitted EBITDA adjustments, covenant test dates/thresholds và scope của công ty con. Các qualification EBIT ICR, DSCR, covenant compliance và issuer PD hiện false. Phần này bổ sung C4 financial analysis; chưa đóng C4 debt-service/covenant gate.

Backend: `artifacts/private/sec-coverage-tests-final-20261010.xml`, 33 tests PASS cho coverage, memo capture và HTTP guards. Browser QA đối chiếu exported observations với raw SEC companyfacts, tính lại ratios bằng Decimal, kiểm tra selectors/reload/mobile/outage và giữ nguyên frozen holdout access ledger.

Browser receipt `artifacts/private/sec-coverage-qa-1c32f79854e0/receipt.json`:
**4 groups PASS**. Default 5-period scope có tổng supported ratio cells:
AAPL0, MSFT4, Ford2, GM0 (mỗi kỳ có hai ratio cells). Cả supported và
missing/ambiguous field candidates được đối chiếu raw; switching sang
InterestExpense kiểm tra riêng, không fallback. Desktop/mobile screenshots
đã kiểm tra trực quan; latest-period reading hiển thị nguyên nhân thiếu inputs.
