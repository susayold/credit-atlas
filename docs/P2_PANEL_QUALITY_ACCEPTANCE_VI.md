# P2.02 — nghiệm thu Panel Quality

Scope: supplied annual sample2012 và case `d01-a24484b21a21`. Kiểm tra data grain,raw blanks,field-specific sentinels,state/terminal mappings và source investigation readouts. Audit dữ liệu không xác thực publication timestamp hoặc release identity của publisher.

## Yêu cầu và evidence

| Yêu cầu gốc | Đối soát | Kết quả |
|---|---|---|
|Origination/performance panel,keys/months|Full canonical counts,unique keys,parent support,reporting coverage|18technical checks khớp|
|Sentinels và quality findings|Raw field blanks so với snapshot; raw token→canonical null cho sáuavailability fields|64blank field counts và6sentinel fields khớp|
|Quality issues và affected counts|Browser so toàn integrity/availability table với verified API|4segment scopes PASS|
|Source investigation evidence|Reported count/status/action,source/feature coverage và investigation order; private report giữ whole-source scope|PASS|
|Unknown/gap không thành current|Independent raw delinquency/state mapping và continuity checks; canonical/source boundary tests|4.510.559monthly mapping rows,0differences|
|Không nối khoảng thiếu|Gap detection và13-month contiguous support; boundary tests; P2.05/P2.06 independent continuity acceptance|PASS|

## Kết quả cụ thể

- 50.000origination rows/unique loans;4.510.559performance rows,50.000loans có performance.
- Duplicate origination/monthly keys,orphans,no-performance loans,gap loans đều0 trong snapshot này. Observed months per loan min1,max171;47.349loans có ít nhất13contiguous observed months.
- Reporting coverage2012-01→2026-03. Unknown-status rows0,REO1.073,D3+18.057loan-month rows. D3+ stock rows không là incident defaults.
- Populated loss374source rows; không là374resolved loans hoặc qualified LGD observations.
- Canonical missing:classicFICO0,DTI17.400,LTV3,CLTV3,VantageScore50.000,property valuation method50.000. Raw blanks của các numeric/sentinel fields này bằng0; missing phát sinh từ token-specific contract, không được thay bằng0.

Không globally replace9/99/999. Delinquency codes là categories;XX giữUNKNOWN,RA giữREO,numeric03–99 giữD3PLUS. Terminal codes phân loại riêng khỏi delinquency state. Data absence giữ unavailable; không có drift/calibration alarm khi chưa validated model/reference population/mature-label protocol.

## Receipts

- Independent `artifacts/private/panel-quality-acceptance-6f1ed5abead2/receipt.json`:18technical/64blank/6sentinel checks và whole monthly state/terminal mapping PASS; source/case/method hashes lưu; retail holdout ledger unchanged.
- `artifacts/private/panel-quality-acceptance-tests.xml`: **49tests PASS**, source/canonical/monitoring/frozen-service boundaries,keys,unknown/sentinels/gaps và immutable scopes.
- Browser `artifacts/private/panel-quality-browser-acceptance-861f7799b297/receipt.json`: **4segment scopes PASS**, exact integrity/availability/action readouts và private export. Quality không bị segment filter làm đổi population; mobile/no page errors/ledger unchanged. Desktop quality readout đã visual-review.

## Provenance finding — không đồng nghĩa publisher authentication

Raw archive receipt `vendor/credit_risk_strategy_lab/data/private/raw/35c41582157804e3f632d68140246fcc6eb0973590ba0cf9a0f03600bf8499f9.receipt.json` ghi rõ:

`release_confirmation: user_supplied; not authenticated by file hash registry`

Research-use confirmation nằm trong receipt khai báo; public_release_approved=false. Source hash chứng minh byte consistency/lineage, không tự chứng minh publisher release hoặc publication time. Những acceptance numerical trước đây với cách gọi “official sample2012” phải đọc cùng caveat này: kết quả được xác nhận trên supplied/pinned corpus, không phải publisher-authentication certificate.

P2.01 Source Explorer cần thể hiện rõ provenance này; chưa được nghiệm thu từ audit P2.02. Received/extraction/rebuild times không được dùng làm publication dates. Source identity/rights/PIT/model qualification vẫn là các scope riêng.

## Kết luận

Đủ evidence cho toàn bộ yêu cầu hiện tại P2.02 trên supplied corpus. Cross-vintage quality/new-source reconciliation là bước tiếp theo; P2.01/P2.08/R2/R3 và goal100% còn mở. Không fit/rescore hoặc truy cập retail final predictors.
