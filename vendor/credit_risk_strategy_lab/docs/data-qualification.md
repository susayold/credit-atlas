# Source qualification result — implementation checkpoint

## Current annual-source checkpoint — 10 September 2026

### Subsequent engineering/audit update

Canonical `canonical-c36cd6b9b666`, labels `labels-ec5d5fb7b61a`,
audit `audit-d3e6fafe4c5e`, portfolio `portfolio-a317e27aa17d`.
97 tests pass; foundation notebook re-derived and compared every label row.

- Correct earlier acquisition-vintage wording: official annual vintage is origination year;
  acquisition determines start of monthly history (guide p16).
- HARP=Y is Relief Refinance (17,399 loans); the HARP subset also requires LTV>80 (11,121 loans).
- 48,066 early-entry eligible loans;12m outcomes:102 D3,45,241 full-horizon no-event,
  2,641 prepayments,82 other exits.1,934 loans are ineligible before outcome evaluation.
- All374 reported actual-loss and expense-component totals reconcile exactly.
- The7 missing losses are6 defect-related and1 recent disposition; none unexplained in this sample.
- Seed20260910 plus edge-case sample covers25loans; symmetric raw/canonical value comparison
  found0 differing rows in both tables. This is programmatic source parity, not visual/manual review.
- Annual/event-category field availability, monthly stocks, count/opening-UPB transition
  matrices and forward-only cure/redefault now exist privately.

See ADR-002 and the canonical/observation methodology documents for current definitions.
Remaining limitations below still apply unless explicitly resolved by this update.

The user downloaded `sample_2012.zip` from the authenticated Clarity SFLLD page
and requested continuation. It was copied into private source storage and parsed
using Release 47, with no format-example ID exceptions.

Input SHA256: `35c41582157804e3f632d68140246fcc6eb0973590ba0cf9a0f03600bf8499f9`.
Initial run: `d3167b604110-30526467`; extended diagnostics: `spike-b451ac1c907c`.

| Check | Result | Interpretation |
|---|---:|---|
| Loans | 50,000 | One row per origination key |
| Loan-month rows | 4,510,559 | Not independent borrowers |
| Duplicate keys / orphan rows / loans without history | 0 / 0 / 0 | Initial integrity PASS |
| Rejected parser rows, both files | 0 | Accepted + rejected reconcile to source lines |
| Loans with within-observation gaps | 0 | Does not reconstruct pre-acquisition history |
| At least 13 contiguous observations | 47,349 | Not automatically negative12m eligibility |
| Period range | January 2012–March 2026 | Latest-release retrospective panel |
| Ever observed numeric D3 | 1,713 loans | 18,057 monthly D3 states; no D3-at-entry loans |
| Ever RA | 120 loans | Separate raw state from numeric D3 |
| Populated actual loss | 374 loans | Not certified LGD targets |
| Eligible terminal codes without actual loss | 7 rows | Do not fill missing losses with zero |
| Multiple terminal rows per loan | 0 | No arbitrary last-terminal reduction needed here |
| Entry age 0 / entry age 0–1 | 43,177 / 48,080 loans | Late entry still needs cohort handling |
| Raw VantageScore=9999 | 50,000 loans | High: no usable score variation; blank-rate screen insufficient |
| Raw DTI=999 | 17,400 loans | High: field-specific sentinel mapping required |
| HARP=Y | 17,399 loans | Segment diagnostics needed; causal missingness explanation not established |

Confidence is high for these exact source counts, not for predictive performance.
No risk model has been fitted. In particular, 1,713 / 50,000 is not a default12m
rate: observation lengths differ, prepayments compete, and labels remain unimplemented.

### Capability verdict

- Monthly engineering: PASS initial source screen; proceed with field-specific canonical design.
- Origination/behavioral labels: CONDITIONAL on entry, censoring, competing events and target tests.
- Loss: CONDITIONAL on the 7 missing cases, signed formula reconciliation, maturity and sample size.
- Multi-vintage validation: NOT READY with only acquisition sample 2012.
- Macro: NOT IMPLEMENTED; matching calendar coverage alone is insufficient.
- Publication: BLOCKED pending rights review; all real source and trajectory data stay private.

Candidate expansion follows the approved plan: 2006–2011 additional train-history
samples, 2014 calibration, 2016 validation and 2018 final OOT. These are acquisition
vintages, not guaranteed contractual origination cohorts. Freeze actual date-based
splits only after profiling all selected samples and verifying label maturity.
No full-standard multi-million-loan download is requested.

### Reproduction and remaining acceptance work

`python -m crsl.spike --source-run artifacts/private/d3167b604110-30526467`
creates a new private run, `profile.parquet`, aggregate diagnostic JSON and
seed-20260910 plus edge-case trajectory selection. Selection is reproducible;
it is not a claim that every selected trajectory has been manually reviewed.
SQL lives in `sql/profile_events.sql`; aggregation logic in `src/crsl/spike.py`.
The existing notebook independently recomputed annual integrity results in 3 cells.

Remaining B03: monthly/event-category missingness, manual private spot checks,
reviewed cohort config, loss exception investigation and split-level event support.
Therefore B03 and R0 are not marked complete. B04–B35 are not complete.

Private report payload: `artifacts/private/spike-b451ac1c907c/artifact.json`.
The canonical HTML delivery command passed to rendering but failed the desktop
horizontal-overflow verifier twice (including one targeted SQL line-wrap correction).
No final `report.html` was released. Failure screenshots are retained privately.
Report QA failure does not invalidate the independently reproduced data counts.

## Historical format-example checkpoint (preserved)

The following describes the earlier public-format example, not the annual sample
now available. Its old annual-access blocker has been resolved.

Date: 2026-09-10.
Evidence run: ed5da120d9c9-29579293.
Purpose: test source parsing and assess whether the available file can support the V4 research plan.

## Conclusion

**The public Release 47 format example is not research-qualified.**
The annual sample still needs to be obtained through authorized Clarity access.
This is not a claim that the annual Freddie Mac dataset has poor integrity:
the finding applies only to the public format-example archive.

## Source and grain

Public ZIP: https://www.freddiemac.com/fmac-resources/research/docs/release-47-sample-files.zip

Two source files, with expected origination and loan-month layouts.
Data-kind metadata stays format_example, never annual_sample.
All raw files, staged records and detailed profile outputs remain private.

## Checks performed and evidence

| Check | Measured result | Interpretation |
|---|---:|---|
| Origination rows | 1,000 | Format-example rows, not research population |
| Distinct origination loan identifiers | 1,000 | No duplicate origination key |
| Performance rows | 1,011 | Monthly example records |
| Distinct performance loan identifiers | 12 | Not 1,011 independent loans |
| Duplicate performance loan-month keys | 0 | Unique key within this example |
| Performance rows with no matching origination ID | 1,011 / 1,011 (100%) | Two examples cannot be joined for research |
| Origination records without matching performance | 1,000 / 1,000 (100%) | No complete linked research cohort |
| Field counts | 31 origination / 35 performance | Matches official July 2026 layout |
| Positional/type staging | Pass in format-example mode | Does not imply research approval |

The example uses Q5 IDs in origination and Q6 IDs in performance.
Those are not valid quarters for the production source contract.
The first strict parsing attempt correctly rejected them.
A separate format-example-only path allows inspection while preserving that exception in manifests.
Annual research parsing still rejects Q5/Q6 identifiers.

## Risk, severity and confidence

1. Critical for underwriting research: no matching origination/performance population.
   Confidence high: exact key anti-join counts, reproduced in SQL and notebook.
   Likely cause: these are independent provider format examples, not a linked annual sample.
   Do not “fix” by matching row order or stripping the identifier prefix.
2. High for research representativeness: selection design of this example is not established.
   Confidence high in the limitation; do not infer random sampling.
3. High for legacy formula reuse: Release 47 loss-field sign conventions changed.
   Source confirmed in release notes; loss arithmetic has not been implemented.
4. Medium implementation lesson: the host's shared pytest temp folder denied access.
   Resolved with a fresh project-local test folder, without changing global permissions.

## Temporal interpretation

The performance example has observations across multiple calendar periods,
but that does not repair the failed join or establish a research sample.
The pipeline reports coverage and gaps without inventing pre-acquisition current months.
Monthly D3+ records are not incident defaults; populated loss records are not automatically usable loss labels.
No outcomes have been promoted into model labels.

## Automated controls delivered

- Source download caching and hash checks.
- Exact header comparison to reviewed positional contract.
- Explicit release requirement; no schema inference from vintage.
- ZIP path/symlink/size/member validation.
- Bounded-batch Parquet staging and rejected-line reports.
- Counts/keys/anti-joins/gaps/completeness SQL.
- Research gate rejects format examples even when technical checks pass.
- Raw/synthetic/example/research classifications remain distinct.
- Notebook independently recomputes the saved summary.
- 54 local tests; no model metrics claimed.

## Next action

Obtain a permitted annual sample through https://claritydownload.fmapps.freddiemac.com/CRT/.
Prefer 2012 for the first ingestion spike. Provide the ZIP path and release identity.
Then inspect it using the documented CLI, with explicit internal-research-use confirmation.
Only then assess cohort eligibility and choose additional vintages.

Public real-data publication, full label contracts, model fitting and website replacement remain blocked.
