# P1.10 — Model evidence & governance dossier

Retail → Model & evidence có reporting package riêng nối source contract, split support, train-only feature preparation, development selection, freeze và saved final evaluation. Endpoint `/api/retail-dossier[-report]?view_id=...` chỉ nhận verified suite-view scope, đọc pinned aggregate/metadata JSON; không inference/refit/rescore hoặc parse private holdout score rows.

## Nội dung và source binding

Dossier chứa source/history/month/target contract; bốn partition support; selected boosting/raw và development rubric; cả sáu validation metric variants; paired validation uncertainty; saved final-test metrics; limitations và evidence hashes. Không trả raw client IDs, reference rows, model coefficients/trees hoặc filesystem path máy.

Audit trail gồm sáu artifact IDs và recorded times: canonical case, train-only features, development assessment, paired comparison, freeze, saved final evaluation. Quyết định selection trước freeze và freeze trước final access/evaluation được đối chiếu từ persisted metadata. Holdout freeze receipt hash, feature/assessment/comparison bindings và final metrics phải khớp suite projection. Recorded time không tự là publisher availability hay authenticated organizational approval.

Research intended use là historical Taiwan booked-card behavioral benchmark với source next-month payment target. Package không gọi model là Vietnam PD, approval-time underwriting, PD12/regulatory default hoặc bank-approved policy.

## Governance được ghi đúng tình trạng

Review owner chưa cung cấp; authenticated sign-off chưa có; intended-use production approval/OOT/production qualification đều false; final-test confidence intervals chưa có. Rubric được đặt sau development inspection nên validation decision là exploratory. Raw labels/cohort tồn tại trước freeze ở cấp tổ chức; pipeline reserved holdout không chứng minh dữ liệu chưa từng được nhìn thấy ở cấp tổ chức.

Các stage timestamps và flags là local research evidence, không chứng nhận danh tính hoặc quyền phê duyệt ngân hàng. Không invent owner, expiry, monitoring cohorts hoặc sign-off chỉ để đóng trạng thái.

## Verification

- `private evidence omitted from public release`:17 tests PASS. Metadata-only fixtures không có raw predictor/score matrices; kiểm real stage IDs, unsupported scopes, changed metrics, production-claim rejection, final access before freeze rejection và source-contract invariants.
- `private evidence omitted from public release`: source/split/selection/metrics/uncertainty parity PASS; sáu audit trail rows và private JSON download khớp API; governance unqualified flags giữ nguyên; reload/mobile/cross-origin/query/outage-retry PASS.
- Browser chạy dưới inference/refit/deep-verifier tripwires: forbidden_calls0; retail holdout ledger không đổi. App đọc saved artifacts khi mở màn.

Nghiệm thu current research dossier không nâng thành full production governance. Model-review ownership, monitoring protocol, intended-use approval, temporal/deployment cohorts và authenticated organizational sign-off vẫn là next steps. Mục tiêu100% toàn dự án chưa hoàn thành.
