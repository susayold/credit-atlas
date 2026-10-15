# P2.06 — nghiệm thu Cure & Redefault

Ngày12/10/2026. Đối chiếu yêu cầu P2.06 trong plan, trên case `d01-a24484b21a21`, official Freddie annual sample2012. Scope là event ledger, observation support và source-based timeline; không là survival model, cure probability hoặc treatment effectiveness.

## Yêu cầu và kết quả

| Yêu cầu gốc | Kiểm chứng | Kết quả |
|---|---|---|
|D3 episodes và CURRENT nonterminal consecutive months|Dựng event bằng SQL set-based: continuity blocks, D3 anchors, current-run streaks, first sustained confirmation và redefault relation; không gọi engine episode generator|Toàn bộ4.902event rows khớp,0 differences|
|Gap và follow-up windows|Dense grid cho từng tháng t+1…t+6/t+12, so source month/state/terminal và last observed period|9.804event-horizon checks,82aggregate groups khớp|
|Episode events|Browser so toàn event-type counts theo segment với audited follow-up anchors|4segment scopes khớp|
|Follow-up support|Browser so từng event/status/horizon/events/distinct-loans row|8segment×horizon scopes PASS|
|Loan timeline|Đối chiếu nguồn event/month/state/terminal cho hồ sơ đại diện bốn loại event; browser so từng event/date|4event types PASS|
|Gap/unknown phá linkage|Boundary tests; SQL blocks tách gaps/unknown, không reset first-ever D3 history|PASS|
|Terminal CURRENT không thành cure|Test CURRENT tháng3 cùng terminal; SQL loại terminal CURRENT khỏi current streak/confirmation|PASS|
|Thiếu follow-up không thành no-event|Phân biệt source end,gap,unknown,terminal exit/at confirmation; không impute missing thành complete|PASS|
|Confirmation không backdate|Confirmed cure nằm ở CURRENT nonterminal tháng thứ3; timeline giữ confirmation month|PASS|

## Evidence hiện có

- Independent audit: `artifacts/private/cure-acceptance-ac5b999767fe/receipt.json`; saved follow-up projection cùng folder. Kiểm tra SHA của dim_loan,fact_loan_month,episodes,case receipt và methods.
- Tests: `artifacts/private/cure-acceptance-tests-20261012.xml`, **26 PASS**. Bao gồm upstream portfolio semantics, follow-up interruption/anchor/grain, scoped export và frozen-service integrity/filter handling.
- Browser: `artifacts/private/cure-browser-acceptance-f3834b743ccf/receipt.json`, **8follow-up scopes +4timeline event types +4segment exports PASS**; mobile,invalid-token400,cross-origin403; không page errors; frozen retail holdout ledger không đổi.
- Export thêm8scope checks trong independent audit:4segments×all/absent1990 transition year; chart range2020-01/02 và horizon6 không lọc episode6/12follow-up. Chỉ segment áp vào report này.
- Desktop follow-up và timeline screenshots đã visual-review. Các output chỉ ở private workspace. Không đọc retail final predictors, không fit model và không thay source files.

## Kết quả và cách đọc

First observed D3, one-month cure, sustained-cure confirmation và redefault after sustained cure là bốn event types riêng. One-month cure không tự là sustained cure; redefault không tự là first-ever D3. Event counts có thể lặp trên cùng loan; distinct loans không cộng qua event/status groups.

Complete nonterminal follow-up chỉ xác nhận có đủ tháng liên tiếp với trạng thái known/nonterminal, **không có nghĩa không redefault**. Terminal events/source-end thiếu follow-up giữ status riêng. Không dùng complete support để tính cure/redefault probability chưa có risk-set/estimand protocol.

## Các lượt audit trước

Lượt `cure-acceptance-3ff0350bfb4d` đã dừng để sửa chi phí truy vấn: mang74canonical columns qua nhiều window tables dù episode logic chỉ cần4columns. Lượt mới vẫn đọc toàn4.510.559loan-months, chỉ project loan_id/period/state/terminal; không giảm rows/horizon/phép kiểm tra.

Lượt `cure-acceptance-8da309ee6f24` đã khớp toàn4.902events nhưng SQL follow-up bị ambiguous loan_id do join. Đã sửa alias trong script audit, không đổi engine/service để khớp audit. Chỉ receipt PASS cuối được dùng để nghiệm thu; stopped/failed outputs vẫn giữ.

## Kết luận và phần tiếp theo

Đủ evidence cho **toàn bộ yêu cầu hiện tại của P2.06**. Bước phát triển tiếp trong plan—time-to-cure/redefault trên nhiều cohorts với censoring protocol—vẫn mở. Không đóng P2.08/R2/R3 hoặc gọi research workflow này là collections strategy có hiệu quả causal.

Chỉ đánh dấu P2.06 `full_completion_proven=true`; các capability khác giữ trạng thái riêng, goal100% chưa hoàn thành.

## Bổ sung denominator audit — 15/10/2026

Tách rõ occurrence grain và unique-loan support: 4.902 event rows thuộc 1.713 loans; repeated one-month cure/redefault rows được giữ, không diễn giải thành borrowers độc lập. Follow-up status phân hoạch chính xác toàn bộ event rows theo event type × segment × 6/12m horizon trong 24/24 checks. `distinct_loans` của status groups không cộng thành unique loans vì cùng loan có event lặp rơi vào nhiều statuses. Tái tạo ở [denominator audit](../artifacts/private/d01-episode-denominators-a3a3093f04b8/audit.json) và [method note](D01_EPISODE_DENOMINATORS_VI.md). Không ước lượng cure/redefault probability từ các support counts; spell-level risk set và censoring vẫn cần trước survival model.

UI regression 15/10 xác nhận event table theo Toàn sample/Relief/non-Relief hiển thị unique-loan support đúng và giữ disclosure về mẫu số; [receipt 25 checks PASS](../artifacts/private/browser-qa-f35adbcaeddf/receipt.json).
