# Facility calendar và covenant evidence — 11/10/2026

## Phạm vi đã triển khai

Trong Business → SEC issuer → **Facilities & covenant**, app đọc catalog
nguồn riêng của Ford CIK0000037996, không join facility với issuer bằng tên.
Năm tranches: hai corporate revolving, supplemental revolving,364-day
revolving và delayed-draw term loan. Catalog có10phiên bản từ ba filings.
Chỉ có selected acquired disclosures, không phải toàn bộ debt inventory.

Cutoff phải bao gồm cả filing date và effective date. Mỗi tranche lấy latest
eligible version; prior version giữ riêng để thấy ngày thay đổi. Cutoff trước
filing không lấy terms tương lai. Các issuer khác hiện chưa có catalog.

| Tranche | Disclosed commitment USD | Terms2025 | Terms15/04/2026 |
|---|---:|---|---|
| Corporate shorter |3400000000|Maturity17/04/2028|Maturity13/04/2029|
| Corporate longer |10100000000|Maturity17/04/2030|Maturity15/04/2031|
| Supplemental |2000000000|Maturity17/04/2028|Maturity13/04/2029|
|364-day|2500000000|Maturity16/04/2026|Maturity14/04/2027|
|Delayed draw|3000000000|Draw availability28/07/2026|Draw availability31/12/2026|

Delayed-draw loan maturity31/12/2028 giữ nguyên; draw availability end là ngày
khác. Tổng các commitments trong selected catalog là21tỷ USD sau28/07/2025;
18tỷ trước đó, từ17/04/2025. Không cộng hai phiên bản của cùng tranche.
Các tổng này không phải debt principal, EAD hoặc unused availability; local
facilities và các debt instruments khác nằm ngoài catalog.

Nguồn2026: [Ford8-K15/04/2026](https://www.sec.gov/Archives/edgar/data/37996/000003799626000079/f-20260415.htm),
acquired issuer-hosted PDF333pages,2553943bytes,
SHA256 `7fcf8c25fade59e2965d8013131e5dc96d4709297289fc87ff84f22758a59e10`.
Folder `data/private/sec-documents/sec-documents-b46630da17d1` có acquisition,
original PDF, extracted page text và identity receipt. Cộng ba PDF trước:
bốn PDF780pages. PDF780pages không đồng nghĩa780pages đã legal-review.

## Covenant source và dữ liệu còn thiếu

Corporate revolving definition **Available Liquidity** trên PDFpage39,
printedpage12; minimum4tỷ USD tạiSection7.2 PDFpage132, printedpage105.
Hai trang đã render và visual-review tại
`artifacts/private/facility-source-review-20261011`.
Scope áp dụng khi commitments còn hiệu lực hoặc các nghĩa vụ nêu trong clause
còn tồn tại. Cần đọc đầy đủ agreement để xác minh applicability.

Definition có specified available commitments và consolidated cash/equivalents/
marketable securities trừ FMCC, foreign-subsidiary holdings và restricted cash.
SEC consolidated cash, parent-reported global liquidity hoặc Ford Credit
liquidity không tự là covenant actual. Ngay cả approximate US cash share trong
annual report cũng không thay exact legal component ledger.

Actual liquidity, headroom, compliance, principal outstanding, undrawn
availability và DSCR hiện **unavailable**. Không suy zero, không gắn breach
badge, không coi commitments là khoản đã rút. Full amendments, redactions,
permitted adjustments và compliance certificates vẫn cần review.

Đích tiếp theo: source-bound actual-input/adjustment ledger, test/observation
dates, facility utilization và outstanding principal, interest conventions/
cashflows; tính headroom/DSCR khi các dependencies đạt qualification.
P3.07 giữCần dữ liệu, P3.08 giữMột phần.

## Evidence và API

Immutable catalog: `artifacts/private/ford-facilities-1ac0d5d77a40`.
Catalog receipt khóa hashcatalog, builder và từng sourcePDF/page extraction;
API verify lại nguồn, page text và extraction anchors. Hash checks phát hiện
thay đổi, không thay legal/numerical independent review.

GET `/api/sec-facilities` và private attachment
`/api/sec-facilities-report` nhậnview_id/cik/asof. Headerno-store, local-origin
guards, unknown/duplicate scope rejection. SECview dùng để xác minh issuer
identity; facility sources là acquisition riêng, thể hiện trong export.

Backend facilities + SECevents:34testsPASS,
`artifacts/private/facilities-tests-20261011.xml`.
Browser/source/export/mobile/outage5groupsPASS:
`artifacts/private/facilities-qa-18dedf9f1512/receipt.json`.
Desktop/mobile screenshots đã xem; frozen holdout ledger unchanged.
Không nâng completion chỉ vì narrow backend/browser testsPASS.
