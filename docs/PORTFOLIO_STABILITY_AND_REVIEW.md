# P4 — multi-seed diagnostics và finance/review package

## 1. Stability diagnostics

Receipt `exposure-convergence-0741003b87f4` nối đúng tail study
`exposure-tail-10a079f18dc9` và March source `exposure-import-57b88e00bedb`.
Seeds: 20261009, 20261010, 20261011. Draw counts: 1.024, 4.096, 6.144.
Mỗi replication chạy toàn bộ 4 sensitivity cases, 9.602 eligible positions,
native USD và levels 97,5%/99%. Không fit/calibrate model, không đọc/refit
reserved model holdouts.

Mỗi level báo mean, sample SD, min/max giữa các seeds của mean loss, VaR và
ES. So sánh last-two-level means dùng cùng seeds. Các levels có tương quan
vì stream seeds được giữ nguyên; không coi 9 runs là 9 independent replicas.
Seed range chưa phải confidence interval; chỉ 3 seeds chưa chứng nhận hội tụ.

| Case | ES99% seed-mean change: 4096→6144 | VaR99% seed-mean change |
|---|---:|---:|
| Independent | +0,2711% | +0,1403% |
| rho 0,15 | +0,4901% | −0,4826% |
| rho 0,35 | +0,3925% | −0,6336% |
| rho 0,35 + coupled LGD | +0,3968% | −0,6387% |

Tail mass 99% tăng từ 40,96 lên 61,44 draws **mỗi seed**. Chênh lệch nhỏ ở
hai mức này không loại trừ instability ở seed khác hoặc mức quantile cao hơn.
Không dùng một threshold tùy ý để biến diagnostic thành PASS qualification.

Input exact schema: schema_version,tail_id,seeds,draw_counts,visibility,
public_release_approved. 2–8 unique integer seeds; 2–4 increasing unique draw
counts; mỗi run vẫn tuân thủ 300-million work bound của frozen tail engine;
aggregate ≤2 billion position draws. Build guard source/method trước/sau
tính toán. Verify chạy lại mọi replication và đối chiếu full report.
Immutable receipt pin tail source/assumptions/payload/receipt, source lineage,
runtime versions, tail and convergence code. Current views full replay lần
đầu, rồi hash-check all payloads/inputs/receipts mỗi cached read.

Independent diagnostic audit `exposure-convergence-audit-edd2670b9753`
PASS **312 checks**, tính lại mean/sample SD/range/changes từ saved run
summaries bằng math/Fraction; kiểm seed/level coverage và assumptions.
Audit này kiểm aggregate diagnostics, không thay full simulation replay.

## 2. Review package

Một package pin source_import_id, currency, typed evidence refs và verified
aggregate snapshots. Supported refs: scenario, ECL, tail. Source inventory
được đính kèm luôn. Ref từ source snapshot khác bị từ chối. Không raw IDs,
không source/model overrides, không câu kết luận vượt qualified scope.

Review fields: title, rationale, owner, expires_on, draft/reviewed/archived,
assumptions_acknowledged và evidence_refs. Reviewed chỉ là research annotation;
không tự tạo accounting/capital approval hoặc calibration. Reviewed yêu cầu
acknowledgement và chưa expired theo UTC date. Owner là text khai báo;
local app chưa có authenticated identities hay four-eyes sign-off.

SQLite packages/history lưu revision append-only qua BEGIN IMMEDIATE.
Update phải gửi current revision; stale edit trả HTTP409. Save re-verifies
evidence trước và trong transaction; source bị sửa thì rollback. Export
selected historical revision phải khớp verified evidence hiện tại. Nếu nguồn
hoặc private artifact đổi, catalog đánh evidence_current=false và export bị
chặn; record/history vẫn giữ để điều tra. Expired package được ghi rõ,
không tự delete hoặc auto-renew. Qualification flags luôn false.

Input plan `data/private/portfolio-review-plan-20261009.json` là automated
**draft**, owner ghi analyst assignment pending; không giả nhận human review.
Default storage: `artifacts/private/reviews-portfolio.sqlite3`, theo source
snapshot; browser QA dùng database riêng để không tạo reviewed QA notes trong
production workspace.

## 3. API và giao diện

- `/api/exposure-convergence-studies`: source_import_id.
- `/api/exposure-convergence` và `...-report`: convergence_id,
  source_import_id, optional currency.
- GET `/api/portfolio-reviews`: source_import_id, summaries/current/expiry.
- GET `/api/portfolio-review` và `...-report`: source_import_id,id,
  optional positive revision. No-store/private download.
- POST `/api/portfolio-reviews`: exact typed review input; cùng Origin/Host
  loopback, JSON≤64KB và X-CreditAtlas-Client:local.

Exposure page có stability table/export và review editor. Có thể tạo draft,
đọc/sửa latest package, lưu revision mới và xuất đúng revision. Default
evidence refs là latest verified scenario/ECL/tail cho selected source;
sửa package giữ bound refs/currency ban đầu. Không cho browser đổi rho/PD
qua annotation. Historical revision có API/export; UI chưa có history picker.

## 4. Commands và verification

    .\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_convergence.py --assumptions data/private/exposure-convergence-plan-20261009.json
    .\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_convergence.py --verify exposure-convergence-0741003b87f4
    .\.venv\Scripts\python.exe -X utf8 scripts/audit_exposure_convergence.py --convergence-id exposure-convergence-0741003b87f4
    .\.venv\Scripts\python.exe -X utf8 scripts/build_portfolio_review.py --input data/private/portfolio-review-plan-20261009.json --output artifacts/private/portfolio-review-draft-20261009.json
    .\.venv\Scripts\python.exe -X utf8 scripts/browser_exposure_qa.py
    .\scripts\test.ps1

Focused tests: seed/draw contract, deterministic replay/forged diagnostics,
cache/source binding/currency/deepcopy, review versions, stale edit, unsupported
refs/overrides, expiry/acknowledgement, corruption/export guard, origin controls.
Actual browser QA additionally checks scoped diagnostics, draft→reviewed
research annotation, revisioned export/history, mobile and no console errors.
Heavy browser replay và full suite phải chạy lần lượt khi OS memory pressure;
không đổi frozen methodology để che lỗi allocation.

## 5. Remaining scope

Convergence confidence/effective precision nhiều seeds hơn; calibrated
dependence/recovery; contractual EIR/cash-flow/staging/default evidence;
obligor linkage/consolidation; actual finance overlays with separately
declared calculations; authenticated owner/reviewer controls và richer history
UI vẫn mở. Full 5 workspaces/50 capabilities giữ nguyên; research implementation
không thay actual-data qualification, Clarity access, market quotes hay legal
terms chưa có.
