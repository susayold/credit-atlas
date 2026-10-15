# P1.03 — behavioral model và validation benchmark

Đã audit độc lập metrics và paired uncertainty từ saved validation predictions; thêm reliability explorer cho cả sáu model/variant vào **Retail → Validation**. Không fit/rescore actual models và không mở lại final-test predictors.

## Population và phương pháp

Validation có **4.499 clients / 995 events**, ba model constant/logistic/boosting, mỗi model có raw/calibrated probabilities. 13.497 saved score rows có cùng ordered client cohort và labels. IDs/labels khớp đúng validation partition; không dùng ID làm predictor.

Audit tự tính AUC bằng weighted positive-negative pairs với half-credit cho ties, AP bằng precision tại toàn bộ tied threshold group, Brier bằng weighted squared error và log loss bằng weighted Bernoulli loss. Không gọi scorer hoặc metric helpers của pipeline, không dùng sklearn metrics trong audit.

1.000 bootstrap replicates, seed676: resample clients trong mỗi class; row multiplicities tái tạo bằng weights; cùng draw dùng cho cả sáu variants. Audit tự tính lại absolute và paired 95% percentile bounds. Đây là fixed-model, fixed-class-count uncertainty; không bao gồm refit, prevalence/household uncertainty hoặc multiple-comparison correction.

## Validation raw variants

| Model | AUC | AP | Brier | Log loss |
|---|---:|---:|---:|---:|
|Constant|0,500000|0,221160|0,172248|0,528373|
|Logistic|0,776344|0,548004|0,134773|0,431000|
|Boosting|0,784210|0,560998|0,132362|0,423153|

Boosting–logistic cải thiện Brier khoảng0,002411 và log loss khoảng0,007848. Paired intervals của hai proper scores có lower>0 trong conditional exploratory analysis; AUC/AP intervals có zero. Không suy ra superiority trên population mới từ các con số này.

## Chọn model và final-test boundary

Rubric development chọn boosting/raw khớp saved comparison: Brier cải thiện≥0,001; Brier/log-loss lower bounds>0; AUC degradation trong tolerance. Calibration của boosting không đạt quy tắc chọn variant. Rubric được đặt sau development inspection, không phải preregistered confirmatory decision.

Case/assessment/comparison/freeze hashes khớp. Freeze receipt và holdout access/evaluation metadata ghi model/variant đã chốt trước final evaluation; không có model selection hoặc refit trong access receipt. Đây là audit persisted evidence, không chứng minh dữ liệu chưa từng được nhìn thấy ở cấp tổ chức. Historical raw cohort đã tồn tại trước freeze. Không đọc private holdout scores hoặc predictors trong đợt này; chỉ đọc saved metadata/aggregate.

## Bằng chứng

- `artifacts/private/retail-validation-acceptance-1a726071255c/receipt.json`: 24 point metrics, 60 reliability bins, 132 interval values khớp; max absolute error **1,3322676295501878e−15**, tolerance1e−12; validation ID/label parity, suite projection và selection-rule parity; model-fit/scoring/final-predictor reads đều0; ledger không đổi. Access intent được lưu trước audit.
- `artifacts/private/retail-validation-acceptance-tests.xml`: **19 tests PASS**, gồm độc lập tie/weighted/edge metric checks và synthetic assessment/comparison guards. Synthetic tests không fit lại actual benchmark.
- `artifacts/private/retail-validation-browser-acceptance-0c1160bc0618/receipt.json`: 6 variants, 60 bin rows, 39 known chart points, 6 metric rows, 20 paired metric rows và suite export khớp; reload/tab/mobile PASS; final-chart population label giữ đúng; ledger không đổi.
- `artifacts/private/retail-data-contract-browser-954d18e891a6/receipt.json`: source/month/category/target contract regression PASS sau bổ sung validation explorer.

App vẽ chỉ supported bins; empty bins hiển thị **Unavailable**, không tạo điểm0%. Chart validation có nhãn riêng, không gọi nhầm final-test. Suite JSON export giữ cả sáu variants và paired results; dropdown chỉ chọn chart đang xem, không thay đổi scope của whole-suite export hoặc selected model.

## Chưa hoàn thành ngoài benchmark

Random cohort không là temporal OOT. Chưa có deployment cohorts, Vietnam calibration, intended-use approval, authenticated sign-off hoặc production qualification. Không dùng benchmark này làm approval-time underwriting, PD12 hoặc regulatory default. P1.02 và các yêu cầu data/model khác giữ gate riêng. Mục tiêu 100% toàn dự án chưa đạt.
