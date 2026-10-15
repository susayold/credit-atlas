# API nguồn doanh nghiệp và payment rules — 11/10/2026

## Dữ liệu mới đã thu

Trang SEC Filings chính thức của Apple dùng public GET feed
`/feed/SECFiling.svc/GetEdgarFilingList`. Code widget trên chính trang này
công bố cách dùng exchange=CIK, symbol, year, filingTypeList và paging.
Không đăng nhập, không bypass SEC/Clarity; chỉ lấy tài liệu được issuer công bố.

Script `scripts/acquire_apple_base_indenture.py` lấy S-3ASR năm2024,
chọn đúng filing01/11/2024/CIK0000320193 và CONVPDF URL từ DocumentList.
Original response giữ trong `issuer-feed.json`; acquisition receipt có
feed URL, hash, FilingId17933238, PDF URL/hash/bytes và retrieved_at.
Không coi Q4FilingId là SEC accession; SEC accession của registration là
0001140361-24-044880.

Bundle S-3ASR gồm base indenture92pages,818655bytes:
`private evidence omitted from public release`.
SHA256 `f1a1d73cef7fadd2d3065a826e4d2618e48ad02d976df55e7c80d38fb7fa1183`.
Đã identity-check Apple/date/indenture, extract toàn bộ page text;
selected clauses render để kiểm tra text/layout. Không có full legal-review claim.

[Trang issuer](https://investor.apple.com/sec-filings/default.aspx),
[SEC base indenture](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).

## App và ý nghĩa nghiệp vụ

SEC issuer → Apple → **Payment rules**. Có5clause readings, section/page,
original page evidence, issuer-feed/source hashes và private JSON export:

| Rule | Section | PDF page | Điều cần kiểm tra |
|---|---|---:|---|
|Business Day|101|38|Weekends và bank closures tại Place of Payment; series overrides|
|Place of Payment|101|40|Place(s) của series được xác định theo Section301|
|Legal Holidays|113|45|Next succeeding Business Day áp dụng cho payment/maturity, có exceptions|
|No interest for postponement|113|46|Không cộng interest trong khoảng chuyển ngày theo clause này|
|Office/agency|1002|72|Office và fallback trustee addresses cần phân biệt với series payment place|

New York governing law hoặc trustee officeChicago không tự chứng minh
calendar jurisdiction. Section1002 có officeNewYork trong required/fallback
context; chưa đủ để tự chọn calendar cho mọi payment place/series.
Không dùng federal/NYSE holiday calendar rồi gọi là legal banking calendar.

Adjusted dates còn unavailable. Tiếp theo cần series place/overrides/notices,
bank-closure calendar đúng phạm vi và dated outstanding/redemption/payments.
Lịch Note cashflows hiện vẫn nominal/no-redemption path và giữ qualification.
Full debt-service/DSCR/covenant actuals chưa đạt.

## Nghiệm thu và lineage

Immutable rules `private evidence omitted from public release`.
Verification khóa builder/rules/PDF/page text/feed hashes và kiểm tra metadata
CIK/form/date/DocumentList→PDF link. Cutoff/issuer guards không trả future
source hoặc rules của issuer khác. Base source tách khỏi SECfinancialview.

GET `/api/sec-note-rules`, `/api/sec-note-rules-report` vớiview_id/cik/asof;
private attachment/no-store/local-origin/duplicate/unknown guards.
Backend rules+note schedules34testsPASS,
`private evidence omitted from public release`.
Browser/source/export/mobile/outage6groupsPASS: `private evidence omitted from public release`. Desktop/mobile và sourcePDF45/46/72 đã visualreview; frozen holdout ledger unchanged.
P3.08/C4 vẫnMột phần; goal100% chưa đạt.
