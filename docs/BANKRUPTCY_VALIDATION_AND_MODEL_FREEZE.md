# P3 — One-year bankruptcy development validation & model freeze

09/10/2026. Original-ARFF source case `bankruptcy-case-e1e67482a2b4`, frozen
study `bankruptcy-study-e0c65ad465e3`, development features
`bankruptcy-features-fc51ea164f93`. Actual assessment
**`bankruptcy-assessment-0e7cb5cc894d`**, paired group comparison
**`bankruptcy-comparison-e3ee221ca493`**, authoritative model freeze
**`bankruptcy-freeze-cebc982ca176`**. Selected **boosting_platt**.
Reserved final591 statements/41 source-positive labels **chưa được score**.
Đây là development validation, chưa final evaluation/production validation.

Historical checkpoint ở trên. Latest one-time final đã hoàn tất và consumed:
[BANKRUPTCY_FINAL_MODEL_CARD.md](BANKRUPTCY_FINAL_MODEL_CARD.md). Frozen model,
protocol và validation artifacts không đổi sau final; không reselect/rescore.

Source/ratio contract: [BANKRUPTCY_RATIO_WORKFLOW.md](BANKRUPTCY_RATIO_WORKFLOW.md).
Protocol/preprocessing: [BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md](BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md).

## 1. Actual fitting và leakage boundary

Train3.546/246 positives; calibration886/61; validation887/62. Exact feature
groups không cross partitions; unknown firm overlap và not-OOT vẫn giữ.
64 train-median/asinh/scaled ratios +64 missing indicators, dimension128.
Source ordinal, group ID, horizon, subset code và label không vào model X.

Before fit, assessment reads only three development roles from pinned
canonical facts/partitions. It independently reconstructs identities, labels,
feature-group fingerprints, exact train encoder state và entire development
matrix; changed feature values vẫn fail nếu modified digest được cập nhật.
No reserved-final predictors được selected ở assessment/comparison/freeze.

Frozen settings thực thi đúng protocol:

- Constant train label prevalence0,06937394247038918.
- Logistic C1/max_iter3000/tol1e−8/no class weights; fit train only.
- Histogram boosting lr0,05,120 iterations,15 leaves,min_leaf30,L2=1,
  seed365; early stopping disabled; no internal validation, no class weights.
- Separate Platt logistic C1 on raw clipped logits for logistic/boosting;
  fitted calibration split, not validation. Clip epsilon1e−12. Boosting
  calibration slope1,0483837984285598/intercept0,31232135785996823.

Convergence warnings fail the run; no automatic changing of settings to obtain
better metrics. Sklearn1.8.0 required by reviewed tree exporter. JSON trees
retain native numeric thresholds and leaf contributions; no pickle loading.
Numerical JSON scorer reused from reviewed retail helper; P1 artifacts,
methods, champion và consumed holdout không bị chỉnh sửa/rescore.

Native↔JSON predictions on **5.319 development rows**, all3 model states and
2 Platt states: **max absolute difference0,0** on actual run. Saved validation
scores are separately reconciled with metrics and persisted model/calibration
predictions. No fit hoặc selection uses final predictions.

## 2. Validation evidence — source-statement weighted

| Candidate | ROC AUC | Average precision | Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|---:|
| Constant raw | 0,500000000 | 0,069898534 | 0,065013004 | 0,253378534 |
| Logistic raw | 0,932766373 | 0,759224790 | 0,030317558 | 0,118875968 |
| Logistic Platt | 0,932766373 | 0,759224790 | 0,030456315 | 0,119041099 |
| Boosting raw | 0,967917889 | 0,864015573 | 0,022327009 | 0,086950949 |
| **Boosting Platt** | **0,967917889** | **0,864015573** | **0,021898554** | **0,085251500** |

Each candidate uses **887 same ordered statements/62 events**,879 exact
groups. Private score artifact4.435 rows =887×5; all candidates retain same
ordinals/labels/groups. AP is sklearn average_precision, not trapezoidal PR
area. Reliability uses ten fixed probability bins; empty bin stats=NULL, not
zero observed rate. Positive-slope Platt preserves AUC/AP ranking here.

Metrics apply to this historical source sample and one-year bankruptcy label,
not loan default PD, credit approval performance, Vietnam calibration hoặc
issuer financial memo. Unknown firm identities/availability, retrospective
sample construction và only62 validation positives limit generalization.

## 3. Paired group bootstrap và interpretation

**1.000 valid replicates**,seed3651,0 single-class exclusions. Each replicate
draws879 exact-feature groups with replacement; all statements of every
selected group retained, preserving duplicate source-record weights. Replicate
rows range880–896; không force887 bằng cách split duplicate groups. Same draws
used for five candidates; paired differences use matching draw IDs.

95% percentile intervals, conditional on fitted models/current validation
groups; no model retraining. Exact groups không identified firms. Intervals
exploratory/unadjusted for multiple comparisons. Replicate count/seed chosen
after point-metric inspection, disclosed in bootstrap-settings; không claim
toàn bộ uncertainty procedure preregistered. Model settings/selection rubric
were frozen before fitting/validation metrics.

Boosting Platt minus logistic Platt:

| Metric | Point difference | 95% lower | 95% upper |
|---|---:|---:|---:|
| ROC AUC | +0,035151515 | +0,004094382 | +0,075352742 |
| AP | +0,104790783 | +0,034849446 | +0,180798906 |
| Brier | −0,008557761 | −0,015113238 | −0,002237125 |
| Log loss | −0,033789599 | −0,055086188 | −0,013966178 |

Conditional comparison favors boosting versus calibrated logistic on these
metrics. It does not establish firm-independent/OOT or production superiority.
**Platt versus raw boosting improvement is uncertain:** Brier difference
−0,000428455, interval[−0,001320427,+0,000454289]; log-loss difference
−0,001699449, interval[−0,004024242,+0,000535925]. Those intervals include0.
Do not state Platt reliably improves boosting based on point scores alone.

`paired-replicates.parquet`:5.000 rows,1000×5×4 metric values. Verifier checks
draw/candidate identity, finite source predictions, saved interval quantiles and
paired deltas; out-of-range/mismatched draws or changed lineage invalidate it.
The earlier comparison attempt failed before completion due missing Arrow
import; retained separately, not counted as successful uncertainty evidence.

## 4. Authoritative champion freeze

Prefit rubric: lowest validation Brier, then log loss among Brier ties within
1e−6, then fixed simplicity order among log-loss ties within1e−6. ROC AUC/AP
không selection criteria. All five candidates are eligible, including constant.
Intervals are supporting evidence, not an added post-hoc selection gate.
Rubric selects **boosting_platt** from point scores; this does not change the
uncertain calibration-benefit interpretation above.

Freeze copies selected JSON model, Platt parameters, train encoder, protocol
and selection evidence. Digests pin assessment/comparison/features/study and
reviewed scoring methods. Original-source/horizon study registry now pins
one authoritative model-freeze ID and receipt digest; rerun same comparison
reuses freeze. Another comparison cannot silently reselect that study.
Copied model/encoder/calibration must equal selected development artifacts.

Freeze is not final-score consumption. **One-time final evaluation/consumption
ledger is still pending**, as are final uncertainty/model card and model-result
UI. Source-ratio app remains usable; these development results currently have
CLI/private artifacts and this document, not an added model page in the app.
Immutable intake/study/assessment receipts retain their original stage flags;
freeze receipt separately records champion_selected=true/final_test_scored=false.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/assess_bankruptcy.py --features bankruptcy-features-fc51ea164f93
.\.venv\Scripts\python.exe -X utf8 scripts/compare_bankruptcy.py --assessment bankruptcy-assessment-0e7cb5cc894d
.\.venv\Scripts\python.exe -X utf8 scripts/freeze_bankruptcy.py --comparison bankruptcy-comparison-e3ee221ca493
.\scripts\test.ps1
```

Assessment/comparison reruns create new immutable artifacts without changing
fixed protocol. Authoritative freeze remains bound to the comparison above;
do not use new run IDs to reset selection or later final consumption.
Full software suite: **662 tests PASS** (375 engine +287 application),92,89s.
23 added checks cover actual fitting/persistence/no-final access, reliability
boundaries, source-feature tampering even with updated digests, persisted model/
score disagreement, group resampling/paired identity, full comparison artifacts,
fixed-rubric tie rules and authoritative freeze reuse/changed model rejection.
Whole-suite status: [FIVE_WORKSPACES_STATUS.md](FIVE_WORKSPACES_STATUS.md).
No UI/server change this turn; previous ratio browser acceptance stays8 checks.
Full five-workspace scope remains open, including SEC/SME timing/memo/covenant/
debt work and other modules; one bankruptcy benchmark does not cover full P3.
