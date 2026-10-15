# Resolved loss research card

`crsl.losses.summarize` produces an aggregate descriptive loss bridge from a
hash-checked audit table. It is intentionally conservative: one earliest loss
terminal row per loan, source signs preserved, no imputation for missing
components, no clipping, and separate unresolved/partial-coverage counts.

The default severity denominator is `removal_upb`. The resulting amount and
severity are observed source diagnostics, not an LGD model. The B18 fit gate
requires support and coverage review, a compatible endpoint with the risk
label, and temporal evaluation. The current one-vintage 2012 source does not
pass that gate, so `expected_loss_dollars` remains unavailable.
