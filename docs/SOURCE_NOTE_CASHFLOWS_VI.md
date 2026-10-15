# Note cashflows có terms nguồn — 11/10/2026

## Dữ liệu và cách dùng

Mở Business → SEC issuer → Apple → **Note cashflows**. Chọnall hoặc một trong
bốn note series phát hành12/05/2025 và ngày kết thúc lịch danh nghĩa.
Nguồn là8-K accession0001140361-25-018400, filing12/05/2025, earliest event
report05/05/2025. SECmetadata đã đối chiếu với certificate; hai ngày không
được thay lẫn nhau. Terms và projection là các acquisition riêng của SECview.

| Series | Original issue principal USD | Coupon/year | Maturity |
|---|---:|---:|---|
|2028|1500000000|4.000%|12/05/2028|
|2030|1000000000|4.200%|12/05/2030|
|2032|1000000000|4.500%|12/05/2032|
|2035|1000000000|4.750%|12/05/2035|

Certificate yêu cầu coupons12/05 và12/11, first coupon12/11/2025;
day-count360-day/twelve30-day months, FINRA11620(b). Series này có regular
periods180/360, không cần suy irregular coupon convention.
Principal trả ở stated maturity trong no-redemption path.

Lịch dùng **original full issue principal, no early redemption/default,
no additional issuance**. Đây là kịch bản từ terms nguồn thực; không phải
đã xác minh current outstanding hoặc actual paid amounts.
Các notes callable, nên redemption/default/repurchases/amendments có thể làm
khác lịch này. Maturity không thay bằng par-call date.

Nominal coupon dates và adjusted payment dates giữ riêng. Base indenture
Business Day definition/holiday calendar chưa qualified; adjusted datesnull.
Không dùng weekend-only calendar rồi gọi là exact legal settlement dates.
Cutoff lọc filing availability vànominal dates, asofexclusive/endinclusive;
coupon chuyển ngày có thể nằm khác window. Không suy trạng thái đã trả nợ.

## Công thức và đối soát

`interest = original_issue_principal × annual_coupon_rate ×180/360`.
`principal = original_issue_principal` ởmaturity, các kỳ khác0.
`total = interest + principal`. ExactDecimal, không floatcash arithmetic;
unsupported irregular/sub-cent schedules bịreject.

Full lifetime path:50coupon/principal rows;4.5tỷUSD principal,
1.18tỷUSD interest,5.68tỷUSD total. Từcutoff11/10/2026 đến12/05/2035:
42rows;985.5triệuUSD projected interest,4.5tỷUSD principal,
5.4855tỷUSD total. Các kết quả phụ thuộc pathassumptions trên.
Annual buckets làcalendar year, không fiscal maturity buckets của SEC.
Partial enddate không tự làfullremaining debt service.

## Evidence

AcquiredPDF90pages,589879bytes tại
`private evidence omitted from public release`;
SHA256 `1237b0d46464bd0564997f6f9e061d1a27e21d3dba9236dc229f8839891f1760`.
[SECcertificate](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).
Immutablecatalog `private evidence omitted from public release`, hashes khóa
catalog/builder/PDF/page extraction, terms cópageanchors. PDFpages35/48
đã render và visualreview;41cũng giữrender cho series2035.

API `/api/sec-note-schedule` và privateattachment
`/api/sec-note-schedule-report`; view_id/cik/asof/end/note_id,
local-origin/no-store/duplicate/unknown guards. Export giữsource terms,
pathassumptions, rowformulas, annual partitions vàqualificationfalse.

Backend note+facilities36testsPASS,
`private evidence omitted from public release`.
Browser/source-table independentaudit6groupsPASS: `private evidence omitted from public release`. Desktop/mobile screenshots đã xem; export parity, outage recovery và frozen holdout ledger unchanged.

P3.08/C4 vẫnMột phần: chỉ4series; issuer inventory, latest balance,
actual calendar/payment inputs/full legal regime/covenant liquidity và
cashflow available for debt service vẫn thiếu. Không dùng totals này để
tính DSCR toàn Apple hoặc ECL. Tiếp theo thu baseindenture/calendar evidence,
dated outstanding/redemption history và borrower-scoped actual cashflows.

## Base indenture research cho bước tiếp theo

Đã tìm đúng [Base indenture01/11/2024](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), accession0001140361-24-044880, EX4.1. Section101 định nghĩa Business Day phụ thuộc Place of Payment và ngày ngân hàng được phép/bắt buộc đóng theo luật hoặc executive order. Section113 chuyển payment/maturity tới next succeeding Business Day, không cộng interest cho thời gian chuyển đó. Cần xác minh Place of Payment, các overrides và calendar trước adjusted-date qualification. Hiện mới đọc web, chưa có full acquired base-indenture file trong catalog.

## Acquired base source và app rules

Base indenture đã acquired qua issuer publicAPI trong bundle92pages, `sec-documents-480342e5f2e5`. Payment rules tab có5source clauses và privateJSON, backend34PASS/browser6groupsPASS. [Chi tiết và qualification](ISSUER_API_AND_PAYMENT_RULES_VI.md). Đoạn research phía trên là checkpoint trước acquisition; adjusted dates/current outstanding vẫn chưa supported.
