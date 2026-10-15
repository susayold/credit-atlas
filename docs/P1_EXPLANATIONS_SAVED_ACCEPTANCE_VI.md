# P1.07 — giải thích toàn bộ validation cohort từ audited saved artifacts

App đọc explanation đã lưu cho đủ **4.499 validation clients**, thay vì chạy lại model/coalitions khi mở màn. Source/model/reference/explanation artifacts giữ nguyên. Registry chỉ nhận đúng hai studies đã có independent audit certificate; studies chưa có audit không được tự gọi qualified hoặc fallback sang study khác.

## Bằng chứng numerical và lineage

Independent audit gốc của complete cohort có45.021 checks trên4.499 records (`retail-cohort-explanations-audit-a441ed7a5c48.json`); audit gốc của parent12 examples có375 checks (`retail-explanations-audit-d4c7f6227d3d.json`). Audit certificates được pin bằng exact SHA256 và bind đúng study-complete receipt; receipt pin toàn bộ inputs/outputs. Audit-method files cũng phải giữ đúng hashes. Đây là bằng chứng đã chạy trước đó trên đúng bytes hiện tại, không phải fresh tree-inference audit trong đợt này.

Verifier mới kiểm tra certificate/source/output hashes, frozen model/source bindings, saved probabilities, ordered score ranks, study-scoped tokens, training-reference scope và12-example parity. Tự tính lại contributions của12 cases từ16 saved coalition values theo24 orders; đối chiếu reference + signed group contributions với probability của cả4.499 clients, residual trong tolerance1e−12. Global signed/absolute distributions, minima/maxima và positive/negative/zero counts khớp saved rows.

Four feature groups là credit limit, repayment status, bill history và payment history. Reference32 training rows và16-coalition marginal substitution đã được audit gốc; không dùng final holdout làm reference. Không đọc lại final-test predictors hoặc private holdout scores. Không fit/rescore actual model.

Fingerprint serving adapter cũ được hỗ trợ chính xác trong method provenance; numerical engine methods vẫn phải khớp. Certificate và audit-method hashes tiếp tục nằm trong cached guard, không chỉ kiểm tra lúc load đầu tiên. Không sửa receipt/model artifacts gốc.

## Runtime/API/UI

- `explanations-saved-probe-59f8ebc3bf4b/receipt.json`: chặn inference/deep replay entry points, forbidden calls0;12 parent examples;90 API pages chứa đủ4.499 unique tokens; exact-token search/client report PASS; holdout ledger không đổi.
- `explanations-saved-view-tests.xml`:4 tests PASS về private HTTP/scope/pagination/cached corruption trên synthetic serving fixtures và real certificate fail-closed checks. Synthetic fixtures không được dùng làm certificate cho production/source data.
- `retail-cohort-browser-qa-fea76087b373/receipt.json`:8 nhóm PASS về toàncohort, trang sau/rank ngoài12 examples, signed local export, URL/reload, lowest-score exact search, unknown-token empty/no fallback, desktop/mobile và ledger.

Browser receipt được sửa nhãn metadata legacy “full replay” thành “saved audited consistency”, lưu original receipt digest cùng lý do. Không mô tả một bước đọc saved artifacts là model/coalition inference rerun. App/export hiển thị contribution tương đối finite reference đã chọn; dữ liệu raw IDs và reference rows không được trả cho client.

## Giới hạn còn mở

Contributions giải thích output của fixed historical model, không chứng minh nguyên nhân, tác động của can thiệp, fairness hoặc regulatory adverse-action reasons. Chưa có intended-use approval để scoring hồ sơ mới, reference sensitivity trên population triển khai, temporal/Vietnam transportability hoặc authenticated sign-off. Mục tiêu100% toàn dự án chưa đạt.
