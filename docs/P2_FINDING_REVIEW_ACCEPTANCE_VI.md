# P2.10 — private evidence & review

Finding lưu current run/view/filter context, reviewer text và evidence references; thay đổi bằng revision với history append-only. Có thể draft → reviewed → archived → reopen draft. **Reviewed là local research status, không có authenticated reviewer identity, roles hoặc bank credit approval.** Memo không sửa raw/canonical data, frozen case hoặc model gates.

## Phần bổ sung

Giao diện cố định finding context ngay khi mở form, thay vì lấy lại current run/view/filters khi bấm Save. Sửa finding giữ context từ record gốc. Bản xuất riêng ở `/api/finding-report?run=...&id=...&revision=...` lấy đúng reviewer text và filters của revision đã chọn; bỏ revision sẽ chọn bản mới nhất. History trong bản xuất dừng ở revision được chọn, không đổi nội dung các revision trước đó.

Bản xuất có finding, history, evidence refs, aggregate report, case lineage và view-specific diagnostics cho Sources/Loss hoặc pseudonymous loan timeline khi record có loan key. Aggregate tables giữ filter applicability riêng: quality/loss whole-source không bị ngầm đổi thành segment/date scope.

Evidence được resolve từ **current verified immutable case**, với filters của revision, không được mô tả là numerical snapshot đã lưu lúc tạo finding. Evidence refs là labels người viết chọn, không tự chứng minh conclusion. Báo cáo ghi `authenticated_reviewer_identity:false`, `bank_credit_approval:false`, `public_release_approved:false`.

## Kiểm tra

- 41 tests trong `private evidence omitted from public release` PASS: persistence/reopen, concurrent stale revision, atomic history, invalid input, foreign case/loan scope, exact historical exports, frozen evidence guards.
- Browser dùng server loopback và database QA riêng trên D:, với frozen mortgage case thật. Tạo finding từ cả 9 views; kiểm filters, reviewer text và status revisions; tải 4 historical versions; stale editor bị409; modal-open context giữ nguyên khi application state đổi; HTML trong memo không thực thi.
- Export riêng Sources/Loss giữ provenance/diagnostics; lifecycle finding có pseudonymous timeline, không raw loan ID. Invalid revision/missing version/cross-origin bị từ chối.
- Kiểm hash 44 source/output file entries sau QA, database findings thật và retail holdout ledger không đổi. Mobile 390px không overflow.

Receipt browser cuối cùng và các regression P2.01–P2.07/P2.09 được pin trong sổ `COMPLETION_REQUIREMENTS_50.json`, cùng method/app/server hashes. Các lần QA chưa thành công được giữ, không dùng để nghiệm thu. Server QA đôi khi ghi ConnectionAbortedError khi navigation hủy request đang tải; không xem một request bị client hủy là receipt PASS hoặc source-integrity failure. PASS chỉ được ghi sau toàn bộ assertions thành công.

## Phạm vi còn thiếu

Identity/roles, authenticated sign-off và formal team review policy vẫn là bước phát triển tiếp theo, chưa triển khai. Không nâng checkpoint “Một phần” thành production workflow chỉ vì chức năng local finding đã được kiểm tra. Mục tiêu toàn dự án 100% chưa đạt.
