# Actual public mortgage context acquisition — 2026-10-09

Downloaded through HTTPS using native curl, without credentials or computer use.
Receipt: `data/private/public-context/fred-c8f88c10f8c7/run-complete.json`.
The three source CSVs, native-frequency Parquet, monthly context and saved
SHA-256 digests remain in that private directory. All output hashes verified.

| Series | Source | Frequency | Actual observations | Last reference date |
|---|---|---|---:|---|
| UNRATE | BLS via FRED | Monthly, seasonally adjusted, percent | 945 | 2026-09-01 |
| USSTHPI | FHFA via FRED | Quarterly, not adjusted, 1980 Q1=100 | 206 | 2026-04-01 |
| MORTGAGE30US | Freddie Mac via FRED | Weekly, not adjusted, percent | 2,898 | 2026-10-08 |

Metadata and citation sources:
- https://fred.stlouisfed.org/series/UNRATE
- https://fred.stlouisfed.org/series/USSTHPI
- https://fred.stlouisfed.org/series/MORTGAGE30US

## Completed context run

The frozen case `d01-a24484b21a21` contains 171 reporting months from January
2012 through March 2026. The context run produces 171 rows: unemployment is
available for 170 months and weekly mortgage-rate monthly means for all 171.
The unavailable unemployment value for October 2025 remains null. The housing-price index
stays quarterly, with 57 native quarter observations in the case date range;
there is no invented monthly interpolation.

These are latest revised snapshots. Reference dates do not establish when an
observation became available to a historical prediction. This run is descriptive
and retrospective, not a qualified point-in-time feature pipeline. PMMS changed
methodology on 2022-11-17. The mortgage monthly mean uses source weekly dates
inside each reporting month and records its observation count.

## Remaining loan-data dependency

No additional annual loan vintage was downloaded. Only the existing actual
2012 annual sample is available; no mortgage risk model was fitted. Macro series
cannot replace borrower-level origination and monthly performance labels.
Freddie Mac directs download users to register and sign in to Clarity:
https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset

The user confirmed no login session exists. Once an authorized session and
annual-sample URLs are available locally, the existing HTTP downloader can
acquire and verify the ZIPs; source registration, rebuild and temporal-study
qualification must then run before fitting.

## Re-run

From `D:\data\Codex\credit-atlas`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/acquire_public_mortgage_context.py
```

Each attempt creates a new private directory and preserves its success or
failure receipt. Two earlier Python HTTP attempts timed out; they are retained
as failed attempts rather than presented as successful downloads. Native curl
completed the actual successful acquisition. Failed downloads are not used.

## Refresh — 2026-10-16

Re-fetched the three official FRED CSVs without credentials. The verified run is
`data/private/public-context/fred-11216f1a2e33/run-complete.json`: 4,050 native
observations and 171 case-aligned months. `MORTGAGE30US` now has 2,899 weekly
observations through 2026-10-15 (one more than the 2026-10-08 snapshot);
`UNRATE` remains through 2026-09-01 and quarterly `USSTHPI` through
2026-04-01. SHA-256 checks are recorded in the private run receipt.

The local D01 **Sources** view now serves verified latest values and the
case-aligned 2012-01–2026-03 monthly series through `/api/mortgage-macro-context`.
It shows unemployment, the within-month mean of native weekly mortgage-rate
observations, and HPI at its native quarterly grain. The API verifies all
receipt output hashes and does not silently fall back to an older successful
run if the newest run is corrupt. These are latest-revised retrospective
context, not historical point-in-time predictors, and they do not add a loan
performance vintage or open the D01 model gate.

## ALFRED month-end snapshots — 2026-10-16

The same three series were downloaded from the official [ALFRED download
form](https://alfred.stlouisfed.org/help/downloaddata), selecting “Observations
by Vintage Date, All Observations” and zipped CSV. The verified acquisition is
`data/private/public-context/alfred-asof-20261015T235942Z/manifest.json` in the
private workspace. It contains 41 ZIP files and 399 vintage columns across
UNRATE (170), USSTHPI (58), and MORTGAGE30US (171). Each batch is CRC-checked and
has a SHA-256 digest. A 12-month lookback is retained so the first D01 month can
use previously released unemployment and HPI observations.

For every D01 month from 2012-01 through 2026-03, the adapter chooses the latest
actual ALFRED vintage date on or before that month's calendar end. The private
API returns 171 monthly rows with complete availability for all three measures:
UNRATE latest-known observation, the average of mortgage-rate weekly
observations within the month that were present in the selected vintage, and
the latest FHFA HPI quarter already published by the cutoff. The HPI remains
quarterly; there is no interpolation. Raw zipped source exports and receipts
remain private; only acquisition/verification code and aggregate UI outputs are
in the public project.

The Sources view labels this as point-in-time *context*, not as a model feature.
A month-end cutoff can occur after an underwriting decision or a target event;
the actual feature cutoff must be set to the decision's information date before
training. ALFRED context adds neither Freddie loan-level history nor default
labels, so it does not satisfy the missing annual-vintage or model-validation
requirements. The two public series sources are [UNRATE](https://alfred.stlouisfed.org/series/downloaddata?seid=UNRATE),
[FHFA US house price index](https://alfred.stlouisfed.org/series/downloaddata?seid=USSTHPI),
and [Freddie Mac 30-year mortgage rate](https://alfred.stlouisfed.org/series/downloaddata?seid=MORTGAGE30US).

Re-run from the private workspace root:

```powershell
.\.venv\Scripts\python.exe -X utf8 ..\credit-atlas-public\scripts\acquire_alfred_monthly_vintages.py --root . --headless
```
