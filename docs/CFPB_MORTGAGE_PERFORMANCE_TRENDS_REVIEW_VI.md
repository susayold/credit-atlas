# CFPB Mortgage Performance Trends — source review

Checkpoint: 2026-10-15. This is a supplemental geography/time-series source for
the mortgage research workspace. It is not a loan-level dataset and does not
change the D01 Freddie Mac sample, target, or model-data gates.

## Source and coverage

CFPB publishes two CSV tables, 30–89-day delinquency and 90+-day delinquency,
for states and counties. The current release covers January 2008 through
December 2025 and was published in August 2026. The files are wide: one row per
geography and 216 monthly percentage columns. The county files contain 507
county-equivalent records plus the national row; the state files contain 51
state/district records plus the national row. County and state FIPS codes are
retained as text so leading zeroes are not lost.

The four official CSVs were downloaded to private storage under
`data/private/public-context/cfpb-mortgage-performance-trends-2026-08/`.
Acquisition metadata, byte counts, SHA-256 hashes and profile checks are in its
`receipt.json`. Total download size is 1,012,455 bytes. All four files have the
expected 216 months and parse with zero blank or non-numeric observation cells.
Observed rate ranges are 0.0–11.3% for 30–89-day county records,
0.0–13.8% for 90+-day county records, 0.3–7.0% for 30–89-day state records,
and 0.2–10.7% for 90+-day state records. Values are stored as percentage
points in the source, not fractions.

Official downloads:

- [CFPB download page](https://www.consumerfinance.gov/data-research/mortgage-performance-trends/download-the-data/)
- [CFPB methodology and definitions](https://www.consumerfinance.gov/data-research/mortgage-performance-trends/about-the-data/)
- [County 30–89 days late CSV](https://files.consumerfinance.gov/data/mortgage-performance/downloads/CountyMortgagesPercent-30-89DaysLate-thru-2025-12.csv)
- [County 90+ days late CSV](https://files.consumerfinance.gov/data/mortgage-performance/downloads/CountyMortgagesPercent-90-plusDaysLate-thru-2025-12.csv)
- [State 30–89 days late CSV](https://files.consumerfinance.gov/data/mortgage-performance/downloads/StateMortgagesPercent-30-89DaysLate-thru-2025-12.csv)
- [State 90+ days late CSV](https://files.consumerfinance.gov/data/mortgage-performance/downloads/StateMortgagesPercent-90-plusDaysLate-thru-2025-12.csv)

## Meaning and limits

CFPB describes these rates as delinquent mortgage records divided by all
outstanding mortgages. The 30–89-day series is early-stage delinquency. The
90+-day series is serious delinquency excluding loans already in foreclosure.
CFPB suppresses counties, metros, and non-metro areas with fewer than 1,000
mortgages in the sample. This therefore is not complete county coverage and
does not have a county loan-count denominator suitable for reconstructing
precision or exposure.

The data derive from the FHFA/CFPB National Mortgage Database, the same
underlying sample family as the separate FHFA NMDB aggregate package already
shown in the app. It is a monthly, county/state representation of that context,
not an independent source or a second sample. CFPB states that reported-missing
performance may be imputed using past performance, absent reports are not
imputed, and historical rates can be revised as credit data are updated. Its
methodology warns that emergency-period servicing/forbearance reporting can
suppress delinquency rates. The latest published history is retrospective and
does not provide the original vintage for each value.

## Intended module use

Use as a separately attributed monthly geographic context series in Mortgage
Sources. Allow National, State, and available County selection; preserve the
source's percentage-point values and selected geography FIPS. Show both
delinquency definitions with their denominators and suppression caveats. Keep
this source separate from HUD tract exposure and from FHFA quarterly NMDB
performance; do not interpolate quarterly values or merge the three sources
into one time series. Do not join it to private Freddie loans, use it as a
loan-level predictor, infer local default probability, or count it as a new
loan-performance vintage.

## Verification record

- Official landing page says current data cover 2008-01–2025-12 and were
  published August 2026; older archives exclude later revisions.
- Official methodology confirms NMDB lineage, sample-based geographic
  aggregation, minimum 1,000 mortgages for shown county/metro areas,
  imputation/reporting caveats, and the two delinquency definitions.
- Four downloaded files passed header, row-count, 216-period, numeric-cell,
  and percentage-range profile checks. Hashes are preserved in the private
  receipt and are not published with loan-level or private data.
- Source is acquired for a contextual UI extension only. No D01 model gate or
  acceptance percentage changes as a result.
