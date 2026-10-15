# Observation and labels — development contract v1

## Time and eligibility

The current estimand is **first-observed early-entry D3 before prepayment**,
not contractual-origination default probability or regulatory default.
Landmark t is the first observed reporting month. Primary window is t+1 through
t+12 inclusive. First observation at source and contractual ages 0–1 is required,
with exact agreement; contractual age = reporting month minus first payment month +1.
Modified-at-entry, severe/REO-at-entry, unknown-at-entry and terminal-at-entry are excluded.
Relief Refinance loans remain flagged and separately reported, not silently discarded.

Eligibility uses entry-time information only. Future coverage controls whether the
outcome is known; it does not select the initial eligible population.
Config: `configs/cohort.json`; SQL: `observation.sql` and `labels.sql`.

## Outcome rules

- D3 observed in the window: positive only with contiguous, known states up to first event.
- Complete horizon without event: negative.
- Prepayment before event: negative under event-before-prepayment estimand, with competing flag.
- Other/credit terminal without numeric D3, or REO before numeric D3: other exit, no binary label.
- Unknown or gap before classification: unavailable. Unknown/gap after known D3 does not erase it.
- Incomplete history without classifiable event/exit: censored, never automatically negative.
- Same-month numeric D3 and exit: D3 priority at the source's monthly resolution.
  This is an explicit tie convention, not evidence of intramonth causal order.
- Repeated terminal rows or records after terminal fail for manual review.
- Label-known month is when evidence becomes observable in the latest-release reconstruction;
  it is NOT proof that this historical value was published then.

## Current measured 2012 results

Run `labels-ec5d5fb7b61a`:

- 50,000 starting loans = 48,066 eligible +1,919 not early-entry +15 terminal at entry.
- Eligible outcomes =45,241 complete no event +102 D3 +2,641 prepayment +82 other exits.
- Binary labels =47,882 negatives +102 positives; 2,016 unavailable/ineligible overall.
- These are not full-market estimates; a model is not approved by label availability.
- 89 of the 102 events occur in Relief Refinance loans; only 13 in the other group.
  This matters for feature-missingness confounding and sparse subgroup support.

Original-principal attrition reconciles in `summary.json`. Principal is rounded source
UPB, not exact transaction cash flow. Time-split research needs more vintage samples;
do not split monthly rows randomly to manufacture a larger independent training sample.

## Episode convention

Episodes are separate lifetime descriptors, not replacements for the fixed-window label.
One-month cure follows an observed D3 episode. Sustained cure is confirmed at the third
consecutive CURRENT nonterminal month; confirmation is never backdated.
Redefault means a subsequent D3 after confirmed sustained cure. Unknown/gaps interrupt
episode linkage. First-ever observed D3 never resets. Termination-current is not cure.
