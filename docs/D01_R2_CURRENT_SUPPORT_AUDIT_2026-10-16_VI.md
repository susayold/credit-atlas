# D01/R2 — current split and feature-support audit

**Checkpoint:** 16/10/2026. **Purpose:** re-run source/split readiness on the
current frozen Freddie 2012 case while additional annual vintages remain behind
Clarity authentication. This is a support/data audit, not protocol approval or
model training.

## Inputs and lineage

- Case: `d01-202610150931`; pipeline: `pipeline-307c354f3d74`.
- Source release contract: Release 47; only origination vintage present: 2012.
- Target: `d01-early-entry-d3-before-prepay-12m-v1`, first-observed 12-month D3
  event before prepaid/matured. It remains D3 event risk, not regulatory PD.
- Split config SHA-256:
  `1748a4ce517dd3e7e59dc9870ce5fc6d0770111c6c82193c111bf11a1912c0b6`.
- The config status is `candidate_not_approved_for_training`. Preparation logs
  access, rechecks lineage and never fits a risk model.

## Split support on the current source

| Role | Required origination vintages | Positive | Negative | Result |
|---|---|---:|---:|---|
| Train | 2006–2012 | 100 | 43,227 | 2012 contributes eligible loans; 2006–2011 absent |
| Calibration | 2014 | 0 | 0 | Required vintage absent |
| Validation | 2016 | 0 | 0 | Required vintage absent |
| Final test | 2018 | 0 | 0 | Required vintage absent; no test outcome was evaluated |

Across the 50,000 source labels, 4,657 train-role rows were excluded because
their outcome was not known before the 2014-01-01 train cutoff; another 2,016
had unavailable labels. The remaining train cohort is 43,327. The assignment
audit reports all missing required vintages: 2006–2011, 2014, 2016 and 2018.
The positive count of 100 is the entire observed train support under this
candidate protocol; it does not establish adequate model power or segment
support.

`PREPARED_NOT_FIT_READY` blockers are:

- `missing_required_vintages`
- `insufficient_class_support`
- `protocol_not_approved`
- `feature_contract_not_qualified`
- `study_not_frozen`

The zero calibration/validation/test counts are unavailable because those
cohorts are absent. They are not zero event rates. No random split or row-level
monthly split was substituted.

## Train-only feature availability

The separate train-only encoder audit covered 43,327 included train loans and
did not include final-test predictors. All configured features had at least one
known train value; saved encoder transform parity passed across all development
rows. Availability within this one cohort was:

| Feature | Known | Missing | Missing share |
|---|---:|---:|---:|
| Classic FICO | 43,327 | 0 | 0.00% |
| Original DTI | 27,569 | 15,758 | 36.37% |
| Original LTV | 43,325 | 2 | 0.005% |
| Original CLTV | 43,325 | 2 | 0.005% |
| Original UPB | 43,327 | 0 | 0.00% |
| Original term | 43,327 | 0 | 0.00% |
| Dwelling units | 43,265 | 62 | 0.14% |
| Occupancy, purpose, property type, first-time-homebuyer | 43,327 each | 0 each | 0.00% |

These are measured missingness counts, not imputations. The encoder's missing
indicators and imputation are engineering behavior only; the feature contract,
missingness reason, vintage stability and use eligibility still require review
before any fit. No absent values were projected or filled during this audit.

## Reproduction commands and private receipts

Run from the public checkout with its `src` on `PYTHONPATH`:

```powershell
$env:PYTHONPATH='D:\data\Codex\credit-atlas-public\src'
python -m credit_atlas.cli --root D:\data\Codex\credit-atlas prepare-study --case d01-202610150931
python -m credit_atlas.cli --root D:\data\Codex\credit-atlas prepare-features --study study-b71a0d76e11d
```

Private receipts (do not publish the underlying loan rows):

- `D:\data\Codex\credit-atlas\artifacts\private\study-b71a0d76e11d\study-complete.json`
- `D:\data\Codex\credit-atlas\artifacts\private\study-b71a0d76e11d\split-audit.json`
- `D:\data\Codex\credit-atlas\artifacts\private\feature-audit-bbe0ad46de92\feature-coverage.json`
- `D:\data\Codex\credit-atlas\artifacts\private\feature-audit-bbe0ad46de92\feature-complete.json`

## Decision and next data action

This confirms that the 2012 sample cannot support the planned train/calibration/
validation/OOT study by itself. Keep R2/R3 open. First acquire an authorized
Freddie annual sample pilot (the plan names 2008 as a candidate train pilot),
then audit release/schema, IDs, maturity, labels, feature availability and
resource footprint before registering it. Do not fit after only a pilot. Next
acquire the remaining predeclared role vintages and re-check event support and
uncertainty before approving any protocol revision. If support fails, report
that result rather than weakening cutoffs or substituting random splits.

Freddie's official page says yearly sample downloads are through Clarity
registration/sign-in and performance is published through 31/03/2026:
[SFLLD access and coverage](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset).
The current unauthenticated endpoint probe returned HTTP 403; details are in
[`D01_GINNIE_ACQUISITION_PREFLIGHT_2026-10-16_VI.md`](D01_GINNIE_ACQUISITION_PREFLIGHT_2026-10-16_VI.md).
