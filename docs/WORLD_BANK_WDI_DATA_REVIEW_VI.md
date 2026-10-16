# World Bank WDI — data and source review

**Checkpoint:** 17/10/2026. This is annual country/economy context for P4, not a borrower-level credit outcome or a sovereign default model.

## Source and acquisition

CreditAtlas queried World Bank Indicators API v2, database `2` (World Development Indicators), for seven selected indicators and years 1960–2025. The source package contains 22 files: seven observation responses, seven indicator metadata responses, seven DataBank glossary pages, and the country/economy catalog. The acquisition receipt records **30,437,643 bytes**, SHA-256 per file, and retrieval timestamps from **2026-10-09 05:06:17Z to 05:06:33Z**. A live API spot check on 2026-10-17 for the NPL series returned `lastupdated=2026-10-08`, the same source version as the local snapshot. The other six series were not fully re-downloaded for this spot check; their local receipt has the same source date.

The [World Bank Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) describes V2 as programmatic access to the World Bank databases and says authentication is not required. [Basic call structures](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures) document year-range queries. The request range is not a claim that every indicator/entity has data for every year.

| Indicator | API rows | Non-null values | Source NULLs | Economies with values | Aggregates with values | Non-null year bounds |
|---|---:|---:|---:|---:|---:|---|
| Bank nonperforming loans / gross loans (`FB.AST.NPER.ZS`) | 17,556 | 2,357 | 15,199 | 154 | 0 | 2000–2025 |
| Bank capital / assets (`FB.BNK.CAPA.ZS`) | 17,556 | 2,301 | 15,255 | 152 | 0 | 2000–2025 |
| Domestic private credit / GDP, all financial corporations (`FS.AST.PRVT.GD.ZS`) | 17,556 | 9,990 | 7,566 | 186 | 48 | 1960–2025 |
| Domestic private credit / GDP, banks (`FD.AST.PRVT.GD.ZS`) | 17,556 | 11,696 | 5,860 | 186 | 48 | 1960–2025 |
| External debt stocks / GNI (`DT.DOD.DECT.GN.ZS`) | 17,556 | 6,161 | 11,395 | 121 | 12 | 1970–2024 |
| Real GDP growth (`NY.GDP.MKTP.KD.ZG`) | 17,556 | 14,388 | 3,168 | 214 | 48 | 1961–2025 |
| CPI inflation (`FP.CPI.TOTL.ZG`) | 17,556 | 11,547 | 6,009 | 193 | 48 | 1960–2025 |
| **Total** | **122,892** | **58,440** | **64,452** | — | — | Series-specific |

The country catalog has **296 entries**: 217 economies and 79 aggregate groups. Each indicator response has 14,322 economy rows and 3,234 aggregate rows (49 aggregate groups × 66 requested years). NPL and capital aggregate rows are all NULL in this snapshot. These NULLs are observed missing values, not zero rates; the app does not carry values forward or estimate them. For NPL, the latest non-null year is 2025 for 154 economies; that does not mean 154 complete annual panels.

## Verification and application mapping

The local `verify_source` check re-hashed all 22 source files against the private receipt. `derive_source` re-parsed the source, validated its catalog joins and indicator/year keys, and returned 122,892 canonical observations, 296 catalog entries and seven indicator definitions. The separate country audit receipt records a bidirectional SQL comparison with zero differing rows, duplicate keys or orphan keys. The public source register binds 22 objects to the `world-bank-wdi` parent group; the app uses `country_observatory.py` and `country_views.py` for `/api/country-view` and `/api/country-report`.

Values use annual country/economy × indicator grain. The NPL series describes deposit-taker system asset quality, not a portfolio-level delinquency rate or an individual consumer PD. The capital indicator is Tier 1 capital / total assets according to its source definition; it is not interchangeable with CET1/RWA. External debt / GNI covers public and private external debt, not just government borrowing. Keep source/declared units and indicator notes with outputs.

## Source providers and reuse constraints

The World Bank’s [Dataset Terms summary](https://data.worldbank.org/summary-terms-of-use) says datasets are generally available under CC BY 4.0 unless the data or indicator metadata says otherwise, requires attribution, prohibits implied World Bank endorsement, and warns that some datasets contain third-party data with additional restrictions. The WDI indicator metadata names underlying organizations including IMF, OECD and national statistical offices. Therefore the register keeps provider-specific reuse review open for each series. The raw source snapshot remains private until that review is complete; the public register contains aggregate counts and short hash prefixes only.

## CreditAtlas use and next steps

WDI is useful for country-level banking soundness, credit depth, external leverage, growth and inflation context. It can support descriptive country comparison and research questions about macroeconomic conditions. It cannot supply borrower features, underwriting outcomes, monthly vintage dynamics or a calibrated PD/LGD by itself. The snapshot is latest-revised, not historical point-in-time data; it is not qualified for an out-of-time macro backtest without vintage-availability evidence. No forecast, imputation, zero-fill or carry-forward was created.

Next, preserve these distinctions in N03 KPI lineage; review provider/license restrictions before redistributing any raw series; and continue the 12 remaining N02 parent-group bindings. Do not infer a risk variable where no observed value exists.
