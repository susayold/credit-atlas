# P1 — UCI350 behavioral benchmark: dữ liệu và protocol

Scope: 30.000 credit-card clients trong cohort Taiwan của source, với lịch sử
April–September 2005 và source-defined next-month default target. Đây là
behavioral benchmark. Không áp dụng calibration này cho Việt Nam, không coi
source label là regulatory default hoặc một approval-time underwriting target.

## Source và typed adapter

Raw acquisition: `data/private/public-suite/suite-619b1ee9aa8c/uci-retail.csv`
và metadata JSON cùng directory. Adapter `src/credit_atlas/retail.py` kiểm tra
chính xác X1…X23 mapping với descriptions trong official UCI metadata, binary
Y, unique ID và domain ranges trước khi ghi typed Parquet.

Canonical clients giữ 23 fields, source ID và target trong private storage.
Long history có 6 rows/client với reference month, status code, signed bill
amount và previous payment amount. Đơn vị monetary là NT dollar/TWD của
source. Negative statement balances được giữ nguyên, không clipping.
Không tạo 180.000 independent supervised observations từ 30.000 labels.

Source codes PAY=-2/0, education=0/5/6 và marriage=0 có trong payload nhưng
không được giải thích đầy đủ bởi simplified source dictionary. Adapter giữ
nguyên codes; không tự suy diễn -2 là good/bad/default hoặc gộp thành DPD=0.
History reference dates không chứng minh historical publication availability.

## Predictors và partition contract

Baseline predictor set: 13 numeric fields (limit, six statements, six previous
payments) và 6 payment-status categorical fields. ID/target không phải
predictor. SEX, EDUCATION, MARRIAGE và AGE được giữ để audit nhưng excluded
from prediction allowlist. Điều này không tự chứng minh model fair: các
remaining fields vẫn có thể có proxy relationships; cần subgroup/support
review trước intended-use claims.

Protocol `uci350-behavioral-random-benchmark-v1` dùng deterministic SHA-256
ranking theo source ID và seed trong mỗi target class. Fractions 60/15/15/10:
train, separate calibration, validation và reserved final-test. Integer rounding
được xác định bằng cumulative floor boundaries; tổng các roles luôn đúng
source population. Rows order không ảnh hưởng assignments. Không có client
ở hai roles. Không gọi partition này là temporal/OOT split.

| Role | Positive | Negative | Total |
|---|---:|---:|---:|
| Train | 3.981 | 14.018 | 17.999 |
| Calibration | 996 | 3.505 | 4.501 |
| Validation | 995 | 3.504 | 4.499 |
| Reserved final-test | 664 | 2.337 | 3.001 |

Preparation có thể đọc all labels để stratify và source facts để kiểm tra
quality. Chưa có development model matrix hay final-test scoring. Các bước
feature fitting/model selection sau này chỉ nhận permitted development roles.

## Reconciliation và receipts

Typed client values được đối chiếu toàn bộ bằng SQL casts từ raw CSV và
bidirectional EXCEPT ALL. History được đối chiếu qua sáu source-month SELECTs
riêng, kiểm tra mỗi status/bill/payment value. Actual run cho zero differing
client rows và zero differing history rows; source/input hashes được kiểm tra
lại trước complete receipt. Run giữ protocol, support, category counts,
quality warnings, reconciliation và output SHA-256.

## Model steps còn phải triển khai

1. Train-only scaler/category vocabulary đã triển khai trong
   `src/credit_atlas/retail_features.py`. Actual feature run
   `retail-features-d53aa8ba9ed6` học 13 numeric mean/scales và sáu status
   vocabularies từ 17.999 train clients; feature dimension 81. JSON reload và
   Parquet matrix parity khớp trên toàn bộ 26.999 development clients.
   Chưa có risk-model fitting. Numeric missing/nonfinite bị từ chối; codes
   chưa thấy trong train đi vào explicit unseen bucket, không cập nhật vocabulary.
   Feature query chỉ chọn 19 allowlisted fields của train/calibration/validation.
   All labels/IDs có thể đọc để xác minh saved stratified assignments, với
   access intent lưu trước lần đọc. Reserved final-test predictor rows không
   có trong development matrix; transform API từ chối `final_test` partition.
   Actual validation có 2 PAY_4 và 1 PAY_5 values chưa thấy trong train;
   coverage report giữ các counts này, không mở rộng vocabulary từ validation.
2. Constant và fixed-settings logistic baseline; bounded histogram boosting
   challenger cùng features/cohort. Không reuse mortgage origination allowlist
   hoặc giả tạo later landmark dates để qua temporal mortgage gates.
3. Separate sigmoid calibration; validation ROC AUC, average precision, Brier,
   log loss, reliability/support và uncertainty. Investigate negative calibration
   slope/convergence failures, không âm thầm thay model.
4. Model/feature/protocol freeze trước reserved final-test; held-out evaluation
   có tên random benchmark, không OOT. JSON artifacts và rescoring parity,
   model card, intended use/limitations, UI evidence và reproduction checks.
5. Policy/cost scenarios chỉ khi assumptions rõ. Dataset không có đủ income,
   reject outcomes, collections interventions hoặc full contractual schedules
   để khẳng định affordability, causal collections efficacy hay pricing optimum.

Source attribution: [Yeh, I. (2009), Default of Credit Card Clients, UCI,
DOI 10.24432/C55S3H](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients),
CC BY 4.0. Actual development results were subsequently created; see
[RETAIL_DEVELOPMENT_RESULTS.md](RETAIL_DEVELOPMENT_RESULTS.md). Final
holdout/model-selection and other P1 acceptance requirements remain open.

Command:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_retail.py --suite suite-619b1ee9aa8c
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_retail_features.py --case retail-case-470bdb40682f
.\.venv\Scripts\python.exe -X utf8 scripts/assess_retail.py --features retail-features-d53aa8ba9ed6
```
