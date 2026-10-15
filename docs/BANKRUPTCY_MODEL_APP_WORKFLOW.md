# P3 — Bankruptcy Model Evidence

Mở app local bằng `scripts/run.ps1`, chọn **P3 · Bankruptcy model** hoặc
`http://127.0.0.1:8770/?view=bankruptcymodel`.
Snapshot thực tế: `bankruptcy-model-view-2f63a60b48df`, từ kết quả cuối
`bankruptcy-holdout-907870affe8d` và freeze `bankruptcy-freeze-cebc982ca176`.

## Phạm vi và cách đọc

Đây là benchmark phân loại phá sản theo horizon **một năm** của UCI 365.
Financial statements không phải borrower/loan độc lập đã định danh; kết quả
không được diễn giải thành PD khoản vay hoặc qualification triển khai.

1. **Cohort support:** train 3.546/246 events, calibration 886/61,
   validation 887/62, final 591/41. Exact-feature groups giữ cùng partition;
   việc này chưa chứng minh không trùng doanh nghiệp hoặc out-of-time.
2. **Validation:** bảng riêng cho constant, logistic và boosting, với/không
   Platt. Champion `boosting_platt` chọn bằng rubric đã chốt trước fitting:
   Brier, rồi log loss, rồi simplicity order. Final không chọn model.
3. **Final:** chỉ champion; AUC 0,962794, AP 0,863689, Brier 0,021611,
   log loss 0,087160. Hiển thị 95% exact-group bootstrap intervals và
   1.000 valid draws. Chỉ 41 events; uncertainty conditional trên model cố định.
4. **Reliability bins:** count, events, mean probability và observed rate;
   bin rỗng giữ unavailable, không thay bằng zero. Các nhóm nhỏ cần thận trọng.
5. **Evidence:** target, transform, fixed fit settings, calibration, study,
   freeze, evaluation IDs, attribution và giới hạn sử dụng. Có link về ratio
   explorer, nơi cả năm horizons có dữ liệu; chưa phải cả năm có model.

## API, export và quyền truy cập

- `/api/bankruptcy-model-views`: catalog verified/unavailable, không filters.
- `/api/bankruptcy-model-view?view_id=...`: snapshot verified.
- `/api/bankruptcy-model-report?view_id=...`: JSON attachment tương đương view.

Chỉ chấp nhận một `view_id`; extra/duplicate filters bị từ chối. Chỉ loopback,
Host/origin kiểm tra, no-store/CSP, private và chưa public-release approved.
Export gồm aggregate metrics, cohorts, intervals và reliability bins; không
gồm source ordinals, group IDs, từng xác suất, model coefficients hoặc raw paths.

Mỗi lần đọc xác minh methods, immutable receipt/snapshot digests và tái đối
chiếu projection với evidence nguồn đã lưu. Thay metric rồi cập nhật digest
vẫn không qua kiểm tra. Deep verification có thể mất vài giây.

Ledger đã **completed**. Các routes không fit, select, transform hay infer
trên final. Verifier đọc saved final scores để tái tính metrics/intervals;
validation lineage được kiểm tra riêng. Không có API rescore hoặc reset final.

## Acceptance

Checkpoint 09/10/2026: **675 tests PASS** (375 engine + 300 application),
145,67 giây. Actual-source browser **8 checks PASS**:
`bankruptcy-model-browser-qa-47386fc6e30b`. Desktop/mobile screenshots được
kiểm tra trực quan; chuỗi cấu hình dài xuống dòng, không tràn trang 390px.
Final inference functions bị khóa trong toàn bộ browser run; ledger bytes
không đổi. Live API trên port 8770 trả HTTP 200 đúng snapshot đã xác minh.

Software checks bảo vệ projection privacy, forged aggregate, method changes,
identifier, extra/duplicate query parameters, private attachment và Host/origin.
Actual-source browser script `scripts/browser_bankruptcy_model_qa.py` kiểm tra
real cohorts/metrics/intervals, export parity, URL reload, mobile 390px,
navigation và không cần mortgage runs. Script khóa hàm final transform/predict
và đối chiếu ledger bytes trước/sau, xác nhận chỉ đọc saved evidence.

Chi tiết model: [BANKRUPTCY_FINAL_MODEL_CARD.md](BANKRUPTCY_FINAL_MODEL_CARD.md).
Phần còn lại: finding/review workflow, intended-use/policy/monitoring qualification,
nguồn SEC/SME và toàn bộ acceptance của [suite plan](PLAN_FIVE_WORKSPACES.md).
