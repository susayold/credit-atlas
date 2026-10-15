# P2.03 — nghiệm thu Portfolio & Cohorts

Checkpoint trên case `d01-a24484b21a21`, official annual sample2012. Đối chiếu yêu cầu về observed states/UPB, segment/month filters, charts/profile/export và count-versus-balance semantics.

## Yêu cầu và evidence

| Yêu cầu gốc | Kiểm chứng | Kết quả |
|---|---|---|
|Observed loan-month states/UPB|Python streaming aggregates từ canonical, không dùng portfolio_monthly.sql để dựng expected values|Toàn4.510.559loan-months;7.182monthly field checks khớp|
|Segment và reporting-month filters|Whole-source/segment monthly projections; empty range; profile scope giữ riêng|16export scopes khớp|
|Monthly charts|Browser kiểm tra actual SVG coordinates từ source values theo basis/range|360chart points khớp|
|Profile|Python bucket definitions đối chiếu từng dimension/segment/bucket/count/openingUPB/share|13dimensions/102groups/50.000source loans khớp|
|Selected-scope aggregate export|Browser download so đúng monthly rows/filter context|6UI scopes PASS|
|Zero UPB giữ riêng|Actual source zero/missing counters và dedicated synthetic nonterminal-zero/NULL/terminal cases|PASS;zero không thành missing/terminal|
|Count và balance denominator khác|Count D3/usable loan count; UPB D3/usable known UPB; zero balance denominator giữ null|PASS|
|Không cộng loan-months thành unique loans|Source grain/count được ghi rõ; monthly stocks không được gọi originated volume|PASS|

## Sửa cách hiển thị metric basis

Bảng Monthly stock ledger trước đây luôn dùng count share và tên chung D3 share, trong khi ở UPB mode headline/chart dùng balance share. Đã cho last column theo selected basis và ghi rõ **D3 count share / D3 UPB share**. Tại March2026, count share khoảng0,19% và UPB share khoảng0,25%; UPB mode hiện nhất quán headline/chart/table.

Không thay frozen data hoặc công thức nguồn. Export vẫn giữ cả hai fields cùng basis/filter metadata. Count, current-UPB và origination opening-principal mix là ba scopes khác nhau; profile shares ởall view vẫn có denominator riêng từng segment, không gộp hai100% thành overall share.

## Zero/missing boundary và actual support

Sample thực không có active zero-UPB observations. Vì vậy boundary tests kiểm tra riêng4rows: CURRENT balance100, D3 balance0, D3 balanceNULL, terminal CURRENT balance0. Kết quả active3,terminal1,missing balance1,D3count2; count share2/3 nhưng balance share0. Balance denominator bằng0 hoặc toànmissing giữ unavailable.

Origination profile coi original principal<=0 là unsupported theo existing contract; đây là quy tắc khác với known zero current balance trong monthly stock. Sample hiện tại có original principal support đầy đủ; không dùng validation này để tuyên bố phù hợp mọi vintage tương lai.

## Receipts

- Independent `private evidence omitted from public release`: **513monthly scope rows /7.182checks**,13dimensions/102profile groups,16exports PASS. Source/case/method hashes lưu trong receipt; retail holdout ledger unchanged.
- `private evidence omitted from public release`: **27tests PASS** gồm zero/NULL/terminal/zero-denominator boundaries,profile/export integrity,portfolio và frozen-serving scopes.
- Browser `private evidence omitted from public release`: **6scopes /408profile bucket checks /360chart points PASS**, header/value theo basis,empty range/mobile/reload và scoped downloads. Desktop UPB và empty mobile đã visual-review; không page errors; ledger unchanged.

Một lần kiểm tra header bằng accessibility role không resolve được; test cuối kiểm tra trực tiếp nội dung th cuối cùng và toàn bộ values, không bỏ kiểm tra label/basis.

## Hồi quy frontend liên quan

Sau sửa ledger basis, đã chạy lại:

- P2.04: `lifecycle-browser-acceptance-d26ebafc7b2b/receipt.json`,10cases/clear/race/outage PASS; source/static privacy audit mới `lifecycle-acceptance-326d86ee5e4e/receipt.json` PASS.
- P2.05: `transition-browser-acceptance-e67e015a9055/receipt.json`,6scopes PASS.
- P2.06: `cure-browser-acceptance-d2f94359d516/receipt.json`,8follow-up scopes/4timeline types PASS.
- P2.07: `competing-browser-acceptance-3117cc8058a2/receipt.json`,12scopes PASS.

## Kết luận

Đủ evidence cho **toàn bộ yêu cầu hiện tại P2.03**. Nhiều origination vintages và standardized composition comparisons là bước phát triển tiếp theo; P2.08/R2/R3 và goal100% còn mở. Không fit/refit hoặc truy cập retail final predictors. Existing JSON numeric representation không là accounting ledger; source Decimal sums được đối soát trước conversion.
