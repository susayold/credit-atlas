# CreditAtlas — issuer filings và nguồn debt/covenant

Checkpoint 11/10/2026. Mở SEC issuer workspace → **Issuer filings**.

## Timeline trong app

Timeline dùng verified submissions/history metadata, gồm 8-K, 8-K/A,
10-K, 10-K/A, 10-Q và 10-Q/A. Chọn issuer, cutoff, từ ngày, form group
và item code. Phân trang 25 dòng; summary tính trên toàn bộ matched filings.
JSON export giữ đúng filters/page, source captures và từng source occurrence.

Filing date, report date và acceptance timestamp được giữ riêng. Amendment
là accession riêng, không tự thay original. Một filing có nhiều items nên
item counts có overlap, không cộng thành số unique filings.

1.01/2.02/2.03 là gợi ý tìm agreement/results/obligation documents. Không
suy default, covenant breach, outstanding debt hay borrowing amount từ item code.
Legacy hoặc thiếu items không được hiểu là không có credit events.
Full filing/exhibit contents phải thu thập và đọc riêng trước khi trích legal terms.

## Acquisition mới

Nguồn `sec-source-2dd5a9f2962a` tải qua HTTP/API cho AAPL, MSFT, F và GM,
gồm submissions, toàn bộ history files được manifest chỉ định và companyfacts.
Mỗi file có URL, bytes, SHA-256 và retrieved_at; snapshot cũ không bị ghi đè.
Canonical case `sec-case-2740ddb85d45`, app view `sec-view-913c93906c18`.
Snapshot mới selectable trong app; các study/model/memo cũ giữ nguyên source.

Nguồn dữ liệu không có default labels hoặc qualification cho issuer PD.
File được tải mới không tự chứng minh có thêm observations so với snapshot cũ.

## Full-text debt/covenant source mới

HTTP SEC Archives cho tài liệu Ford 20/05/2026 trả403, được lưu là failure.
Không bypass access. PDF Ford 28/07/2025 được tải qua URL tài liệu công bố của
doanh nghiệp trên CloudFront; 64 trang,594149 bytes, SHA-256:
`20f5e0471d8809213a6fb28c051acbe3f3167480d7e06cfd151c7cfc8460e85f`.

Folder `private evidence omitted from public release` giữ original PDF,
page text, rendered pages1/10/42, identity check và `draft-terms.json`.
Đã đọc các trang liên quan, chưa full legal/amendment-chain review.

Draft intake có commitment3 tỷ USD, availability end28/07/2026 và drawn-loan
maturity31/12/2028. Commitment không phải outstanding principal.
Section7.1 có minimum Available Liquidity4 tỷ USD; definition bao gồm specified
unused revolving commitments và các thành phần liquidity với exclusions.
Consolidated cash SEC không được dùng thay contract-defined Available Liquidity.

Actual contract-defined liquidity chưa có; headroom/compliance giữ unavailable.
Later amendments/current terms chưa verified. Draft terms chưa được dùng để
gắn breach badge hoặc gọi complete covenant workbench/DSCR.

## Phần tiếp theo

Thu later amendments và dated facility utilization/liquidity inputs; version
term definitions/effective dates; xây source-bound covenant intake/calculation
và reviewer workflow. Timeline discovery là một bước của P3.06/P3.10; không
đóng toàn bộ credit memo, P3.07 covenant hoặc P3.08 debt-service schedule.

Nghiệm thu: backend29PASS `sec-events-tests-final-20261011.xml`; browser8groups
PASS `sec-events-qa-a355fade2b6e`, raw four-issuer/date/filter/page comparison,
private JSON, reload/mobile và outage recovery. New-source independent audit
`sec-audit-a0df37e6ae3b` PASS;14files byte-identical với prior snapshot.

Tiếp tục acquisition: Ford credit amendments17/04/2025 PDF171pages
`sec-documents-a1aa8dad9beb` và annual report2025 PDF212pages
`sec-documents-563b8f103cfd` đã tải/identity-check/text extract.
Annual report có liquidity metrics riêng của Ford Credit và của parent;
không dùng Ford Credit net liquidity để so parent contractual threshold.
Candidate snippets giữ source-page refs và cần scope review trước calculation.
Ba PDF tổng447pages; không gọi full legal terms/current compliance verified.

## Amendments2026 và app facility calendar

Đã thu Ford15/04/2026PDF333pages, tổng4PDF780pages. Term availability end được amendment kéo dài tới31/12/2026; ngày28/07/2026 phía trên chỉ thuộc original2025version. Corporate/supplemental/364-day maturities cũng đã cập nhật trong versioned app calendar. Xem [Facility calendar](FACILITY_CALENDAR_AND_COVENANT_VI.md). Selected corporate covenant definition/clause có evidence; full legal chain và actuals vẫn chưa qualified.
