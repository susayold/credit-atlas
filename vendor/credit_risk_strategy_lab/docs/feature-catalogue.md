# Origination baseline feature contract v1

This is a tested preprocessing component, not a fitted or approved real-data model.
Source: canonical Release47 origination table. Source publication may revise values;
historical archival availability is not verified.

## Included features

Numeric: Classic FICO, original DTI, original LTV, original CLTV, original UPB,
original term and dwelling units. Each receives a missing indicator. Median imputation,
mean and population-standard-deviation scaling are learned on included train rows only.
An entirely missing training field is flagged, imputed zero and given unit scale; this
prevents undefined preprocessing, but model validation must remove/ablate unsupported fields.

Categorical: occupancy, loan purpose, property type, first-time-homebuyer indicator.
Vocabulary comes only from train, with separate missing and unseen buckets.
Reserved bucket names cannot collide with literal source values.

No fitted state changes during transform. Column ordering is saved in `feature_names`.
Missing input columns fail; extra columns are ignored rather than auto-selected.
Nonfinite numbers fail. The encoder expects canonical nulls, not raw sentinel values.

## Excluded from this baseline

Current delinquency, balance, rate, modifications, assistance, ELTV, servicer, terminal
codes, actual loss, target and label time are never predictor inputs.
Loan IDs and private geography are also not model inputs.

Seller/channel: involvement and disclosure timing require separate availability review.
Original rate: pricing/endogeneity may dominate an origination-feature interpretation.
Borrowers: pre-2018Q2 category2 means >1 rather than exactly2; not treated as a numeric count.
Valuation method and VantageScore: no usable coverage in the current vintage.
Relief/HARP flags: retained for diagnostics, not included as baseline shortcut; a separately
specified ablation may be justified once vintage and feature availability are reviewed.

Config: `configs/features_origination.json`. Code: `src/crsl/features.py`.
The strict code-level allowlist prevents a config edit from silently admitting future fields.
The encoded vectors are not themselves evidence of model discrimination, calibration or utility.
