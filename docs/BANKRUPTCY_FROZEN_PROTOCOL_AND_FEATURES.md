# P3 — Frozen one-year bankruptcy protocol & development features

09/10/2026. Source `bankruptcy-case-e1e67482a2b4` original-ARFF facts;
study **`bankruptcy-study-e0c65ad465e3`**, features
**`bankruptcy-features-fc51ea164f93`**. Protocol/partition và preprocessing đã
chạy thật; **chưa fit model, chọn champion hay score reserved final**.
Source/precision/ratio app: [BANKRUPTCY_RATIO_WORKFLOW.md](BANKRUPTCY_RATIO_WORKFLOW.md).

Đây là historical protocol/features checkpoint. Latest development fitting,
validation/group uncertainty và champion freeze đã hoàn tất ở
[BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md](BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md);
latest one-time final ở [BANKRUPTCY_FINAL_MODEL_CARD.md](BANKRUPTCY_FINAL_MODEL_CARD.md).
Source protocol/partitions/encoder không
đổi trong bước fitting tiếp theo.

## Frozen scope và lựa chọn trước metrics

Horizon1yr/source code5, 5.910 statements/410 source-bankruptcy labels=1.
Chọn horizon từ intended task trước modelling, không từ so sánh AUC năm
horizon. Các horizons khác là studies riêng, không concatenate thành cùng PD.
Protocol lập sau source quality/precision inspection, trước model fitting và
validation metrics. Không tuyên bố protocol có từ trước khi nhìn source.

`protocol.json` khóa 64 features, transform, seed, group assignment, bốn
partition, fixed model settings, calibration và selection rubric:

- Constant: train source-label prevalence; logistic C1/max_iter3000/tol1e−8,
  no class weights; histogram boosting lr0,05/120 iterations/15 leaves/
  min_leaf30/L2=1/seed365, early stopping disabled. Chưa fit các models này.
- Platt logistic trên raw clipped logits, C1, epsilon1e−12, calibration
  partition riêng; compare raw/calibrated logistic và boosting, constant raw.
- Primary **validation Brier, lower better**; secondary validation log loss,
  tie tolerance1e−6; final tie order constant/raw logistic/Platt logistic/raw
  boosting/Platt boosting. AUC/AP báo cáo, không dùng chọn champion.
- No hyperparameter search, no final-test selection, source-record weighted
  exact-group uncertainty; không gọi exact groups là identified firms.

Reserved final còn cần model/transform freeze và one-time consumption ledger.
Registry hiện tại là **study reservation**, chưa final-score consumption ledger.
Không khẳng định one-time evaluation đã triển khai hay đã chạy.

## Partition thực tế và chống reset bằng cách tạo lại case

Fingerprint giữ ordered64 finite numeric values dưới dạng float.hex và explicit
NULL; +0/−0 có cùng numeric meaning. Không dùng label trong fingerprint.
Group chứa mixed labels vẫn giữ mọi rows và một partition; không majority-
relabel hoặc dedup. Source hiện tại không có mixed-label exact groups.

Class-stratified exact-group ranking dùng seed+horizon+stratum+group hash;
group weighted midpoint theo60/15/15/10 cumulative boundaries. Fractions có
thể xấp xỉ khi group weights >1; không tách group để ép exact fraction.

| Partition | Statements | Label=1 | Label=0 | Exact groups |
|---|---:|---:|---:|---:|
| Train | 3.546 | 246 | 3.300 | 3.516 |
| Calibration | 886 | 61 | 825 | 870 |
| Validation | 887 | 62 | 825 | 879 |
| Reserved final | 591 | 41 | 550 | 585 |
| Total | 5.910 | 410 | 5.500 | 5.850 |

60 excess exact duplicate records retained; **0 groups cross partitions**.
Input order không làm đổi assignment. Ordinal chỉ là identity/lineage key,
không predictor. Firm IDs và dates chưa có: vẫn **unknown entity overlap** và
**not OOT**. Exact-vector disjointness không chứng minh independent firms.
Reserved final chỉ41 positives; future uncertainty phải phản ánh small support.

Registry key = SHA256(original official ARFF ZIP digest + horizon), dưới
`private evidence omitted from public release`. Atomic directory reservation
pin một study cho source/horizon; case ID, CSV mirror hoặc method version không
được dùng để reset study. Rerun cùng case trả verified existing study; case
mới trên cùng original source/horizon bị từ chối và phải reuse study cũ.
Incomplete reservation cần review; không tự xóa hoặc tạo alternate final set.

## Train-only transformation đã chạy

Development SQL chỉ chọn train/calibration/validation rows từ pinned
partitions join canonical facts; **591 reserved-final predictors không được
selected để encoding hoặc ghi vào development artifacts**. Raw canonical
dataset vẫn có final source facts; source verification/data audit không phải
model scoring hoặc development feature encoding.

64 original ratios → train-median impute → signed `asinh` → train mean và
population standard deviation; zero scales →1. Cộng64 fixed binary missing
indicators = **128 dimensions**. Signed asinh giữ ordering và negatives,
ổn định numeric range cho extreme ratios; không clip/winsorize hoặc suy đoán
log base/unit của source. Đây là preprocessing transform, không thay source
ratio definitions. Fit toàn bộ parameters trên train; calibration/validation
chỉ transform. No all-missing train feature trong actual source hiện tại.
Nếu all-missing train feature xuất hiện thì recorded fallback median0/scale1
và missing indicator; không suy luận missing value bằng zero raw observation.

Encoder.fit từ chối non-train roles/refit, boolean/string/nonfinite fields.
Median computation tránh overflow khi các finite values rất lớn. Encoder JSON
restoration reproduces native matrix **exactly**; serialized scales phải finite
positive, feature order đúng. Future model X chỉ lấy x001…x128; ordinal/group/
partition/target columns trong private development table dùng audit riêng.

Actual artifacts có **5.319 development rows ×128 =680.832 numeric cells**.
`encoder.json`, `development.parquet`, `coverage.json`, access-start/completion
receipts pin study/source/method hashes. Final encoded rows=0, model fitting=0,
final scoring=0. No score, AUC, Brier hoặc champion được tạo ở checkpoint này.

## Evidence và commands

Independent DuckDB audit **`bankruptcy-feature-audit-cf483766dd8c` PASS**:
SQL recomputes training medians, means/std afterasinh, và mọi development
feature cell từ original facts. Max scaled train-stat difference
**4,9960e−15**; max encoded absolute difference **9,5923e−14**;
predefined tolerance1e−10. **0 group crossings,0 final encoded rows,0 development
key differences**. Đây là preprocessing numerical proof, chưa model validation.

Full software suite **639 tests PASS** (375 engine +264 application),72,31s.
12 added checks cover order-invariant grouping, NULL/signedzero identity,
mixed-label groups, reserved lineage reuse/reset rejection, encoder/extremes/
missingness/serialization/train-only fit, changed evidence và final-role SQL
access. Deliberate final-predictor poison test mocks source verification only
to isolate query boundary; production source verification rejects changed
source bytes. Không dùng test mock để claim actual poisoned source accepted.
Previous browser acceptance của ratio app giữ riêng8 checks; turn này không
thay UI/server hoặc chạy thêm browser acceptance.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_bankruptcy_study.py --case bankruptcy-case-e1e67482a2b4 --horizon 1
.\.venv\Scripts\python.exe -X utf8 scripts/audit_bankruptcy_features.py --features bankruptcy-features-fc51ea164f93
.\scripts\test.ps1
```

First command reuses same frozen study on rerun nhưng tạo new development
feature artifact; không score final. Next: fit fixed constant/logistic/boosting
trên train, separate calibration, validation score persistence/native parity,
paired exact-group uncertainty, implement frozen rubric, champion freeze,
then one-time final with lineage consumption ledger/model card/UI. SEC/SME
timing/memo/covenant/debt workflows và other four modules vẫn thuộc full scope.
