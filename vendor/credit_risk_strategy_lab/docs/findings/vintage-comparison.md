# B11 — Maturity-aligned vintage comparison

Status: PARTIAL; current data has one origination vintage. No cross-vintage winner.

## Reproduce the evidence

Run `python -m crsl.vintage --canonical-run artifacts/private/<canonical-run>`.
The explicit development horizons are 6, 12 and 24 months after first observation.
Run `python -m crsl.verify_vintage --run artifacts/private/<vintage-run>` to check
source identity membership at every horizon and independently multiply the
four-state transition matrices. `notebooks/02_vintage.ipynb` is the executable
analytical companion; execution saves real outputs privately.

The verified 2012 development run is `vintage-78feb345a476`. Its `summary.json`
contains cohort denominators, exclusions, risk sets, censoring, competing exits,
first-event counts, cumulative probabilities and bootstrap intervals. The separate
`vintage_stock.parquet` describes all reported loan stocks, not only eligible loans.

## Interpretation contract

The first numeric-D3 event, prepayment/maturity, and other exit compete. Other exits
are not relabeled as D3 or silently dropped. Follow-up stops before an unknown/gap;
later observations never repair first-event observability. Month-end event ties
follow the existing D3-priority contract. A loan contributes at most one endpoint.

Discrete Aalen–Johansen is computed from common at-risk sets. Without censoring,
it reduces to observed first-event count divided by the eligible population.
With censoring, its interpretation requires independent censoring; the observed
lower bound and unknown share remain visible. No prediction model is fitted here.

Cells are null if the entire eligible vintage/segment is not calendar-mature.
No extrapolation after the risk set is exhausted by censoring is allowed. A fully
absorbed event process may retain its terminal probabilities. Age is observation
age, not assumed contractual age; early-entry eligibility is inherited from B06.

Intervals are percentile 95% IID loan bootstrap with 500 replicates and seed 17.
Identical endpoint/time records are sampled using their exact loan counts. This
does not resample loan-months and does not capture common economic shocks or
source revisions. Fewer than ten observed events is flagged sparse. Zero/all-event
samples do not receive a misleading degenerate bootstrap interval.

## Decision and alternative explanation

Preserve separate Relief/non-Relief diagnostics when training becomes possible.
Observed segment separation may reflect selection into refinancing, portfolio mix,
and earlier borrower histories rather than any causal effect of the program.
The present sample cannot determine which origination year is worse. Do not infer
approval uplift or realized profitability from these descriptive curves.

## Remaining acceptance

- Qualify the additional vintages and compare them at common observation ages.
- Integrate the maturity-aware heatmap and denominator drill-down into the website.
- Complete the real-data publication/privacy review before distributing results.

Method reference: [survival package multi-state vignette](https://cran.r-project.org/web/packages/survival/vignettes/compete.pdf).
