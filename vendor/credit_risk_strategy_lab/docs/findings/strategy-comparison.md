# Strategy comparison — no validated findings yet

B22 is PARTIAL. `src/crsl/policy/optimize.py` now implements a finite-menu,
validation-only Pareto primitive. It maximizes both principal and count retention
while minimizing observed event rate among selected loans. Equal candidates are
retained; no arbitrary tie-break selects a champion. Unsupported or infeasible
candidates remain in the output with explicit reasons.

The caller must supply a predeclared candidate menu and common maturity-aligned
cohort. Cohort fingerprint and denominators must match across candidates. A menu
hash is recorded, but this is not yet a persisted pre-outcome selection lock.
The current function checks supplied metadata; it does not independently verify
the source rows or prove that the caller did not inspect test data previously.
It rejects train/calibration/test partitions for selection.

The default minimum 50 selected events is an illustrative research support guard,
not a universal standard or statistical significance test. Zero-event or empty
selections cannot be promoted as proven superior. Constraints are never relaxed
automatically. A frontier is a trade-off set, not a robust improvement claim.

Only synthetic engineering tests have exercised this optimizer. No actual policy
frontier, optimized cutoff or out-of-time benefit is reported. The separate S0/S1
2012 replay remains descriptive; see the development policy card.

## Paired uncertainty implementation

`src/crsl/policy/uncertainty.py` now accepts one origination record per loan,
positive principal, fixed policy selections and a known 12-month D3 target.
Label availability must precede the evaluation cutoff; missing outcomes are
rejected rather than silently dropped or treated as negative. The caller must
document the common eligible, endpoint-available cohort and excluded population.

Both policies use the same sampled loan indexes and multiplicities in each
resample. Seed, resample count and confidence level are required explicit inputs;
the result records them and hashes the sorted comparison inputs. Reordering
inputs does not alter results. This is not yet a persisted settings freeze.

Reported deltas are candidate minus baseline for selected event rate, count
retention and original-principal retention. Intervals are percentile intervals
with linear interpolation. Undefined bootstrap draws are counted explicitly.
Intervals are suppressed if fewer than 95% of draws are defined; event-rate
intervals additionally require the configured event support in both selections.
Defaults are development settings, not institutional risk appetite.

This loan-level bootstrap conditions on fixed fitted models, policy rules and
the supplied cohort. It does not quantify model fitting uncertainty, common
macro/vintage shocks, policy-selection bias, causal effects, or simultaneous
uncertainty over multiple candidates. It is not applicable to repeated behavioral
loan-month observations without a separate cluster-aware protocol.

Synthetic tests verify exact zero paired deltas for identical policies, input
order invariance, missing/immature label rejection, event-support suppression and
undefined risk for empty selections. No actual risk-improvement interval has
been generated or claimed.

## Fixed-retention ranking

`src/crsl/policy/retention.py` implements count- or principal-based retention.
It ranks a fully scored, upstream-qualified cohort from lower to higher risk and
includes the complete boundary tie group. The requested fraction is a minimum,
not a guarantee of exact volume. Actual retention and overshoot are explicit.
No fractional loans or arbitrary loan-ID tie breaks are used. Missing scores
fail the call rather than disappearing from the denominator. Outcomes are never
read. Zero and full retention are supported explicitly.

This primitive does not validate model lineage, source availability or calibrated
PD. The caller must apply those gates and preserve/document the qualified cohort.
It must not silently shrink the cohort to scoreable loans. A fixed-retention rule
has a cohort-specific boundary score: that is different from a fixed absolute PD
cutoff. The target/basis/tie rule must be frozen before test evaluation; a new
cohort's score ranking may then be evaluated without using its outcomes.
Synthetic tests cover whole-tie overshoot, count versus principal denominators,
endpoint targets, ordering invariance and invalid/missing score rejection.

## Development protocol receipts

`src/crsl/policy/protocol.py` validates and exclusively creates a protocol receipt
containing the S0–S3 policy configuration, candidate IDs, allowed retention floors,
bootstrap settings, cutoff and code/model/split digests. An existing receipt is
never overwritten. Reading requires the externally retained receipt SHA256, so
editing the file and its internal hash does not pass against the original pin.

`compare_locked` checks supplied lineage digests and uses the frozen menu/support;
unplanned floors are refused. `bootstrap_locked` uses saved settings verbatim.
Receipts remain explicitly development-only. They are not signed approvals,
trusted timestamps, or proof that a user never looked at test outcomes. The
wrappers do not yet independently load and validate model/split source artifacts.
The receipt menu supports S0–S3 and explicitly named fixed-retention variants.
Each retention variant freezes its target, count/principal basis and whole-group
tie rule. IDs cannot collide with S0–S3 or another variant. `retention_locked`
applies those settings verbatim and records the receipt digest; unlisted variants
and alternative tie rules are refused. The same variants can enter the locked
frontier menu. Upstream model and score provenance still require integration.
No actual research protocol has been frozen using placeholder model hashes.

Remaining: source-integrated maturity-aligned comparison,
approved validation data and calibrated models, subgroup concentration,
one-shot final-OOT orchestration, public-safe policy table and reviewer UI.
