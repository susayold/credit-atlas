# Private remote backup — 2026-09-12

This is a development backup, not a completed research release.

- GitHub: https://github.com/susayold/credit-risk-strategy-lab (PRIVATE verified).
- Initial source commit: `c033da1`; 135 files, no executed notebook outputs.
- Drive folder: https://drive.google.com/drive/folders/1fxmuNdoSfc4tXwP4YMQ6GtxradGsazq5
- Source ZIP file ID: `1FZn34uG7Tn5U0nOiUzuYaY3zEpDf7jWy`; parent and owner-only permissions verified by metadata readback.
- ZIP SHA256: `F28B7DC0F93EC4849F5CF63DF672632B508BCFF1E538219A55750DDDCC4F12F` (352978 bytes).
- Local regression: 375 passed with the new profile and segmented-evidence tests.
- First remote CI run: https://github.com/susayold/credit-risk-strategy-lab/actions/runs/34591270565 (completed, success verified using GitHub CLI).

## Latest source snapshot — 2026-09-12

- Source commit `064d334` pushed to `master`; the aggregate-data package is versioned under `data/aggregate/` with stable LF line endings.
- Drive ZIP: `credit-risk-strategy-lab-source-064d334.zip` (`1FZn34uG7Tn5U0nOiUzuYaY3zEpDf7jWy`), 352978 bytes; parent and owner-only permissions verified by metadata readback.
- ZIP SHA256: `F28B7DC0F93EC4849F5CF63DF672632B508BCFF1E538219A55750DDDCC4F12F`.
- Local regression: 375 passed. The private website/workbook snapshot is based on `pipeline-83667cc64126`; Excel QA passed with 15 sheets, 4,569 matching preview cells and zero formula errors. The workbook now includes portfolio anatomy and segmented transition tables.
- The source ZIP contains tracked code, documentation, contracts, tests and static site assets only. Raw annual data, loan-level outputs, private pipeline artifacts and real-data Excel remain excluded.

## Aggregate data folder — 2026-09-12

- Drive folder: https://drive.google.com/drive/folders/1OU6bjh4acXTMVI22b1jzX1HomBuMeG9G
- Contents: non-identifying snapshot, label outcomes, monthly portfolio, portfolio anatomy buckets, overall and segmented state transitions, competing-risk vintage rows, observed-loss summary, manifest, aggregate report export, private workbook and source-code ZIP.
- The folder is owner-only and contains no raw annual ZIP, loan-level Parquet, IDs or prediction rows. This is the maximum safe upload under the current rights review; raw and loan-level derived data remain local.

## Not uploaded

Raw annual data, canonical loan records, loan-level derived outputs and source
document copies remain local. Credentials, environments, dependencies and caches
are excluded. The Drive folder contains only owner-only aggregate evidence, the
private review workbook/report and the tracked source-code archive. A private
destination is not itself proof of provider permission to redistribute the raw
dataset or loan-level derived products.

The archive is the immutable initial source snapshot, not automatic ongoing sync.
Do not treat repository creation or green CI as completion of B00–B35.

## B11 source snapshot — 2026-09-11

- Source commit `8890a3d` pushed and remote CI run `34592429128` completed successfully.
- Drive ZIP ID `1uVxn0jObG5IsJtOyMTn1P3x9jmOhiEV4`: 242655 bytes; owner-only permissions and expected parent verified.
- SHA256: `abbc89fa3a81a7d4b9f368ed4e3be5eb2b54b681d0b29560397e2dca843ec8b7`.
- Added vintage source, synthetic tests, methodology and clean notebook; no executed notebook images/outputs or private loan records included.
- Local suite: 346 passed. Five notebook cells executed; figures reviewed after correcting stock-axis tick precision. Whole-notebook viewer review is not claimed.
