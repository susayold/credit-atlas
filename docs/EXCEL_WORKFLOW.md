# Excel workflow — 10/10/2026

Excel intake and review export are implemented first in P4 Exposure. The five
workspaces remain separate domains in the common application; this checkpoint
does not mean every domain accepts arbitrary company spreadsheets.

The Mortgage **Sources** view also exposes five fixed Excel downloads for
Freddie Release 47 parser examples, Fannie sample rows/layout, and Ginnie sample
records/layout. The routes read bounded workbooks from the local private `D:`
data tree; they accept no query filters and return 404 when the local workbook
is absent. Workbooks containing source sample rows/identifiers are excluded
from the public GitHub repository. Freddie Release 47 examples are not annual
vintages; the Fannie, Ginnie, NSMO, HMDA and Freddie source populations remain
separate.

## Analyst workflow

1. Open Exposure and choose **Tải mẫu Excel nhập danh mục**.
2. Replace the three fictional `EXAMPLE` rows in `InputPositions` with your
   portfolio records. Expand the Excel Table for extra rows. Update
   `InputControl` source namespace, description and reporting period.
3. Upload the `.xlsx` with **Nhập Excel**. The app validates the typed exposure
   contract, retains the original workbook and creates a new private import.
   The source workbook digest is part of verified lineage.
4. Inspect native-currency totals, zero balances and missing risk inputs.
   Select one currency and a grouping, then **Xuất portfolio Excel**.
5. Review the six sheets: Summary, ScenarioModel, ResearchResults, Inventory,
   Review and Audit. ScenarioModel supports Baseline/Mild/Adverse, with editable
   PD odds, LGD additions and EAD factors. Formula results recalculate locally.
   ResearchResults contains saved Python factorized EL, ECL and Monte Carlo
   VaR/ES. Changing Excel assumptions does not rerun ECL or Monte Carlo.
6. Save the analytical review in the app to version it. Workbook notes do not
   write back to the app. Draft/reviewed annotations do not qualify estimates
   for accounting, capital or lending decisions.

## Input contract and limits

The template has 13 exact columns: position_id, pool_key, representation, as_of,
currency, amount_unit, reported_amount, segment, region, source_state, pd, lgd,
ead. `InputControl` has 11 metadata keys from the existing exposure contract.
Dates use explicit ISO text (e.g. `2026-10` for month grain), not Excel serials.
Amount units are major/thousand/million. Keep PD/LGD/EAD blank when
`risk_contract` is JSON `null`; missing risk is unavailable, not zero loss.
The template contains illustrative USD/VND positions, not company data.

Supported input is `.xlsx`, at most 20 MB, 50,000 positions, 1,000 ZIP entries
and 100 MB expanded. Preserve the sheet names and exact headers. Input sheets
accept values only: formula caches are rejected. Convert source calculations
to explicit values first. Old `.xls`, VBA, external links and Power Query
connections are unsupported. Extra company formats need explicit column
mapping before they can be imported.

Excel numbers retain at most 15 significant digits. Store long identifiers or
more precise amounts as text. The adapter rejects unsafe numeric precision
and expansion. Zero amounts remain zero; currencies are never added without
an explicit FX model. Input source amounts are not automatically EAD.

Export is scoped to one native currency and source import. The current Excel
scenario layout supports at most three eligible scenario segments. Saved
results carry source/version identifiers; changes to evidence invalidate the
cached export. Excel uses numeric formulas and cent-level reconciliation;
the original typed app data remains the precision and lineage authority.

## Runtime and reproducibility

The packaged input template is `apps/excel/templates/CreditAtlas-Portfolio-Input.xlsx`.
The deliverables are under `outputs/01a119ef-c68b-7292-b81e-8192458d08f8`.
Authoring uses bundled Node and `@oai/artifact-tool` through
`apps/excel/build_workbook.mjs`. This development workspace has a junction to
the bundled package runtime; another machine must supply that runtime/package
and may set `CREDIT_ATLAS_NODE`. The app does not require Microsoft Excel to
be installed. Native Excel desktop execution has not been tested.

API: GET `/api/exposure-excel-template`; GET `/api/exposure-excel-report` with
`import_id`, `currency`, `dimension`; POST `/api/exposure-excel-import` with
exact `filename` and base64 `content_base64`. Intake requires local same-origin
headers. Downloads are private/no-store. Original input, typed import and
export input/workbook hashes are retained in private artifacts.

Verification commands:

```powershell
.\scripts\test.ps1
.\.venv\Scripts\python.exe -X utf8 scripts/audit_excel_workbooks.py
.\.venv\Scripts\python.exe -X utf8 scripts/browser_exposure_qa.py
```

The builder recalculates and checks formula errors, switches baseline/adverse,
perturbs missing and zero PD inputs and renders every sheet. The independent
saved-XLSX audit reads XML and checks cached controls. Browser QA exercises
template download, upload, separate USD/VND totals, native report download,
formula caches, mobile layouts and private source-bound review workflows.

Actual live checkpoint: `artifacts/private/excel-live-019213c72060.json`, PASS.
Browser checkpoint: `exposure-browser-qa-349d06c7515b`, 19 checks PASS.
Final Excel tests: 9 PASS. See FIVE_WORKSPACES_STATUS.md for full-suite
resource failure and isolated successful retry.
