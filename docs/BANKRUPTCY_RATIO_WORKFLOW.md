# P3 — Polish Bankruptcy Ratio Lab

09/10/2026. Canonical case `bankruptcy-case-e1e67482a2b4`, private app snapshot
`bankruptcy-view-e99b04caf0ed`. Đã có intake, original-source reconciliation,
typed financial facts, horizon/feature profiles, app/API và scoped export.
Chưa fit bankruptcy model hoặc xác minh entity-disjoint/OOT validation.

## 1. Dữ liệu và source interpretation

CSV/metadata từ batch `suite-619b1ee9aa8c`. Bổ sung official ZIP qua HTTPS:
`polish-reference-0fcebfb0f6ff`, **8.834.471 bytes**, SHA256
`17377929aa0b204bbf957e56462cf827c19fe4e2ce89f27dfbc77f9ea2bb16c9`.
Kiểm tra CRC, đúng năm ARFF members, bounded member sizes; đọc trực tiếp ZIP,
không extract hoặc tải từ mirror. Raw, receipts và artifacts giữ trên D:.

[UCI365](https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data)
mô tả năm forecasting cases. `year` trong CSV là subset code; không phải
calendar year, observation year hoặc publication date. Metadata headline
10.503 là subset thứ ba; combined CSV có **43.405 financial statements**.

| CSV code | Forecast horizon | Statements | Source class=1 | Source class=0 | Rows with missing | Exact feature duplicate excess |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 5 năm | 7.027 | 271 | 6.756 | 3.833 | 82 |
| 2 | 4 năm | 10.173 | 400 | 9.773 | 6.085 | 90 |
| 3 | 3 năm | 10.503 | 495 | 10.008 | 5.618 | 87 |
| 4 | 2 năm | 9.792 | 515 | 9.277 | 5.023 | 82 |
| 5 | 1 năm | 5.910 | 410 | 5.500 | 2.879 | 60 |

Class fraction là tỷ lệ nhãn của source subset, chưa calibrated loan PD.
Bankruptcy source label không tự trở thành loan delinquency/default, IFRS9 PD,
Vietnam SME calibration hoặc observed underwriting outcome.
Source là historical research sample; không có released firm ID, statement
date, filing/publication time hay loan terms. Không ghép firm qua subsets,
không gọi split theo `year` là temporal validation và không pool năm targets.
Attribution: Tomczak, S. (2016), DOI 10.24432/C5F600; CC BY 4.0.

## 2. Phát hiện CSV precision loss và xử lý có evidence

Đối chiếu toàn bộ 43.405 rows × 64 features với original ARFF cho thấy:

| Code | Numeric cells CSV khác ARFF | Affected statements |
|---|---:|---:|
| 1 | 0 | 0 |
| 2 | 652 | 492 |
| 3 | 731 | 520 |
| 4 | 709 | 490 |
| 5 | 0 | 0 |

Tổng **2.092 cells / 1.502 statements**. Mọi chênh lệch là original scientific
token có CSV value bằng three-significant-digit `ROUND_HALF_UP`. Ví dụ
subset2/row1/A55: ARFF `2.425e+005` = **242.500**; CSV = **243.000**.
Đây là quan sát xác minh trên payload; chưa xác minh nguyên nhân upstream.
Không dùng tolerance chung để bỏ qua arbitrary mismatches.

Labels, missingness, row counts và within-subset order khớp. Unexplained
numeric differences, label differences hoặc missingness differences đều fail.
Canonical ratios dùng original ARFF values. CSV values không bị ghi đè:

- `financial-statements.parquet`: 43.405 original-ARFF facts; 68 typed fields.
- `csv-mirror.parquet`: 43.405 independently reconciled typed CSV records.
- `csv-arff-rounding.parquet`: 2.092 cells với ordinal, subset, feature,
  cả hai numeric values, original token và explicit matching-rounding flag.
- `feature-quality.parquet`: 320 profiles = 5 horizons × 64 features.
- `horizon-summary.parquet`: 5 reconciled populations.
- `contract.json`, run-start/completion receipts: source/method hashes,
  contracts, qualification và lineage.

DuckDB parser độc lập đối chiếu raw CSV ↔ CSV mirror bằng bidirectional
EXCEPT ALL: **0 differing rows**. Arrow original facts roundtrip equality PASS.
Không gọi raw CSV ↔ original ARFF là zero differences; rounding table là phần
bắt buộc của interpretation và UI/export.

## 3. Ratios, units, missingness và grain

CSV A1…A64 ↔ ARFF Attr1…Attr64 ↔ source definitions X1…X64 được nối theo
verified column order. Feature cards giữ literal definitions trong metadata,
không tạo financial statements/component balances để tính lại ratios.
Float64 giữ giá trị numeric để phân tích; raw source tokens vẫn có trong ZIP/CSV.
Không tuyên bố exact monetary accounting precision cho float financial features.

CSV `NaN` và ARFF `?` → NULL; nonfinite hoặc unknown numeric tokens fail.
Signed values/zero/extremes giữ nguyên. Không impute, clip hoặc winsorize ở
canonical stage. **A37 thiếu 18.984/43.405 cells**. `abs > 1e6` chỉ là
diagnostic count, không rejection rule; min/median/max dùng known values.
All-missing feature → NULL statistics, không zero.

A29 log base chưa rõ; A55 working-capital currency/unit chưa rõ; không đổi
sang USD/VND hoặc mặc định log10. A48/A49 source EBITDA wording dùng
minus depreciation; giữ nguyên và cảnh báo, không silently sửa thành formula
khác. Days-like ratios và monetary-like fields không có chung unit.

Row identity là CSV source SHA256 + record ordinal, **không firm identity**.
401 excess exact feature duplicate records được giữ. SQL independent audit
`bankruptcy-duplicates-d2938d9890a8` PASS: 82/90/87/82/60 duplicate groups,
không conflicting labels trong các nhóm exact duplicates của source hiện tại.
Không thấy identical 64-feature vectors qua subsets; điều này **không chứng
minh entity disjointness**: cùng firm ở các năm khác có ratios khác nhau.

## 4. App/API/export đã chạy

App: http://127.0.0.1:8770/?view=bankruptcy&bankruptcy_view_id=bankruptcy-view-e99b04caf0ed

Navigation P3 có SBA descriptive case và bankruptcy-ratio case riêng.
Chọn verified snapshot, forecast horizon1–5 và featureA1–A64. UI hiển thị
whole selected-horizon population, literal definition, feature extrema/
missingness và toàn bộ 64 quality rows. Feature selector thay highlighted
metric; không lọc population. Precision audit luôn theo selected horizon.
Source class fraction chưa là calibrated PD. No mortgage-run dependency.

| Endpoint | Scope |
|---|---|
| `/api/bankruptcy-views` | Verified/unavailable snapshot catalog; no filters |
| `/api/bankruptcy-view?view_id=…` | Whole-source aggregate snapshot |
| `/api/bankruptcy-report?view_id=…&horizon=4&feature=A55` | Forecast4yr = code2; 64 quality profiles và selected feature; private attachment |

Unknown/duplicate filters, malformed IDs/horizons/feature names bị từ chối.
Không có arbitrary SQL/row-level browser lookup. Private exports giữ numeric
precision, contracts/attribution và denominator. Browser display có thể làm
tròn; report giữ actual numeric values. Host/origin/CSP/no-store guards reuse
local server. Methods/source/raw/output changes invalidate current snapshot.

Actual sample scope: horizon4yr/A55 = 10.173 statements, 10.172 known,
1 missing; min−1.805.200, max3.657.400, median832,67. Không chuyển thành
monetary units chưa được xác minh.

Software suite: **627 tests PASS**, 375 engine + 252 application, 73,80s.
25 added tests cover reference mismatch/rounding, source values/metadata,
duplicates/extremes/NULLs, changed evidence, horizon filters và actual HTTP.
Browser `bankruptcy-browser-qa-48cc91e0317b`: **8 checks PASS**, actual source,
horizon/feature/precision scope, canonical/export extrema parity, URL reload,
390px mobile, no mortgage dependency, P5/SBA/P2 navigation và no JS errors.
Screenshots desktop/mobile đã xem. Earlier failed intake/browser/audit attempts
được giữ riêng; không tính là completion receipts.

```powershell
# Download original ARFF ZIP only if --reference is omitted:
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_bankruptcy.py --suite suite-619b1ee9aa8c --reference polish-reference-0fcebfb0f6ff
.\.venv\Scripts\python.exe -X utf8 scripts/build_bankruptcy_view.py --case bankruptcy-case-e1e67482a2b4
.\.venv\Scripts\python.exe -X utf8 scripts/audit_bankruptcy_duplicate_groups.py --case bankruptcy-case-e1e67482a2b4
.\.venv\Scripts\python.exe -X utf8 scripts/browser_bankruptcy_qa.py
.\scripts\test.ps1
```

## 5. Kế hoạch model — one-year final/card đã có, model app còn thiếu

Protocol/features checkpoint: [BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md](BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md).
Development: [BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md](BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md).
Latest: [BANKRUPTCY_FINAL_MODEL_CARD.md](BANKRUPTCY_FINAL_MODEL_CARD.md).
Steps1–5 đã có one-year protocol, partitions, features, actual development fit,
group uncertainty và rubric selection. Step6 đã có champion freeze/one-time
final/ledger/uncertainty/model card; step7 model UI/API/export/findings còn thiếu.
Whole suite hiện667 tests;627 phía trên là historical ratio-app checkpoint.

1. Freeze benchmark intended use và protocol **trước fitting/validation**.
   Start horizon1yr/code5, 5.910 statements/410 positives; các horizons khác
   là studies riêng. Đây là lựa chọn intended task, không chọn từ AUC của
   năm models. Source quality đã được inspect; ghi rõ protocol lập sau data
   audit nhưng trước development fitting. Không tuyên bố preregistration từ
   trước khi nhìn source.
2. Create stable exact-feature-group IDs from original ratios + explicit NULL
   serialization. Giữ duplicates cùng partition; không dedup/remove positives.
   Freeze deterministic class-stratified group assignments với train60%,
   calibration15%, validation15%, reserved final10% approximate by group.
   Reconcile group disjointness/record counts/support; unknown firm overlap
   và non-OOT vẫn là limitations. Không để ordinal/subset/horizon/label vào X.
3. Train-only transforms: finite numeric checks, train median imputation,
   missing indicators và train scaling cho logistic. All-empty train columns
   có explicit fallback/flag; không dùng validation/final values để chọn
   fill/caps/features. Serialized transforms phải reproduce predictions.
   No near-duplicate tolerance/distance threshold tuned on final test.
4. Fit fixed reference constant, logistic và tree challenger trên train;
   fixed modest hyperparameters trước metrics, không unbounded tuning.
   Calibration dùng calibration split riêng; raw/calibrated semantics rõ.
   Persist parameters/model and compare native/persisted predictions. Evaluate
   Brier/log loss/ROC AUC/AP/reliability trên validation, uncertainty resampling
   duplicate groups với record weights. Không gọi groups là identified firms.
5. Freeze explicit selection rubric trước validation execution; ưu tiên
   probability-quality metrics, report ranking và sample uncertainty, giữ
   reference nếu evidence không hỗ trợ challenger. Threshold/cost scenarios
   là downstream declared assumptions; không optimized loan approvals từ
   source class sample. Reserved final predictors chưa được materialize vào
   development artifacts và chưa score.
6. Freeze model/transforms/methods/config/partition hashes; one-time final
   evaluation có consumption ledger. No refit/reselect/re-score final bằng
   cách đổi case ID. Export final metrics và research model card, đồng thời
   giữ low-positive-support/unknown-entity/OOT/financial-definition limits.
7. Integrate validation/frozen-result/model-readiness UI và findings. SEC
   statements, issuer memo, covenants/debt schedules và SME timing models
   còn riêng trong full P3 plan; bankruptcy benchmark không thay chúng.
