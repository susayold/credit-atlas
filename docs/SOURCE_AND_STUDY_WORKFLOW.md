# Source import and temporal-study preparation

All new workspace files stay on D:. The user resumed acquisition on 2026-10-09;
additional Clarity annual samples require a login session that is not yet available.
The code below supports authorized local ZIPs and authenticated HTTP downloads.

Three public FRED macro series were acquired and a 171-month retrospective
context run completed. See [PUBLIC_MORTGAGE_CONTEXT.md](PUBLIC_MORTGAGE_CONTEXT.md)
for files and limits. These do not qualify the loan-model temporal study.

## Import a local authorized annual ZIP

1. Preserve the original source ZIP and release identity.
2. Compute and record SHA-256, e.g. Get-FileHash -Algorithm SHA256.
3. Confirm permitted internal research use for that file.
4. Run import-annual with archive, release 47, expected-sha256 and the explicit
   research-use-confirmed flag.
5. Use the returned asset index for rebuild; then build-snapshot for the newly
   returned case directory.

Example argument structure, substituting the actual path and lowercase digest:

    .\.venv\Scripts\python.exe -m credit_atlas.cli import-annual --archive <actual-zip-on-D> --release 47 --expected-sha256 <actual-sha256> --research-use-confirmed
    .\.venv\Scripts\python.exe -m credit_atlas.cli rebuild --asset-index <returned-index>
    .\.venv\Scripts\python.exe -m credit_atlas.cli build-snapshot --case <returned-private-case-directory>

Release 47 pairs are sample_orig_YYYY.txt and sample_perf_YYYY.txt. Legacy
sample_svcg names and public format examples do not meet this contract.
Member validation, CRC and digest checks establish archive integrity; they do
not authenticate sampling design or substitute for the source-use attestation.

Registry changes are atomic under a single-writer lock. Previous config and
registration receipts are preserved privately. Reimporting the same immutable
registered reference is idempotent. A different reference for an existing
digest, conflicting receipt or other writer's lock is rejected.

Parsing, referential integrity, annual identity and history-presence gates must
pass before foundation analytics. Qualification remains source/cohort-specific;
registration does not activate model fitting or approve public release.

## Prepare a temporal study

    .\.venv\Scripts\python.exe -m credit_atlas.cli prepare-study --case d01-a24484b21a21

Repeat --case for additional verified annual cases. An optional --protocol
points to a local JSON protocol. By default the command uses the pinned engine's
candidate split protocol:

- Train: 2006–2012, fit cutoff January 2014.
- Calibration: 2014, fit cutoff January 2016.
- Validation: 2016, selection cutoff January 2018.
- Final test: 2018, locked for model selection.

Chronology, loan uniqueness, label-known cutoffs and scoring timing are checked
by the existing domain engine. Pooling two rebuilds of the same annual vintage
is rejected, preventing duplicated samples from inflating apparent support.

The command writes a schema-2 private study receipt, split assignments, support
audit and the original protocol bytes in protocol.json. The protocol hash and
decoded configuration must both match on later reads. Older schema-1 preparation
receipts are retained as historical artifacts; rerun prepare-study before using
the feature command.
It logs access intent before reading labels, including whether final-test source
counts may be inspected for support/timing audit. This log does not reconstruct
all previous dashboard access or justify calling such cohorts untouched.

## Current actual-data result

Study study-e7b5a47685c1 has 50,000 source labels. Included training support is
100 positive / 43,227 negative; calibration, validation and test support are
zero. Missing vintages, insufficient class support and candidate protocol
approval remain blockers. Feature qualification and study freezing also remain
separate requirements.

Even a split-ready dataset is not automatically model-fit-ready. prepare-study
never fits models, calibrates, selects a champion, unlocks final-test evaluation
or changes the pinned engine's candidate protocol.

## Audit development features

    .\.venv\Scripts\python.exe -m credit_atlas.cli prepare-features --study study-e7b5a47685c1

Use the actual study ID returned by prepare-study. This command:

1. Verifies prepared digests, saved protocol bytes, source case receipts,
   engine commit, target and non-overlapping vintages.
2. Logs access before rereading labels to rederive the saved split assignments
   and support audit. The log declares whether final-test label counts may be
   read; this is not a claim that those counts remain untouched.
3. Joins only included train/calibration/validation rows to the pinned
   origination allowlist. Final-test predictors are not materialized or scored.
4. Fits imputation, scaling and category vocabulary on included train only,
   then audits development transforms without changing fitted state.
5. Reports per-partition missingness and unseen categories. All-missing training
   fields require reviewed exclusion/ablation; engineering fallback is not
   feature qualification.
6. Saves JSON encoder/config/coverage and reconciles restored encoder vectors
   to native vectors across every development row.

Current actual feature audit: feature-audit-585be3bb2299, 43,327 included train
loans, no calibration/validation rows and no all-missing allowlisted training
field. Restored transform parity passes. The study remains unqualified.

No constant/logistic/boosting risk model is fitted by this command; it produces
no predicted probabilities, model metrics, champion or final-test assessment.
If there are no included training rows, encoder availability is explicitly
unavailable. Invalid/changed artifacts retain failure receipts and are not
presented as completed work.

The Models & validation screen reads aggregate preparation/feature-audit status
through /api/studies. It shows only related verified case evidence, flags legacy
or changed artifacts and caps each artifact scan at 100 recent receipts. It
does not expose raw loan identifiers, private paths or fitted risk scores. Prepared-study support covers the whole
study; segment, monthly range and display-basis controls do not refit or
repartition these cohorts.

The next command is assess-study. Support/review gates, train-only tuning,
same-cohort challenger/calibration and artifact verification are documented
in DEVELOPMENT_ASSESSMENT.md.
