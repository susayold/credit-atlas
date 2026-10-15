# B19: macro vintage availability

## Scope and current acceptance

Implemented in `src/crsl/macro.py` with `configs/macro.json`. This is a three-series
adapter and tested temporal join, not a completed macro forecasting study. The current
environment has no FRED_API_KEY, so no actual vintage dataset, observed revision
comparison or real-loan macro feature table has yet been acquired. Tests use synthetic
API-shaped records and are not observed macro evidence. B19 remains PARTIAL.

## Source and mechanism

| Series | Source definition | Research rationale | Boundary |
|---|---|---|---|
| UNRATE | BLS, monthly, seasonally adjusted, percent | Repayment-capacity context | National labor market is not individual employment status |
| USSTHPI | FHFA, quarterly, NSA, index 1980Q1=100 | Collateral-price context | Not a property valuation or observed current LTV |
| MORTGAGE30US | Freddie Mac, weekly ending Thursday, NSA, percent | Refinancing-incentive context | Existing fixed-rate loan coupons do not reset with market rates |

Definitions checked against [UNRATE](https://fred.stlouisfed.org/series/UNRATE),
[USSTHPI](https://fred.stlouisfed.org/series/USSTHPI) and
[MORTGAGE30US](https://fred.stlouisfed.org/series/MORTGAGE30US). The mortgage-rate page
identifies a PMMS methodology change on 2022-11-17; comparison across that date must
retain the break. No state or individual-level enrichment is inferred.

UNRATE and USSTHPI source pages tag public-domain data with citation requested.
MORTGAGE30US is copyrighted and needs a separate redistribution review. FRED service
access is not blanket permission to redistribute every underlying series. Keep the
current outputs private. Use the documented API, not scraping or alternate endpoints
to bypass access. See [FRED terms](https://fred.stlouisfed.org/legal/).

## Native records and calendar

Each revision retains series_id, reference_period, reference_end, realtime_start,
realtime_end, value, units, frequency and revision_id. Raw API response strings and
metadata are retained privately with request parameters excluding credentials.
`lin` requests source levels: a percent series remains percent, not a fraction or
percentage change. Source metadata versions must match the expected units, native
frequency and seasonal adjustment; mismatch requires review, never auto-conversion.

Monthly references are first-of-month dates and quarterly references begin a calendar
quarter. The code computes the end of that measurement period. Weekly source dates
are preserved without shifting old observations. The adapter does not resample weeks
to months or quarters to months, interpolate, or invent release calendars.

The official API uses inclusive real-time intervals. Omitting those parameters normally
selects today's knowledge. Requests therefore pin the full real-time start and a fixed
end, alongside observation coverage, and preserve each observation's interval. Pagination,
response bounds, row counts and duplicate/overlapping revisions are checked. See
[real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and
[observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html).

## Information-cutoff rule

`information_cutoff` means the **start of a calendar date**, not an intraday timestamp.
The adapter uses knowledge through the preceding day. Thus a source revision dated
D becomes usable at D+1. This conservative project convention excludes same-day
release ambiguity; it is not a claim that the source itself always publishes one day
late. An intraday datetime is rejected rather than silently losing its time zone.

For a series and cutoff:

1. Ignore reference periods not completed by the preceding day.
2. Consider only revisions whose real-time start is no later than that day.
3. Select the newest such reference period, then the revision valid on that day.
4. Require its inclusive real-time end to cover that day.
5. Enforce maximum age from reference-period end: 90 days for UNRATE, 180 for USSTHPI,
   28 for MORTGAGE30US. These are explicit development staleness assumptions, not
   official release SLAs or tuned predictive parameters.
6. Preserve source `.` as unavailable. A withdrawal does not resurrect an old revision;
   a missing recent observation does not silently select an older numeric value.

Returned statuses distinguish available, no_released_observation, source_missing,
unavailable_revision_window and stale. Unavailable values remain null, never zero.
The index returns copies so a consumer cannot mutate its cached historical selection.

ALFRED release dates can come from the original source, its data provider, or the date
the series first appeared in FRED when other release evidence is absent. Date-vintage
selection is therefore not proof of exact intraday dissemination. See
[ALFRED help](https://alfred.stlouisfed.org/help). It also does not make the separate
latest-release mortgage dataset archival point-in-time data.

## Integration and boundaries

`join_records` retains one record for every input loan/landmark and configured series,
including unavailable macro values. Duplicate input landmarks fail. The private
Parquet output retains source numeric text beside a numeric value, selected revision,
availability date and status. No imputation occurs here.

`compare_revision` holds the reference period constant at two information dates.
Its later value and delta are labeled retrospective and must not become predictive
inputs at the earlier origin. T17 tests a revision after scoring. T31 tests a future
actual macro path. Scenario paths require an explicit scenario label; an oracle
sensitivity requires its own explicit label and is not a normal forecast result.

Macro remains an optional, separate stage. Missing API access writes unavailable.json
without a completed-run receipt, leaves the non-macro core unchanged, and never calls
a latest-data fallback. Network/API failures are sanitized so API keys do not appear
in exception text or receipts. Partial or tampered caches cannot be loaded as complete.

## Reproduce when authorized access is available

Provide the key through the process environment, not a CLI argument or chat. Official
access documentation: [FRED API](https://fred.stlouisfed.org/docs/api/fred/).

```powershell
.\.venv\Scripts\python -m crsl.macro fetch
.\.venv\Scripts\python -m crsl.macro join --label-run <completed-label-run> --macro-run <completed-macro-run>
.\scripts\test.ps1
```

Use actual returned run paths; do not interpret an unavailable run as completed.
Source requests are frozen to the dates in macro.json. Expanding dates requires a new
run. Receipt hashes detect local drift, not malicious replacement of both data and
receipts; these are unsigned research artifacts.

## Remaining B19 acceptance

- Acquire actual vintage responses through authorized official access.
- Review historical metadata and any PMMS frequency/methodology differences.
- Execute the join against the current private loan landmarks and examine coverage.
- Produce one real same-period revised-versus-as-of example and sensitivity analysis.
- Review staleness assumptions and permissions before any public output or model fit.

No macro predictions, causal economic effects or improvements over a naive forecast
are claimed by this implementation checkpoint.
