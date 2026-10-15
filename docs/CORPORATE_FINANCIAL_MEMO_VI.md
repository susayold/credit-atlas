# Corporate financial memo

Mở **P3 Issuer financials → Corporate memo**. Chọn issuer, filing và cutoff ở controls phía trên trước khi tạo memo. Đây là financial-evidence memo của một issuer CIK; không nối issuer này với SBA borrowers hoặc UCI bankruptcy rows.

## Nội dung memo

- Title, owner và trạng thái draft/reviewed/archived.
- Business summary, liquidity, leverage, profitability, cash flow.
- Risks/hypotheses, missing information, conclusion và next validation action.

Title, owner, business summary, conclusion và next action bắt buộc. Các phần khác để analyst bổ sung theo evidence thực. App không điền một nhận định hoặc rating tự động. Owner và reviewed là thông tin tự khai, chưa có authenticated reviewer/sign-off.

## Capture nguồn

Memo mới capture thêm **debt_maturities**: scope đang chọn trong Debt maturities
(default debt_only), selected filing accession, cutoff bằng filing date,
six-bucket principal profile, subtotal/total/shares và exact source evidence.
Requested/resolved scope giữ debt_scope; old captures không backfill.
[Definitions và giới hạn](SEC_DEBT_MATURITIES_VI.md).

Memo mới còn capture **interest_coverage**: expense concept hiện chọn trong
Interest coverage (mặc định InterestExpenseNonoperating), source fields,
operating-income/reported-OCF ratios, exact candidates và source/method hashes.
Coverage dùng selected filing date làm cutoff; requested/resolved scope ghi
concept explicit. Memo cũ không backfill. Browser receipt
`corporate-memo-qa-0eaa9fd5829e` kiểm tra chọn InterestExpense, anchored cutoff,
immutable revisions/export và mobile: **4 groups PASS**.

Khi bấm **Lưu corporate memo** lần đầu, server verify SEC view và đọc selected filing theo exact CIK/accession/cutoff. Server tự tạo annual trend và chụp toàn bộ source projection; browser không gửi actuals hoặc fabricated capture.

Trend trong memo dùng cutoff bằng **filing date của selected filing**. Nếu analyst chọn filing cũ, memo không trộn thêm filings phát hành sau nó. Cửa sổ3/5/10 report periods dùng selector Annual trends hiện tại, mặc định5. Trend vẫn có original-10-K/comparability rules riêng; selected statement có thể là amendment được analyst chọn explicit, nên hai phần giữ selection declarations riêng.

Capture gồm requested/resolved scope, selected filing fields/concepts/ratios, annual history và baseline statements, source digests, evidence digest và thời điểm capture. Các facts/deltas tính theo verified SEC workflows; narrative là input của analyst, không được server xác minh từng assertion. Mỗi memo bound vào whole selected source scope; chưa có claim-to-field citation editor.

## Revisions và lịch sử

Sửa title/owner/narrative/status tạo revision mới; captured evidence giữ nguyên. Concurrent stale revision trả409, cần **Đọc lại memos** và mở latest revision trước khi sửa. Muốn chụp nguồn/kỳ mới, tạo memo mới.

Danh sách lọc theo SEC view + CIK. Lịch sử/JSON giữ original capture kể cả khi current source sau đó không còn verify được; new memo lúc đó không được capture. Update narrative không thay source và không recalculate evidence cũ.

**Xuất corporate memo JSON** gồm current memo và toàn bộ revisions. Lưu ở private SQLite `artifacts/private/corporate-memos.sqlite3`, cùng origin loopback guards của app. Không nhận file path hoặc executable từ client.

## Scope và dữ liệu còn thiếu

Financial ratios và annual trend chưa đủ DSCR, covenant headroom, debt-maturity/refinancing analysis, credit rating hoặc issuer PD. Cần debt-service cashflows, facility schedules, contract definitions/test dates, issuer events và verified legal terms. Memo ghi qualification flags false và giữ missing-information narrative; reviewed không đổi các qualification flags.

P3.06 hiện có financial memo editor/capture/history/export. Complete corporate credit memo với issuer-event/debt/covenant inputs vẫn là phần còn lại trong [plan](PLAN_WORKBENCH_DETAIL.md).

## Kiểm tra

Browser `artifacts/private/corporate-memo-qa-1deb923c721e/receipt.json`: **4 nhóm PASS**. AAPL/GM create/update qua actual UI, source capture và filing-date anchored trend, immutable revision/history/private export, issuer-scoped reload/mobile, no browser exceptions và holdout access ledger unchanged. Hai records QA giữ archived; title/owner ghi rõ QA, không là business conclusions.

Backend `artifacts/private/corporate-memo-tests-final-20261010.xml`: **25 tests PASS** gồm memo+existing HTTP/review regression. Kiểm tra invalid/missing fields, unsupported source/cutoff, injected capture, immutable scope, revision conflict, source outage/historical readability, loopback guard, attachment/no-store và isolation theo issuer. Test results không thay authenticated bank approval hoặc missing legal/data qualification.
