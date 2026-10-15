# P1.04 — policy đọc saved scores: checkpoint sửa verifier

Đã phát hiện đường phục vụ policy cũ gọi deep freeze/assessment verification, trong đó tính lại development predictions để kiểm codec parity. Không mở final-test predictors, nhưng không phù hợp yêu cầu app chỉ đọc saved artifacts.

## Thay đổi đã thực hiện

`retail_policy_saved.py` kiểm tra freeze graph bằng byte hashes/method versions, saved model/encoder/settings bindings, validation IDs/labels và persisted score snapshot. Policy arithmetic được replay từ saved probabilities; không inference/refit model. Không sửa các module nguồn đã pin: retail, features, assessment, comparison, freeze hoặc holdout.

`RetailPolicyViews` dùng verifier/writer mới cho catalog/report/preview/save. Chi phí và threshold rules vẫn dùng cùng calculator Fraction đã có. Writer mới giữ artifact schema và ghi riêng execution-method hash/no-inference flag. Storage mặc định vẫn private workspace; QA có thể dùng thư mục policy riêng bên trong artifacts/private. Bản xuất API không trả đường dẫn storage.

## Kiểm tra

- `artifacts/private/retail-policy-saved-serving-tests.xml`: 20 tests PASS về ties/empty buckets/missing capacity, strict cost schema, source integrity, semantic replay, immutable version, preview và HTTP contracts. Fixtures chỉ dùng synthetic scores.
- `artifacts/private/retail-policy-audit-8f505ca2f0ed.json`: 184 exact Fraction checks PASS trên policy thật, 4.499 validation clients/995 events; sáu cases gồm ba constant-action benchmarks và ba threshold cases. Holdout ledger không đổi.
- `artifacts/private/policy-saved-no-inference-3b3a84e13d8c/receipt.json`: report/preview/save/reopen/catalog trên policy thật PASS trong storage QA riêng, đồng thời block inference/refit/deep-verifier entry points. Original policy và holdout ledger không đổi.
- `artifacts/private/retail-policy-browser-qa-8f799d39c04b/receipt.json`: 9 nhóm PASS, gồm capacity overflow, dirty-preview/save, immutable saved version, scoped export, reload, reversed thresholds, invalid explicit policy và mobile. QA policies nằm trong thư mục riêng, không thêm vào catalog chính.

Capacity600 của illustrative lower-threshold case cần2.277 review clients, overflow1.677; không reassignment hoặc bỏ khách hàng. Đổi capacity3000 chỉ đổi breach flag, không chứng minh staffing thật. Expected/retrospective costs là declared units, không gọi cash loss, optimal price hoặc causal savings.

## Chưa nghiệm thu toàn màn

`retail_subgroups.source` vẫn import legacy `retail_policy.verify`; catalog subgroup trong cùng màn policy có thể kích hoạt deep assessment parity/inference. Browser PASS về UI/cost không chứng minh toàn màn không inference. Probe no-inference ở trên chỉ chứng minh đường **Policy APIs**, không bao phủ subgroup route.

Tại checkpoint này, cần chuyển subgroup serving verification sang saved-artifact validation mà vẫn giữ source/demographic/score/group reconciliation; **P1.04 chưa được nâng full_completion_proven chỉ bằng Policy API probe**. Việc sửa và audit toàn workflow sau đó được ghi tại [P1_POLICY_SUBGROUP_ACCEPTANCE_VI.md](P1_POLICY_SUBGROUP_ACCEPTANCE_VI.md). Các chi phí thật, daily inflow, reject/treatment outcomes và production qualification vẫn chưa có. Mục tiêu toàn dự án chưa đạt100%.
