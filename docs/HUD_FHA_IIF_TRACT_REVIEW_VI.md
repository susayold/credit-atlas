# HUD FHA Insurance-in-Force by Tract — source review

Checkpoint: 2026-10-15. Source lineage is maintained separately from D01's
Freddie Mac mortgage-performance cohort.

## What the source contains

HUD's public FHA Insurance in Force dataset provides one record per 2010 Census
tract, with tract geography, population/housing context, aggregate count of
active FHA-insured loans, unpaid balance and original mortgage amount. HUD's
catalog calls this an aggregate of active single-family FHA loans; its field
dictionary identifies `UNPD_BAL_SUM`, `IIF_CNT` and `ORIG_MRTG_AMT_SUM` as
unpaid balance, active insured-loan count and original mortgage amount. It is
useful for FHA footprint and geographic concentration context, not for
borrower-level credit decisions.

Official source links:

- [HUD dataset catalog record on Data.gov](https://catalog.data.gov/dataset/fha-insurance-in-force-by-tract)
- [Official HUD ArcGIS CSV download](https://hudgis-hud.opendata.arcgis.com/api/download/v1/items/8f7af6a831dc45f1befc5bee7bc682df/csv?layers=0)
- [HUD ArcGIS layer metadata](https://www.arcgis.com/sharing/rest/content/items/8f7af6a831dc45f1befc5bee7bc682df/info/metadata/metadata.xml?format=default&output=html)
- [HUD FHA Single-Family Portfolio Snapshot](https://www.hud.gov/stat/sfh/fha-sf-portfolio-snapshot) — a different monthly Excel product. Its page says it has loan-level data records, but direct XLSX requests returned HTTP 403 in this environment, so no snapshot workbook was acquired or profiled.

## Acquired file and checks

The CSV is stored only at
`data/private/hud-fha-iif-tract/fha-insurance-in-force-by-tract.csv` and is
excluded from the public bundle. The download used the official ArcGIS Hub
CSV endpoint.

| Check | Result |
|---|---:|
| Source rows / unique GEOIDs | 85,154 / 85,154 |
| Fields | 20 |
| States and territories represented | 52 |
| File size | 12,772,764 bytes |
| SHA-256 | `e47f57af28c2594c03595fe00301a7c7357130f17e0ad32b0cb50e7d5ee03f62` |
| Nonblank active FHA-loan count sum | 7,683,397 |
| Nonnegative-coded unpaid balance sum | $1,445,485,085,013 |
| Nonnegative-coded original mortgage amount sum | $1,637,527,581,865 |
| Blank cells in each of the three FHA measures | 4,620 |
| `-4` in unpaid-balance and original-amount fields | 9,598 occurrences in each field |

The `-4` value is not defined in the layer's published field dictionary. It is
therefore quarantined as an uninterpreted source code and excluded from sums;
it is not treated as a negative loan balance or as zero. Blank cells remain
missing. These totals are reproducible descriptive sums over nonblank,
nonnegative-coded tract values, not a forecast, audited FHA accounting balance,
or risk rate.

## Timing, grain and limits

There is a material publisher metadata inconsistency. Data.gov and the full
ArcGIS item metadata say coverage `03/2025` and the item was last updated
2025-05-01. The live FeatureServer layer description still says coverage
`09/2021`. Treat the file as a static snapshot with unresolved effective date;
do not use it as a current 2026 balance, calculate a trend, or compare it to
another period without clarification from HUD.

The data do not include repayment months, delinquency states, default,
foreclosure, prepayment, loss, applications, denials, or a borrower identifier.
They cannot validate a credit-risk model, establish neighborhood-level
borrower risk, or be joined to Freddie loan rows. Census tract 2010 geography
and the HUD source's single-family/exposure semantics must be preserved.

## CreditAtlas placement

The app adds this as a separate aggregate panel on the Mortgage Sources screen.
The reader validates the full schema, unique tract IDs, numeric domains and
official row count, then emits state-level aggregates only. The tract keys and
geometry are never exported by the app. A content-hash-linked private receipt
protects the acquisition profile. The panel prominently shows the timing
conflict, blank-cell handling, the quarantined `-4` code, and the no-performance
scope. Four synthetic parser checks pass; combined real-data browser QA is
69/69 PASS at `artifacts/private/browser-qa-7a73963387de/receipt.json`.

This source adds a separate FHA geographic-exposure context track. It does not
change D01's `26/50 = 52%` acceptance, add a Freddie vintage, or remove the
NSMO/Ginnie Mae access gates.
