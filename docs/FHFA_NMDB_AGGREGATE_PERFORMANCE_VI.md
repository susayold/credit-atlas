# FHFA NMDB aggregate mortgage-performance context

Checkpoint: 2026-10-15. This note documents a public, aggregate source added to
D01's source-quality workspace. It is contextual evidence only; it does not
change the mortgage study's frozen population, target, vintages, or model gates.

## What was acquired

The official FHFA page lists a quarterly “all geographic areas” performance
archive released 30 September 2026. The ZIP was downloaded directly over HTTPS
from FHFA without credentials, cookies, or a session. The source file contains
261,856 rows and 13 fields, covering 98 quarters from 2002Q1 through 2026Q2.
It contains four series, four mortgage-market categories, and six geography
levels: National, Rural/Non-Rural, Census Region, Census Division, State, and
Metro. The 261,856 source keys are unique. The source marks 764 rows suppressed;
48,028 VALUE1 cells are blank or `.` across the full geographic file.

The national / United States / All Mortgages slice is rendered separately from
the Freddie loan-level sample. It includes four series:

| Source series | Display label | Interpretation |
|---|---|---|
| `P3089DL` | 30–89 days delinquent | Active-mortgage share in this quarter-end performance state |
| `P90DL` | 90+ days delinquent | Active-mortgage share 90 or more days past due at quarter end |
| `PFORECL` | Foreclosure / bankruptcy / deed-in-lieu | Active-mortgage share in the reported in-process category |
| `PFORB` | Forbearance | Separate forbearance share, published from 2019Q4 |

FHFA says the three delinquency/foreclosure performance states are mutually
exclusive and measured in the last month of each quarter. Its technical notes
say the performance rates cover active loans from the quarter after origination
through the quarter before termination. A separate forbearance series begins in
2019Q4. FHFA statistics are weighted estimates from the NMDB's 5% sample, not
unweighted counts from the dataset. The national slice is not a count or rate
for the Freddie supplied 2012 sample.

Selected national / All Mortgages observations, in source-reported percent:

| Quarter | 30–89 DPD | 90+ DPD | Forbearance | Foreclosure / bankruptcy / deed-in-lieu |
|---|---:|---:|---:|---:|
| 2002Q1 | 2.3% | 0.6% | Unavailable | 1.5% |
| 2010Q1 | 3.4% | 4.6% | Unavailable | 3.2% |
| 2019Q4 | 2.2% | 0.9% | 0.5% | 0.3% |
| 2020Q2 | 0.9% | 0.6% | 4.5% | 0.3% |
| 2022Q4 | 1.4% | 0.5% | 0.7% | 0.1% |
| 2025Q4 | 2.2% | 1.0% | 0.4% | 0.1% |
| 2026Q2 | 1.7% | 1.0% | 0.5% | 0.2% |

These are descriptive source observations, not estimates of the D01 target. FHFA
quarter-end states, active-loan denominator, NMDB sample design, and latest
revised aggregate vintage differ from Freddie's monthly loan-level target and
historical extraction. The app does not join the sources, fit with these values,
or claim external model validation.

## Integrity and application behavior

Acquisition/profile implementation: [acquire_fhfa_nmdb_performance.py](../scripts/acquire_fhfa_nmdb_performance.py).
The script checks the official host/status, a 128 MiB transfer bound, exact
single-member ZIP shape, exact CSV headers, quarter/year consistency, source
frequency, numeric fields, suppression flags, duplicate source keys, and complete
national series coverage. It writes an acquisition receipt, raw ZIP, profile,
and hashes under `data/private/public-context/` on D:. The D01 Source & Quality
page now renders separate charts for the three performance categories and
forbearance, plus source release, coverage, suppression, and hash evidence. A
standalone JSON export includes the 98-quarter national series and source hashes;
failed export requests surface an error without triggering an empty download.

The first implementation attempt correctly rejected the publisher's actual
13-column schema after an initial 14-column assumption; no data were interpreted
under that failed schema. The parser was corrected against the file and the final
profile is the successful receipt below.

Latest successful acquisition:

- Latest end-to-end receipt: `data/private/public-context/fhfa-nmdb-performance-e287056bb7cf/receipt.json`
- Raw ZIP SHA-256: `f13c2b3a09b3c4318d43bcf2ba1fcc1e79f9b9c5a1c5ac2f49553dc377787dca`
- CSV SHA-256: `e9a4181a75779dce90f933a2ed8fdf8b0bec24f83ba37d2c2a752184cb69a1da`
- Rows / columns / unique keys: 261,856 / 13 / 261,856
- National time series: 98 quarters, 2002Q1–2026Q2
- Verification: acquisition profile tests 4/4 pass; latest D01 browser acceptance 51/51 pass, including aggregate charts, source caveats, JSON export/hash verification, and export-failure handling; local full-data suite 1,581/1,581 pass; public source-only suite 1,432 passed, with 196 tests skipped because their private data or machine-local evidence is excluded.

The page and source metadata use the official [NMDB aggregate statistics page](https://www.fhfa.gov/data/nmdb)
and the [FHFA data dictionary and technical notes dated 26 June 2026](https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes-2026q1.pdf).
