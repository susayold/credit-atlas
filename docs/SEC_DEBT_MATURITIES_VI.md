# Đáo hạn gốc nợ theo filing SEC

Mở **P3 Issuer financials → Debt maturities**. Controls issuer, filing và cutoff
ở đầu workspace áp dụng trực tiếp. Chọn **Long-term debt only** hoặc **Debt
and capital lease** trong tab. Hai concept families giữ riêng; không fallback
qua nhau, qua filing cũ hoặc qua rolling-maturity concepts.

## Câu hỏi và số liệu

Principal được công bố tập trung vào những fiscal-year buckets nào? App đọc
năm1, năm2, năm3, năm4, năm5 và sau năm5 từ đúng selected filing. Mỗi dòng có
exact USD, concept, status, số candidates và share khi lịch đủ dữ liệu.
Source labels/descriptions giữ trong Definitions & exact maturity evidence.

| Chỉ số | Công thức / điều kiện | Diễn giải |
|---|---|---|
| Supported buckets | Count supported /6 | Coverage trong nhóm concept đã chọn |
| Supported subtotal | Sum các bucket supported | Có thể chỉ là partial subtotal; không thay total |
| Disclosed schedule total | Sum6 khi tất cả supported và không âm | Tổng principal của6 bucket; chưa là total debt/EAD/debt service |
| Bucket share | Bucket / disclosed schedule total dương | Phân bố principal được công bố, không là PD |
| First-three-years share | Sum năm1–3 / total dương | Concentration theo fiscal-year definitions nguồn |
| Largest buckets | Tất cả buckets cùng maximum, khi lịch đủ và total dương | Không ép chọn một bucket trong trường hợp hòa |

Zero trong nguồn là số thực; missing/ambiguous không thành zero. Lịch đủ nhưng
tổng0 có status COMPLETE_ZERO_SCHEDULE và không tính shares. Bucket âm giữ
exact evidence nhưng chặn total/shares với INVALID_NEGATIVE_BUCKET.

## Lựa chọn facts

Match exact CIK/accession, form, filing date, report-end instant, USD và us-gaap
concept. Duration facts bị loại. Duplicate values bằng nhau vẫn giữ candidates;
contradictory values tạo ambiguous. Không dùng một observation của filing khác,
ngày báo cáo khác hoặc một fiscal-year label gần giống để thay dữ liệu thiếu.

Nhóm debt-only dùng các LongTermDebtMaturitiesRepaymentsOfPrincipal concepts.
Nhóm debt/capital lease dùng các LongTermDebtAndCapitalLeaseObligations
repayment/maturity concepts tương ứng. Không cộng hai nhóm vì có thể overlap.
Các available-for-sale/held-to-maturity securities là tài sản đầu tư và không
được đưa vào lịch principal payable này.

Tên NextTwelveMonths trong debt-only tag có source definition là next fiscal
year và loại rolling approach. App dùng definition nguồn, không suy lịch ngày
thanh toán hoặc rolling calendar year từ tên tag. After-year-five là bucket
open ended; không dựng midpoint, maturity duration hay payment date giả.

## Dữ liệu hiện có

Default debt-only, selected latest annual filing trong snapshot lưu với cutoff
2026-10-10: Apple và Microsoft có6/6 supported buckets; Ford và GM có0/6.
Điều này mô tả khả năng trích xuất các standard concepts của snapshot, không
khẳng định Ford/GM không có nợ hoặc không công bố thông tin ở custom tags/notes.

Apple có disclosed six-bucket total91,281,000,000 USD; năm1–3 chiếm khoảng
34.806% trong lịch này. Không reconcile máy móc với balance-sheet carrying debt:
discounts/premiums, leases, short-term debt, scope và contract terms có thể khác.

## Memo và export

**Xuất maturity JSON** giữ full filters, selected filing, exact candidates,
definitions, source/method hashes, subtotal/total/share calculation và limits.
Link bị gỡ khi loading hoặc API error để tránh tải scope cũ.

Memo mới capture **debt_maturities** phía server: explicit family hiện chọn
(default debt_only), exact selected accession và cutoff bằng filing date của
selected filing. Requested/resolved scope lưu debt_scope. Revisions narrative
giữ original capture; memo cũ không backfill. API scope cũ5/6 fields vẫn nhận
được default family, không đổi records đã lưu.

## Dependencies còn thiếu

Instrument/facility identities, precise repayment dates/amortization, coupons
và rate resets, interest payment schedules, borrower cash available for debt
service, signed covenant definitions/test dates/thresholds và permitted
adjustments. Vì vậy facility schedule, interest schedule, DSCR, covenant
compliance và historical-availability qualifications vẫn false.

P3.08 hiện một phần: source principal maturity profile chạy được; full debt
calendar/cash shortfall/refinancing scenarios chưa hoàn thành. C4 vẫn cần inputs
và qualification riêng. Existing SEC Excel xuất financial ratios/coverage;
maturity profile xuất riêng qua **Xuất maturity Excel** trong tab này.
[Công thức và kiểm tra](SEC_MATURITY_EXCEL_VI.md). Không cộng hai debt families.

## Kiểm tra

Backend `sec-debt-tests-final-20261010.xml`: **38 tests PASS**, gồm instant/
filing/unit/concept guards, duplicate/conflicting facts, complete/partial/zero/
negative profiles, cutoff/private HTTP attachment và memo immutable capture.
Browser QA đối chiếu từng candidate với raw SEC companyfacts, totals/shares
bằng Decimal, family selector/reload/mobile và controlled source outage.

`sec-debt-qa-662fad1cb983/receipt.json`: **4 groups PASS**, four issuers raw
reconciliation, family/no-fallback, reload/mobile/outage và unchanged holdout
ledger. `corporate-memo-qa-2cf35018c3e3/receipt.json`: **4 groups PASS**,
explicit debt/capital-lease capture đúng selected accession/filing date,
immutable revision/history/export và archived QA records. USD display có dấu
phân cách hàng nghìn từ exact string; JSON giữ nguyên source values.
