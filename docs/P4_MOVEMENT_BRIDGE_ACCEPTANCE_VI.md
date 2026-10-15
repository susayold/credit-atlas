# P4.06 — nghiệm thu observation movement bridge

Checkpoint 15/10/2026. Phạm vi trong plan: same-source namespace position keys, native currency opening/closing amounts và buckets; ordered bridge, transitions và private exact export. Không suy ra payoff/default từ record biến mất, không coi currency migration là FX P&L, luôn giữ residual.

## Nguồn thực

Bridge `exposure-movement-dbd1ecad612e` ghép hai source-observation imports theo exact position IDs trong Freddie 2012 sample namespace, 2026-02 → 2026-03. Opening 9.804 records; closing 9.698; 9.698 matched same-currency, 106 opening-only, không closing-only hoặc currency migration trong cặp này.

USD opening 928.246.113,34 → closing 915.208.989,12; continuing amount change −13.037.124,22; removed amount 0, added amount 0, residual 0. Opening-only records có zero reported amount trong opening snapshot. Điều này không chứng minh chúng payoff/default hoặc có cash payment bằng zero.

`exposure-movement-audit-0228d51fcb29/audit-complete.json`: PASS 500 independent Fraction checks từ raw CSV: identity partition, record counts, mọi currency/group opening/removed/continuing/transfer/added/closing/residual, complete group keys và transition counts/closing transferred amounts. Source/import/report/method graph được verify trước audit và giữ nguyên sau audit.

## Nhánh không xuất hiện trong cặp thực

`movement-boundary-audit-012d14f1a641/receipt.json`: PASS 100 deterministic synthetic pairs, seed 40615, **26.668 exact checks**. Bao gồm opening-only/closing-only, zero và sub-cent amounts, same-currency changes, USD/VND/EUR migrations và region/segment/source-state changes. Pool/representation identity giữ ổn định; separate tests kiểm trường hợp thay identity bị từ chối.

Independent rational arithmetic xác nhận amount change ghi ở opening bucket trước khi transfer closing amount sang bucket mới. Currency migration được loại khỏi same-currency change và ghi paired removal/addition theo native currencies. Không có synthetic case nào được gọi là actual borrower disposition hoặc institutional FX/cashflow attribution.

## API, UI và private export

`movement-scope-browser-557afb22290b/receipt.json`: PASS tám scopes all/USD × bốn dimensions region/segment/source_state/representation. Actual API projection giữ đúng currency totals, group/transition subsets và whole-pair identity-count scope. Mỗi download khớp expected report và có SHA.

UI giữ captions không suy diễn payoff/default hoặc FX P&L; group row counts đúng scope. URL reload/mobile không overflow; source outage xóa stale export và source recovery khôi phục link. Wrong closing import, absent currency, unknown dimension và raw PD query bị từ chối. Retail/Bankruptcy holdout ledgers giữ nguyên SHA.

Đã xem trực tiếp desktop/mobile screenshots của bản cuối. Mobile dùng table scroll trong panel; ảnh không chứng minh attribution theo actual payment events.

`p4-movement-current-tests.xml`: 15 tests PASS cho bridge precision/zero/reclassification/migration, scope/date/identity guards, forged reports/source mutation, cache byte checks kể cả giữ nguyên mtime, HTTP private export/filter boundaries và independent audit fault detection.

## Kết luận phạm vi

P4.06 đáp ứng current source-observation bridge workflow. Missing record chưa có disposition reason; exact position IDs không chứng nhận borrower/group linkage; continuing balance change chưa tách principal/interest/charge-off/corrections. Không EL movement, FX conversion hoặc cross-currency global total. Các phần này vẫn giữ trong next steps; nghiệm thu không làm chúng trở thành actuals.
