# Excel lịch đáo hạn gốc nợ

Trong **P3 Issuer financials → Debt maturities**, chọn issuer, annual filing,
cutoff và maturity scope; bấm **Xuất maturity Excel**. Hai nhóm debt_only và
debt_and_capital_lease xuất riêng, không cộng thành một lịch nợ.

## Hai sheets

**Maturities** có selected filing/report date/cutoff, six fiscal-year buckets,
principal USD, source status và share. Phần summary có supported-bucket count,
supported subtotal, complete six-bucket total, first-three-years share và
schedule status. Source-exact principal/share text giữ bên phải calculations.

**Facts** giữ numeric USD input cạnh exact text, concept, source status,
report/filing dates, accession, exact candidates, source definition và filing URL.
Có source/case/method hashes và selection rule. Ngày là typed Excel dates;
CIK/accession/exact values là text. Blue numeric cells là source inputs của
workbook; green links lấy từ Facts; cùng-sheet calculations dùng dark text.

## Công thức và guards

- Bucket principal link Facts khi source supported và input numeric.
- Subtotal = SUM các principal numeric khi có ít nhất một; không coi subtotal
  partial là complete total.
- Complete total cần6 supported numeric inputs và tất cả nonnegative.
- Bucket share và first-three-years share cần complete total dương.
- Source zero được giữ0; complete zero schedule không có shares.
- Negative bucket chặn total/shares; missing/ambiguous giữ Unavailable.
- Excel status cập nhật theo source statuses/inputs; NUMERIC_INPUT_UNAVAILABLE
  phân biệt status supported nhưng ô numeric đã bị sửa thành text.

Source edits trong workbook cần đánh giá lại filing/concept/date scope; không
tự tạo source qualification mới. Refresh bằng export lại từ app. Excel dùng
floating point; exact source/derived decimal text giữ để reconciliation.
Six-bucket total không là total balance-sheet debt, EAD, debt service hoặc PV.
After-year-five open ended; không tạo exact payment dates, duration hay DSCR.

## API và capture

POST `/api/sec-debt-workbook` chỉ nhận bounded source filters. Server verify
SEC view và tạo maturity report; không nhận actuals, source capture, output
path hoặc executable từ browser. Nếu không có selected annual filing thì
reject; nếu filing có nhưng buckets missing vẫn xuất với Unavailable. Route
giữ same-origin/local-client, JSON/body bound và private/no-store attachment.
Export control bị gỡ trong lúc đổi scope hoặc source loading/error.

## Kiểm tra

Backend `sec-debt-xlsx-tests-20261010.xml`: **43 tests PASS**, gồm source-filter
contracts cho two workbook exporters, maturity guards và real HTTP boundaries.
Builder kiểm tra formula cache so với exact report rồi thay input để kiểm tra
complete-zero, missing và negative dependencies; restore source trước export.

Saved XLSX được audit độc lập bằng XML/Fraction/Decimal: formula refs, exact
source text/leading-zero CIK, bucket values/shares, subtotal/total/first-three-
years share/status và absence of Excel error cells.
Browser `sec-debt-xlsx-qa-de64508d62d6/receipt.json`: **5 groups PASS**;
actual POST/download cho AAPL/MSFT/default family và AAPL debt/capital-lease
family, raw SEC reconciliation, mobile/export-error recovery và unchanged
frozen holdout ledger. Mỗi workbook có6 bucket rows và23 formulas. AAPL/MSFT
có6 supported buckets; AAPL lease family0 supported buckets, không tạo total0.

Export tài chính B5 đã kiểm tra lại qua real HTTP sau thay đổi exporter:
`sec-debt-workbook-preview/financial-export-regression.json` PASS,
MSFT3-period workbook18rows/28numeric results/12bridges/204formulas,
saved XML audit và no-store attachment. Historical financial artifacts không đổi.

Microsoft Excel desktop recalculation chưa được chạy; cached calculation và
PNG render không là native Excel verification. B6 workbook được triển khai
trong phạm vi disclosed principal profile; C4 facility/debt-service/legal inputs
tiếp tục cần bổ sung. [Source definitions](SEC_DEBT_MATURITIES_VI.md).
