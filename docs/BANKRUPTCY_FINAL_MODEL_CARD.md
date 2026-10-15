# P3 — One-year Polish bankruptcy benchmark: final research model card

09/10/2026. **Frozen boosting + Platt calibration** evaluated once on the
reserved random cohort. Final591 source financial statements/41 label=1:
ROC AUC **0,962793792**, AP **0,863689087**, Brier **0,021610995**,
log loss **0,087159890**. Consumption ledger **completed**.
This is a historical bankruptcy research benchmark; entity-disjoint/OOT and
production loan-default qualification remain unproven.

## 1. Intended use, target and source

Purpose: reproduce and compare historical financial-statement classifiers for
the UCI365 **one-year source bankruptcy label**, retaining source ratio
definitions, missingness/precision evidence and exact duplicate records.
Intended users: credit-risk researchers reviewing this bounded benchmark.
Not yet supported: operational loan approvals/limits/pricing, Vietnam SME PD,
Basel/IFRS9 default risk, accounting ECL, issuer-specific credit decisions or
case-level deployment on newly submitted financial statements.

Source: [UCI Polish Companies Bankruptcy](https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data),
Tomczak (2016), DOI10.24432/C5F600, CC BY4.0. Canonical ratios use the original
official ARFF ZIP, not the less precise CSV mirror. Combined source43.405
statements includes five horizons. This model uses **source subset5 = forecast
1 year**,5.910 statements/410 positives; no pooling of horizon targets.
Historical bankrupt/operating populations have different source collection
periods; no released firm identifiers or per-statement publication dates.
Source class fractions are not representative deployed lending PD calibration.

Canonical case `bankruptcy-case-e1e67482a2b4`; original reference
`polish-reference-0fcebfb0f6ff`; source batch `suite-619b1ee9aa8c`.
The global2.092 CSV/ARFF rounding differences remain auditable; subset5 has0
such differences. Financial features preserve signed/extreme ratios and NULL.
Source A29 log base/A55 currency-unit remain unspecified; A48/A49 EBITDA
wording remains literal. Predictor point-in-time availability is not established
for every ratio; no underwriting-time leakage-free claim is made.

## 2. Protocol, cohorts and training

Frozen study `bankruptcy-study-e0c65ad465e3`; exact numeric64-feature groups
ranked deterministically within source-label strata. Identical feature rows
kept together, all duplicate records retained, no relabel/dedup.
No exact group crosses partitions. Groups are not identified firms; near-
duplicates and repeated-company observations cannot be ruled out.

| Role | Statements | Label=1 | Label=0 | Exact groups |
|---|---:|---:|---:|---:|
| Train | 3.546 | 246 | 3.300 | 3.516 |
| Calibration | 886 | 61 | 825 | 870 |
| Validation | 887 | 62 | 825 | 879 |
| Final | 591 | 41 | 550 | 585 |

Model settings and selection rubric froze after source quality inspection,
before fitting/validation metrics. Train-only median imputation, signedasinh,
train mean/population std,64 fixed missing indicators:128 dimensions.
Preprocessing preparation only materialized5.319 development rows; final
encoding happened later after the one-time access claim. Encoder.fit was not
called during final evaluation. IDs, partition/group fields, label and horizon
codes are not predictors.

Fixed histogram booster: learning_rate0,05,120 iterations,15 leaves,
min_samples_leaf30,L2=1,random_state365,early_stopping=false. Train only;
no internal validation/class weights or hyperparameter search. Platt logistic
C1 fitted on calibration raw clipped logits,epsilon1e−12; no final refit.
Frozen Platt slope1,0483837984285598,intercept0,31232135785996823.
Native↔JSON model/calibration prediction parity: max difference0,0 on5.319
development rows. Separate SQL preprocessing audit max difference9,5923e−14.

Candidates: constant raw,logistic raw/logistic Platt,boosting raw/boosting Platt.
Prefit criterion: lowest validation Brier; among ties within1e−6,lowest log
loss; then fixed simplicity order. ROC AUC/AP and final metrics do not select
the model. **boosting_platt** selected from validation point metrics. Paired
validation bootstrap supports boosting versus logistic; raw↔Platt boosting
improvement intervals include0 and are not established as reliable benefits.

## 3. One-time final result and uncertainty

Assessment `bankruptcy-assessment-0e7cb5cc894d`; validation comparison
`bankruptcy-comparison-e3ee221ca493`; authoritative frozen bundle
**`bankruptcy-freeze-cebc982ca176`**. Final evaluation
**`bankruptcy-holdout-907870affe8d`**. No candidate substitution, calibration
refit, feature selection or threshold tuning occurred after final access.

| Metric | Validation point | Final point | Final 95% lower | Final 95% upper |
|---|---:|---:|---:|---:|
| ROC AUC | 0,967917889 | **0,962793792** | 0,927075734 | 0,992538961 |
| Average precision | 0,864015573 | **0,863689087** | 0,767904051 | 0,944703908 |
| Brier | 0,021898554 | **0,021610995** | 0,013305367 | 0,031387043 |
| Log loss | 0,085251500 | **0,087159890** | 0,055798627 | 0,120665964 |

Final uncertainties:1000 unstratified exact-group bootstrap draws,seed3652,
95% percentile intervals,settings set before final predictor query. Every draw
resamples585 groups and keeps every selected group's source-record weight;
draw rows585–600,0 single-class exclusions. These are conditional on the
fixed model/observed exact groups, not retraining uncertainty or independent
firm/country/calendar-period inference. Only41 positives contribute; intervals
do not resolve sampling bias or unknown repeated-firm dependence.

All final metrics use the same591 statements. AP is average_precision, not
trapezoidal PR area. Reliability bins have explicit statement/event support;
empty bin statistics=NULL. Scores include only the chosen frozen candidate;
no other final candidate was scored for retrospective model comparison.
No economic cost assumptions, approval threshold or profitability claim is
inferred from these metrics.

## 4. Consumption ledger and read-only review

`private evidence omitted from public release` records original-source
ZIP/horizon lineage,study/freeze IDs,freeze digest,evaluation ID and status.
Atomic primary-key claim precedes the final predictor query. A failed claimed
evaluation remains consumed; no automatic retry/reset/new-case substitution.
The current row points to907870affe8d and status=**completed**.

Saved final scores,metrics,bootstrap draws/settings and run verification have
immutable digests. Verification checks frozen lineage/ledger and reconciles
metrics/intervals from **saved scores/draws**,not final predictor transformation
or rescoring. It can revalidate source file integrity and frozen partitions;
that is separate from calling inference on final predictors.
Frozen protocol/assessment/freezer receipts preserve their stage-time
final_test_scored=false flags; final evaluation receipt records true.

```powershell
# Read/verify the already consumed result; no final predictor scoring:
.\.venv\Scripts\python.exe -X utf8 scripts/evaluate_bankruptcy_final.py --evaluation bankruptcy-holdout-907870affe8d

# This one-time scoring request is now rejected by the ledger:
# .\.venv\Scripts\python.exe -X utf8 scripts/evaluate_bankruptcy_final.py --freeze bankruptcy-freeze-cebc982ca176
```

All raw data,source ordinals/group IDs,score artifacts and receipts remain in
private ignored D: directories. No external publication approval. Dataset
attribution requirements still apply. Nothing is deployed for lending decisions.

## 5. Limits, pending app work and next research

Source uses financial statements,not unique identified borrowers/loans.
Historical sample selection,unverified predictor publication time,unknown firm
overlap,undefined units/formula wording and absence of source industry/country
deployment cohorts restrict interpretation. No subgroup fairness,industry
stability,monitoring drift,economic policy or causal explanation assessment is
claimed. Ratios/classifier probabilities do not supply debt schedules,covenants,
cash/recovery/default-time paths or regulatory staging.

Source-ratio UI and the [model evidence app](BANKRUPTCY_MODEL_APP_WORKFLOW.md)
now show verified separate validation/final results, uncertainty, support and
private aggregate export. Views read saved evidence; no final inference.
Findings/review workflow remains to integrate. Other horizons need their own prefit study and
appropriate validation,not selecting the best-looking horizon after this final
result. New model development cannot silently reuse this consumed final cohort.
SEC issuer financials/memos,SME outcome timing/covenant/debt workflows and all
other module acceptance remain in the full suite plan.

Verification evidence: five new checks cover frozen codec/null/signedextreme
parity,no final fitting,concurrent atomic claim,failed consumption,replay
rejection,read-only saved verification and altered score rejection. Actual
saved-score/ledger verification PASS. Full software suite **667 tests PASS**
(375 engine +292 application),117,58s. Whole-suite status:
[FIVE_WORKSPACES_STATUS.md](FIVE_WORKSPACES_STATUS.md).

Earlier workflow detail:
Latest app checkpoint: **675 software tests PASS**, 8 actual-source browser
checks PASS (`bankruptcy-model-browser-qa-47386fc6e30b`), mobile/desktop/export
verified with final transform/predict disabled and ledger unchanged.
[Model app workflow](BANKRUPTCY_MODEL_APP_WORKFLOW.md).

[protocol/features](BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md),
[development validation/freeze](BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md),
[source/ratio contract](BANKRUPTCY_RATIO_WORKFLOW.md).
