# CreditAtlas

CreditAtlas is a multi-workspace credit-risk research application. It brings source-aware portfolio, retail, mortgage, small-business, bank, market, structured-credit, and country-analysis workflows into one local platform. The code emphasizes reproducible transformations, explicit denominators, lineage, missing-data handling, and pre-fit/model-use gates.

This public repository contains the application source, tests, scripts, and selected technical documentation. It does **not** include source microdata, borrower-level records, private research artifacts, local databases, credentials, or generated outputs. The app is a research workbench, not a production lending decision system or a qualified regulatory PD/ECL engine.

## What is included

- Python API, domain adapters, research and report services under `src/credit_atlas/`.
- Browser workspaces and static assets under `apps/web/`.
- Blank Excel input templates under `apps/excel/`; some workbook builder scripts use a host-provided runtime and are not standalone npm workflows.
- Application tests and a pinned, selective copy of the user-owned Credit Risk Strategy Lab engine under `vendor/`.
- Product plans, workflow guides, source contracts, and research-method notes under `docs/`.

## Quick start

Requires Python 3.12 or newer. The current safety boundary requires the clone to be on a Windows `D:` drive. From this directory in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,models,structured,simulation]"
$env:PYTHONPATH = "src;vendor/credit_risk_strategy_lab/src;vendor/credit_risk_strategy_lab"
python -m credit_atlas.cli serve --port 8770
```

Create the local configuration and start the app:

```powershell
Copy-Item workspace.local.example.json workspace.local.json
```

Then open `http://127.0.0.1:8770`. Without locally acquired and registered source data, data-dependent workspaces remain empty or unavailable by design. Follow each source's current terms and access requirements; do not commit source files or access cookies.

Run the application tests with:

```powershell
$env:PYTHONPATH = "src;vendor/credit_risk_strategy_lab/src;vendor/credit_risk_strategy_lab"
python -m pytest -q
```

Tests that require the excluded local borrower data or private evidence receipts are skipped automatically when those inputs are absent. The skip list is explicit in `tests/public_private_data_skiplist.json`.

## Documentation

- [Five-workspace plan](docs/PLAN_FIVE_WORKSPACES.md)
- [Detailed workbench plan](docs/PLAN_WORKBENCH_DETAIL.md)
- [Mortgage module plan](docs/PLAN_MODULE_01.md)
- [Ginnie Mae separate-source review and access gate](docs/GINNIE_MAE_LOAN_PERFORMANCE_SOURCE_REVIEW_VI.md)
- [User workflow guide](docs/WORKBENCH_USER_GUIDE_VI.md)
- [Public release scope and data policy](PUBLIC_RELEASE_SCOPE.md)

Some internal research notes refer to evidence or datasets intentionally excluded from this public copy. See the release-scope document for the boundary.
