# NSMO D02 — horizon support by origination vintage

Updated 2026-10-16. This is a descriptive extension of the D02-3/5 feasibility
screen using the verified NSMO v7.0 PUF. It answers how much C-state baseline
support remains at 6, 12 and 24 months for each `Open_Year`; it does not choose
or label a modeling target.

## How to read the table

Each cell is `C baseline snapshots / unique mortgages / observed 90+ snapshots /
M-or-S censor snapshots`. Baseline snapshots are repeated quarterly landmarks,
so they are not independent loans. The unique-mortgage count is the distinct
support represented in that vintage and horizon. The two event/censor counts
are snapshot outcome counts, not mortgage-level probabilities. M means an
archive gap and S means servicer-suppressed; both stop observation and neither
is a performing outcome. The public machine-readable table retains every
outcome category, including no observed 90+, termination, same-month ambiguity,
and adverse states 7–9.

| Origination year | 6 months | 12 months | 24 months |
|---|---:|---:|---:|
| 2013 | 150,742 / 6,030 / 137 / 422 | 148,248 / 6,030 / 345 / 788 | 142,875 / 6,030 / 722 / 1,376 |
| 2014 | 122,848 / 6,180 / 127 / 396 | 120,722 / 6,180 / 307 / 730 | 116,014 / 6,180 / 595 / 1,254 |
| 2015 | 125,435 / 6,121 / 101 / 440 | 122,697 / 6,121 / 258 / 849 | 116,828 / 6,121 / 468 / 1,562 |
| 2016 | 122,996 / 6,193 / 112 / 404 | 119,551 / 6,193 / 268 / 766 | 112,259 / 6,193 / 502 / 1,369 |
| 2017 | 84,097 / 5,105 / 105 / 390 | 81,484 / 5,105 / 243 / 746 | 75,893 / 5,105 / 405 / 1,378 |
| 2018 | 53,832 / 4,637 / 76 / 320 | 52,047 / 4,637 / 168 / 605 | 48,151 / 4,637 / 278 / 1,038 |
| 2019 | 51,892 / 4,931 / 48 / 334 | 48,957 / 4,931 / 106 / 522 | 42,744 / 4,931 / 193 / 662 |
| 2020 | 75,797 / 5,594 / 50 / 250 | 68,708 / 5,594 / 90 / 434 | 53,947 / 5,594 / 147 / 600 |
| 2021 | 70,078 / 5,327 / 65 / 185 | 61,129 / 5,327 / 125 / 320 | 42,448 / 5,327 / 179 / 402 |
| 2022 | 36,758 / 3,813 / 81 / 150 | 30,367 / 3,812 / 161 / 255 | 16,611 / 3,810 / 167 / 256 |
| 2023 | 22,581 / 3,844 / 49 / 102 | 16,158 / 3,844 / 84 / 152 | 2,487 / 1,773 / 27 / 40 |
| 2024 | 9,275 / 3,870 / 13 / 44 | 2,820 / 1,929 / 19 / 29 | Not available |

## Findings and implications for D02

- Horizon eligibility mechanically shrinks as the follow-up window lengthens.
  The 2024 vintage has 9,275 C baseline snapshots at 6 months, 2,820 at 12
  months, and no 24-month observations with full follow-up in this PUF. The
  2023 vintage retains 2,487 24-month snapshots, representing 1,773 mortgages.
- Older vintages have materially more repeated baseline snapshots because
  loans can contribute multiple quarterly C landmarks. For example, 2013 has
  150,742 six-month snapshots but 6,030 unique mortgages. Snapshot counts must
  not be used as a count of independent observations or standard errors.
- Observed 90+ snapshot counts rise as the observation window lengthens for
  most vintages because there are more chances to observe a transition. This is
  not evidence that a comparable 24-month PD is higher: horizon cohorts are
  different, quarterly snapshots miss within-quarter events, and the audit is
  unweighted and descriptive.
- M/S censor counts also rise with horizon for older cohorts, while recent
  vintages have shorter administrative support. The visible M/S count alone
  does not capture all censoring: close before the next snapshot, same-month
  ambiguity, and other unobserved status codes remain separate in the CSV,
  workbook, and app.
- The yearly partition reconciles to the PUF-wide horizon receipt for snapshot
  and unique-mortgage supports. The 24-month horizon has 11 years because 2024
  contributes no eligible baseline; 6 and 12 months each have 12 years.

## Modeling decision

Keep the current result at **target feasibility only**. Before modeling, D02-5
still needs an explicit estimand and index-time rule, treatment of competing
termination and same-month ambiguity, censoring/selection strategy, survey
design/variance decision, and predictor timing gate. D02-6 must then check
unique positive mortgages by vintage and split before a model is considered.
Repeated C landmarks need loan-clustered resampling/splitting if retained;
otherwise choose one prespecified landmark per loan and accept the narrower
effective sample. Do not infer a minimum sample from the large snapshot count.

## Artifacts and reproducibility

- Full aggregate-by-outcome export: `NSMO_HORIZON_SENSITIVITY_2026-10-16.csv`.
- Filterable Excel sheet: `apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx`,
  sheet `Do nhay horizon` (filter `Phạm vi` to `origination_year`).
- Interactive view: `/nsmo`, “Độ dài cửa sổ và support quan sát được”; the
  existing vintage filter applies to the new year-by-year table.
- Private receipt and PUF remain on D: and are bound by SHA-256; no loan IDs or
  row-level data are published.
- Re-run `scripts/audit_nsmo_horizon_sensitivity.py` against the verified PUF,
  then `scripts/export_nsmo_horizon_sensitivity.py` to regenerate only the
  aggregate CSV before rebuilding the workbook.
