# B00 — Approved project charter

The user approved implementation of the V4 mortgage plan on 2026-09-09.

## Decision
Within eligible, already-funded/acquired U.S. fixed-rate mortgages,
compare retrospective screening strategies on risk and retained count/principal,
then assess temporal stability and portfolio lifecycle behavior.

## Audience
Credit Risk / Portfolio Risk / Risk Analytics reviewers.
The project demonstrates SQL, data verification, label design, temporal validation,
decision strategy and communication. It does not establish consumer-credit production experience.

## Evidence and deliverables
| Capability | Evidence | Planned output |
|---|---|---|
| Source qualification | OBSERVED technical checks | B01–B03 provenance/profile |
| Loan-month lifecycle | DERIVED, after data gate | B04–B12 canonical/cohort/transitions |
| Risk models | MODELED, after label/split gate | B13–B18 cards and evaluations |
| Screening | DERIVED/MODELED | B21–B22 comparison, not approval |
| Forecast/stress | MODELED/SCENARIO | B20/B23 backtest and assumptions |
| UI/Excel | Same validated evidence | B27–B30 public-safe exports |
| Synthetic examples | SYNTHETIC only | Tests and explicit demonstrations |

## Removed from implementation
Application funnel, revolving activation, offer/limit response optimization,
pricing elasticity, actual lender P&L, cross-customer CLV, fraud/KYC enrichment,
causal treatment optimization, protected-group certification, regulatory capital engine.

## Research assumptions
No organization-specific risk appetite has been supplied.
Retention grids in the plan are research scenarios, not Freddie Mac policy.
Mortgage coefficients and outcomes must not be presented as Vietnamese unsecured lending evidence.

## Acceptance
Product/domain disclosed. Every supported capability has an evidence class.
Unsupported capabilities are excluded from the implementation backlog.

