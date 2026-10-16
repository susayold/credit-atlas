# FHFA Enterprise PUDB — credit-access/acquisition source review

**Checkpoint:** 2026-10-15. **Source release:** 2025 Enterprise acquisitions,
published 2026-09-24. **Purpose:** a separate credit-access and acquisition-mix
track in CreditAtlas; this is not a D01 mortgage-performance extension.

## Source acquired and verified

Downloaded the official 2025 Single-Family Census Tract File, data dictionary,
and record-count workbook from FHFA over HTTPS, without credentials or cookies.
The ZIP is 108,870,000 bytes. It contains exactly one CSV with 2,093,767 rows
and 66 unique columns. Streaming verification found 2,093,767 distinct source
record numbers, zero duplicate keys, zero malformed-width rows, one acquisition
year (2025), and 2020 census geography. The Enterprise counts match FHFA's
published workbook exactly:

| Enterprise | Records |
|---|---:|
| Fannie Mae | 987,450 |
| Freddie Mac | 1,106,317 |
| Total | 2,093,767 |

The ZIP SHA-256 is
`a4ec41faf9a89624e4b4c77c0246c8e3962234403b633be34fe91fb636e6af52`. The
dictionary SHA-256 is
`6259b7506efce08752adcea7dcd01ac5af17d9628ed5730ef9b97be4e591beeb`; the
record-count workbook SHA-256 is
`c3707e7ab0ad055e495caa0004557d93c4039a6efdf53b77f157050a059edf8f`. The
latest aggregate-only profile is recorded in the local-private receipt
`receipt-v4-a4ec41faf9a8.json` (profile hash prefix `f7b65acb0795`). It records
blank counts for all 66 fields, including explicit zero counts. Field-level counts
and the detailed profile remain private; no full profile hash or private data
path is published.

## What it contains and what it supports

The Census Tract File is a mortgage-level record of Enterprise acquisitions,
with a sequential source record number, acquisition/census years, Enterprise,
state/CBSA/county/tract fields, acquisition UPB, purpose, federal guarantee,
borrower income and income-to-area-median ratios, borrower/co-borrower race,
ethnicity, sex and age bands, occupancy, lien status, LTV, term, origination
rate/UPB, preapproval, channel, AUS, credit-score model family, DTI category,
and selected tract opportunity/rural/persistent-poverty flags. The 2025
dictionary defines the 2025 release's changed schemas and value codes.

It can support descriptive work on the composition of mortgages purchased by
Fannie Mae and Freddie Mac in calendar 2025: purpose, borrower/tract
characteristics, DTI bands, credit-score model usage, acquisition balance
categories and geographic concentration. This can form a distinct **credit
access/acquisition-mix** workspace, using single-dimension counts, explicit
missing categories, and small-count suppression.

## Hard limits

- This is not an application-level census. It contains acquired/purchased
  mortgages, not the full applicant, approval, or denial population. It cannot
  by itself test approval fairness, disparate treatment, or causal effects.
- It contains no monthly payment history, delinquency transitions, default,
  foreclosure, prepayment, realized loss, or recovery outcome. It cannot train
  or validate PD, cure, severity, or loss models.
- The sequential record number is local to this file and is explicitly not
  related to identifiers in FHFA's other National Files. Do not join it to
  Freddie/Fannie servicing, HMDA, or another loan-level panel to invent
  performance outcomes or identify a person.
- This one acquisition year cannot establish a historical credit-access trend.
  Historical annual releases have their own schema, geography and code changes
  and must be acquired with matching dictionaries before any comparison.
- This file is not the D01 2012 Freddie performance sample. It does not add a
  Freddie annual vintage and does not change the D01 R2/R3 gate or 26/50
  completion count.

## CreditAtlas implementation and privacy boundary

`scripts/acquire_fhfa_pudb_ctf.py` downloads the official archive and both
reference workbooks with size/host limits, then profiles the single CSV. The
reader in `src/credit_atlas/fhfa_pudb.py` verifies schema, year fields, key
uniqueness, category domains and official record totals. It emits only
one-dimensional aggregate counts and hashes, never record numbers or loan
rows. The Sources page exposes the counts with an explicit non-performance
caveat; categories with fewer than 30 records are suppressed in the display.
The JSON export is marked private and not approved for public release.

All source files, derived profiles and the analyst workbook remain under the
private CreditAtlas data root on D: and are ignored by Git. The local workbook
`CreditAtlas-FHFA-PUDB-2025-Analyst-Review.xlsx` has five sheets: Overview,
Category Mix, Missingness, Data Dictionary, and Sources & Methods. It contains
126 supported category rows, reports all 66 fields' missingness, suppresses
categories with fewer than 30 observations, and contains no loan-level rows.
Its internal download route is `/downloads/fhfa-pudb-2025-analyst.xlsx` and is
confined to the service's private `outputs` directory. The current receipt does
not approve public release, so neither workbook nor profile is in Git. The
37,209-byte workbook download passed an HTTP check on a test server; visual
browser and native Excel desktop open/recalculate acceptance remain pending.
The public repository contains only the parser, acquisition and workbook
builder scripts, synthetic tests, and this source review. Profile/reproduction
tests passed; the production audit verified all 2,093,767 rows.

## Official references

- [FHFA Enterprise Public Use Database](https://www.fhfa.gov/data/pudb) — 2025 release notes, file list, privacy/proprietary description, and historical releases.
- [2025 data dictionary](https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-data-dictionary.xlsx).
- [2025 record-count workbook](https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-record-count.xlsx).
- [2025 Single-Family Census Tract File](https://www.fhfa.gov/document/d/pud/2025_pudb_sf_ctf.zip).
