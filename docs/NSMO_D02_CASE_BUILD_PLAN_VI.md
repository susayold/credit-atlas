# D02 — NSMO mortgage-performance workspace

Updated: 2026-10-15. D02 is a separate FHFA/CFPB National Survey of Mortgage
Originations (NSMO) case. It does not use, extend, or relabel the Freddie Mac
D01 panel.

## What is ready

- FHFA v7.0 PUF (page updated 2026-05-27) was downloaded after the user
  authorized the Notice of Monitoring and NMDB Terms acknowledgement.
- The ZIP, CSV and detailed receipts are held in a private local store outside
  the public repository. Only aggregate, non-identifying profile evidence is
  described here.
- 62,359 sample mortgages, 587 columns, 2013–2024 origination years, 51
  quarterly `perf_status_MMYY` columns from 2013Q1 to 2025Q3, 3,180,309 status
  cells, unique nonblank `nsmoid`, no malformed rows, valid positive
  `analysis_weight`, and no unknown performance codes.
- Codebook-grounded streaming parser accepts the lowercase headers in the
  publisher file. Focused tests and a full-file parser pass are complete.

## Build stages

| Stage | Work | Exit evidence | State |
|---|---|---|---|
| D02-0 — access and storage | Review FHFA gate/terms, download official v7.0, preserve source hashes, keep PUF private | Official URL, release, ZIP/CSV hashes, user authorization record, no secrets | Complete |
| D02-1 — structural profile | Check schema, keys, row widths, vintages, quarterly fields, weight domains and code domain | Aggregate-only audit receipt; parser reconciles the actual PUF | Complete |
| D02-2 — codebook reconciliation | Map every physical field to the 322 survey and 265 supplemental entries; distinguish wave variants, as-of timing, termination/forbearance/MTM-LTV and score series | Versioned source dictionary with unavailable, retrospective and non-comparable fields flagged | Next |
| D02-3 — state and observation-risk audit | Produce per-quarter weighted/unweighted status distributions, transition counts, entry/exit and censoring profiles; reconcile `A/B/K/M/P/Q/S` semantics to FHFA documentation | Reconciled state matrix with denominators and a documented choice of valid observed risk set | Not started |
| D02-4 — descriptive workspace | Add a separate UI/API with cohort, survey wave, borrower/mortgage mix, credit-score availability, delinquency-state snapshots, forbearance and termination views | Browser/API acceptance; every metric shows grain, numerator, denominator, weights and source caveat; no IDs | Initial separate page/API implemented; full metric coverage and acceptance pending |
| D02-5 — target protocol | Decide whether the evidence supports a quarterly snapshot outcome or an observed first-entry endpoint; specify horizon, event, competing termination, censoring, missing/suppressed rules and weight/variance method | Signed/frozen target and evaluation protocol before outcome-driven analysis | Not started |
| D02-6 — model study | Only if target support and temporal cohorts are adequate; use time-separated train/calibration/validation/test and report weighted plus unweighted diagnostics | Reproducible model card, calibration/threshold review and source-specific limitations | Not started |

## Intended metrics and guardrails

The initial app should be descriptive, not decisioning. It can show mortgage
origination mix and field coverage; unweighted counts alongside design-adjusted
weighted totals; quarterly status composition; observed 30+/60+/90+ state counts;
forbearance; termination; and transitions only where the previous and current
states are eligible observations. Every view must separate actual delinquency
codes from non-observation/administrative states. The weight sum itself is not a
loan count or a PD; weighted cell totals are not incidence estimates.

Do not use retrospective survey answers, future-quarter VantageScore, future
forbearance, or mark-to-market LTV as origination predictors. Do not infer that a
loan is performing from blank, history-ended, not-yet-reported, archive-gap,
pre-open or suppressed statuses. A quarterly snapshot does not reveal exact
event dates and may miss delinquency between reporting dates. No target is
defined in the current build.

## Public-release and citation rules

Only source code, synthetic tests and sanitized technical documentation may be
committed. Never commit the PUF, identifiers, row-level exports, screenshots,
or private receipts. The FHFA Terms prohibit attempts to identify individuals
and require a caveat that post-download analysis is the users'/authors' own and
is not attested to by FHFA. Do not use FHFA/NMDB marks to imply endorsement. If
the data are cited, include the exact FHFA-required disclaimer in the report:

> The opinions and analyses contained herein are solely of the users/authors of any data analyses or papers, and the FHFA cannot and does not attest to nor vouch for the quality, accuracy, or timeliness of the data, or analyses derived from these data after the data has been retrieved from FHFA.gov.

## Source

- [FHFA NSMO PUF and release information](https://www.fhfa.gov/data/nsmo)
- [Official Notice of Monitoring and Terms gate](https://www.fhfa.gov/data/nsmo/puf)
- [May 2026 codebook and unweighted tabulations](https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-c-v70.pdf)
- [May 2026 technical report](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf)
- Detailed review: `D01_NSMO_SOURCE_REVIEW_VI.md`
