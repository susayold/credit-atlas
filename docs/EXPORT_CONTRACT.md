# Private research export — schema 2

The app's report button and GET /api/report produce the same deterministic
package for the selected verified case and filter context. The original frozen
snapshot.json and report.json are preserved. Schema 2 wraps the engine's
schema-1 aggregate report and adds supplemental evidence; it does not rewrite
upstream engine artifacts or definitions.

## Package fields

| Field | Meaning |
|---|---|
| schema_version | 2 for the CreditAtlas wrapper |
| case_id / target | Selected case and exact early-entry target contract |
| filter_context | Segment, basis, vintage horizon, monthly chart range and transition_year |
| report | Original engine aggregate contract with supported table filters |
| supplemental_evidence.quality_monitoring | Whole-sample integrity, field availability and investigation order |
| supplemental_evidence.episode_followup | Selected-segment observation support after confirmed episode events |
| supplemental_evidence.period_transitions | Selected-segment reporting-year matrices and explicit lifetime comparator |
| supplemental_sha256 | SHA-256 of each supplement's canonical JSON |
| lineage | Case receipt digest, frozen output digests, pipeline and supplement source-code digests |
| scope_notes | Explicit applicability of the filters |
| visibility / public_release_approved | Private / false |

Supplement JSON is hashed using sorted keys, compact separators, UTF-8,
ensure_ascii=false and allow_nan=false. Repeated exports from unchanged
evidence and code with identical filters have identical payloads. Review notes
are mutable private records and are accessed separately; they are not silently
mixed into this deterministic numerical export.

## Filter applicability

| Evidence | Segment | Reporting date range | Horizon |
|---|---|---|---|
| Monthly stock | Applies | Applies to reporting month | Not applicable |
| Profile / segmented transitions | Applies | Does not apply | Not applicable |
| Overall transitions | Whole sample; empty with segment selection | Does not apply | Not applicable |
| Vintage competing events | Applies | Does not apply | Selected 6/12/24m |
| Observed loss | Whole sample | Does not apply | Not applicable |
| Quality monitoring | Whole sample | Does not apply | Not applicable |
| Episode follow-up | Applies | Does not apply | Both confirmation-based 6/12m are exported |
| Period transitions | Applies | Separate transition_year filter; chart range does not apply | Not applicable |

Basis selects how count/UPB metrics are displayed. The numerical export retains
both relevant native count and balance fields rather than discarding evidence.
Episode follow-up horizons are separate from the vintage horizon; selecting
24m vintage does not invent 24m episode support.

transition_year accepts all or a four-digit year. Period-transition rows are
filtered by the opening reporting year at t; December 2020 to January 2021
belongs to 2020. With all selected, all available year rows are retained.
lifetime_rows always retain the whole-period comparator for the selected
segment. Selecting an unavailable year produces empty year rows, not a fallback
to a different year. Original engine lifetime tables are unchanged by this
supplement's year filter.

The period supplement retains pair counts, distinct loans, missing-balance
counts, opening UPB, origin denominator counts/UPB and both probabilities.
Year-to-lifetime and frozen overall/segmented matrices are reconciled exactly
inside DuckDB before decimal balances are converted for JSON. Distinct loans
are counted independently at each grain; they must not be summed across cells
or years. A null balance remains null. Zero aggregate UPB gives an unavailable
balance probability.

## Evidence constraints

- Supplements must share the selected case and pipeline, or export fails.
- Small serving contracts are hashed on each read. Other source/derived files
  are fully hashed on initial case loading, then monitored by file metadata.
- The engine's report guard rejects source identity/prediction keys and
  absolute private filesystem paths.
- Timeline data and source IDs are not included in the aggregate export.
- The package is not an IFRS 9/ECL input contract, lending decision interface
  or public-distribution approval.

Checks: test_frozen_service.py, browser_qa.py, audit_private_package.py.

The `/api/report` consumer contract accepts only `run`, `segment`, `basis`,
`horizon`, `from`, `to`, and `transition_year`. If `run` is supplied it must
match the selected case. Unknown parameters, including metric-use overrides
such as PD12, ECL, or cash flow, fail with a 400-level contract error instead
of silently returning the default descriptive package. See
D01_EXPORT_CONTRACT_AUDIT_VI.md for actual-case five-scope verification.
