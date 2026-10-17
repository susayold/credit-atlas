# HUD FHA Production Report — serious-delinquency transitions

**Scope.** This companion dataset transcribes Table 2 of HUD's August 2026 FHA Single Family Production Report. It remains separate from FHA Single-Family Loan Performance Trends, the FHFA NSMO PUF and Freddie Mac D01. HUD's official index describes the Production Report as a monthly report and currently lists August 2026 as the latest release: https://www.hud.gov/hud-partners/fha-production-report.

## What the table measures

Table 2 reports aggregate serious-delinquency inventory transitions by month. HUD defines the inventory as loans 90 or more days delinquent, in foreclosure or in bankruptcy. Cures are loans leaving serious delinquency and becoming less than 90 days delinquent after a full or partial cure, with or without loss mitigation or lender assistance. The table excludes HECM.

For each month, the reported count identity is:

`Ending inventory = Beginning inventory + Entries − Cures − Claims − Prepayments from serious-delinquency inventory.`

The late-posting adjustment reconciles the next month's beginning inventory to the prior month's ending inventory:

`Beginning inventory(t) = Ending inventory(t−1) + Late-posting adjustment(t).`

The HUD cure ratio is `Cures(t) / Entries(t)`, rounded to one decimal percent. It compares monthly aggregate counts, not a matched cohort. It can exceed 100% (108.0% in March 2026 and 104.5% in July 2026); it is not an individual-loan cure probability, default probability or rate forecast.

## August 2026 snapshot

| HUD Table 2 measure | August 2026 |
|---|---:|
| Beginning serious-delinquency inventory | 537,258 |
| Entering serious delinquency | 65,811 |
| Cured / leaving serious delinquency | 57,893 |
| Claims | 2,288 |
| Prepayments from serious-delinquency inventory | 2,478 |
| Ending serious-delinquency inventory | 540,410 |
| Late-posting adjustment | 1,938 |
| HUD cure ratio | 88.0% |

The ending balance reconciles exactly: 537,258 + 65,811 − 57,893 − 2,288 − 2,478 = 540,410. The beginning inventory also reconciles: July's ending 535,320 + August's 1,938 late-posting adjustment = 537,258.

## Coverage and verification

The curated CSV contains 13 reported months, August 2025–August 2026. All 13 monthly ending-inventory identities match exactly; the 12 beginning-inventory links after the first available month reconcile to prior ending inventory plus the current month's published adjustment. Each published cure ratio matches the cured/entry count ratio to one decimal. No values are forecast, interpolated or imputed.

The app serves these rows through `/api/hud-fha-production-transitions`. The FHA benchmark workbook has a separate **Delinquency flow** sheet, and the combined D02 data-reference workbook has a separate **HUD transitions** sheet. Both keep the source counts filterable and numeric.

## Source and limitations

- Official report: https://www.hud.gov/sites/default/files/Housing/documents/FHAProd_AUG2026.pdf — Table 2, report page 3.
- Release index: https://www.hud.gov/hud-partners/fha-production-report.
- HUD's [2025 Web Publication Procedures and Style Guide](https://www.hud.gov/sites/documents/webpubstandards.pdf) says that, as a rule, content on HUD's Internet websites is public domain. This workbook/app reproduces numeric aggregate values with attribution; it does not copy report graphics or long passages. The report PDF could not be retrieved to inspect any report-specific third-party notice.
- Direct retrieval of the August 2026 PDF binary returned HTTP 403. The PDF is not stored locally; its raw SHA-256 is therefore null. The public CSV is a report transcription, not a downloaded publisher data file.
- HUD notes that this serious-delinquency inventory may not reconcile fully with the separate FHA Loan Performance Trends report because timing and data sources differ. Do not join or add the two series.
- The measures are monthly program-level aggregates. They do not identify borrowers or loan-months and cannot supply a borrower-level default label or a model-training sample.
