# P3.06 — nghiệm thu financial memo và issuer filing timeline

Checkpoint 15/10/2026. Phạm vi là financial memo theo verified SEC issuer/filing, chín narrative sections, immutable evidence digest, issuer-scoped list, revision history và private JSON; plan còn bao gồm issuer filing metadata timeline. Đây chưa phải complete borrower credit decision với actual debt/covenant inputs.

## Memo capture và lịch sử

`maturity-memo-capture-qa-53be504b0819/receipt.json` PASS tám issuer/family captures trong kho QA riêng. Selected filing, trend, interest coverage và maturity evidence đúng scope; trend/coverage cutoff được neo vào ngày filing đã chọn. Narrative revision không thay capture; evidence digest được tính từ canonical JSON. Các qualification flags vẫn false.

`corporate-memo-http-audit-19a0e10beed0/receipt.json` PASS real handler và browser trên hai issuers AAPL/GM, kho memo QA riêng:

- UI tạo/sửa, chín section controls, issuer list, history, private full JSON, reload và mobile.
- Bốn revisions cho mỗi memo, capture/digest không đổi; stale revision bị từ chối 409 và không tăng history.
- Không nhận source scope mới hoặc injected capture trong update; payload vượt giới hạn bị chặn 413. Payload nhỏ có injected capture bị chặn 400. Cross-origin bị chặn 403; unknown report filters bị chặn 400.
- Khi provider report giả lập outage, list/export memo cũ vẫn đọc được, revise narrative vẫn giữ capture; tạo memo mới bị chặn. Source outage không ghi đè bằng chứng cũ.
- Main memo DB và cả Retail/Bankruptcy holdout ledgers giữ nguyên SHA. QA narratives/status là synthetic và self-declared, không phải phê duyệt của analyst có xác thực.

Browser receipt đi kèm: `corporate-memo-qa-cf9d8c95db21/receipt.json`, bốn nhóm PASS. Đã xem trực tiếp memo desktop và mobile editor. Lần audit HTTP đầu dừng do expect nhầm status của full injected capture quá lớn; đã tách kiểm 413 size boundary và 400 invalid-field boundary, không thay đổi production để làm test pass.

## Issuer filing timeline

`sec-filing-timeline-audit-6c16a2df83a6/receipt.json` đối chiếu trực tiếp raw submissions/history với API hiện tại trên source `sec-source-13cf03606e0c` và view `sec-view-b92d9914f1dc`:

| Issuer | Tất cả unique filing metadata | Timeline selected forms |
|---|---:|---:|
| AAPL | 2.265 | 368 |
| MSFT | 4.525 | 423 |
| Ford | 4.446 | 929 |
| GM | 2.138 | 427 |
| Tổng | 13.374 | 2.147 |

PASS 2.147 row metadata checks qua 48 API calls: toàn bộ pages không thiếu/trùng accession, date/form/report date/acceptance time/primary document, raw item/description, occurrences/source ordinals và index/document URLs. Empty primary document giữ null link. Summary ổn định giữa pages; form/item counts và amendments khớp raw population. Mỗi issuer có bảy filter scopes: all/current/annual/quarterly và current items 1.01/2.02/2.03.

`sec-events-qa-c4807e22e56d/receipt.json` PASS tám nhóm browser/API trên snapshot trước vẫn được hỗ trợ: bốn issuer counts trong window 2020–11/10/2026, pagination/item filters, private download, reload/mobile, outage/recovery và holdout guard. Đã xem ảnh desktop/mobile. Snapshot UI này khác snapshot của whole-corpus audit; cả hai được ghi rõ, không gọi là cùng source capture.

Filing metadata không phải full-text legal/default event evidence. Item counts có overlap; amendments là accessions riêng; không suy ra breach/borrowing amount hoặc không có credit event từ missing item code. Không claim live feed hay intraday/PIT availability.

## Tests và kết luận phạm vi

`corporate-memo-acceptance-tests.xml`: 31 tests PASS cho memo và HTTP boundaries. `sec-filing-timeline-acceptance-tests.xml`: 19 tests PASS cho timeline/source/filter contracts.

Các bằng chứng này đóng P3.06 theo workflow financial memo/metadata timeline trong plan. Reviewed/owner vẫn tự khai báo; không issuer PD, DSCR, covenant compliance hay credit approval. Full-text issuer events, effective debt/covenant actuals và complete borrower recommendation vẫn là đầu vào phát triển tiếp theo, giữ nguyên trong sổ yêu cầu.
