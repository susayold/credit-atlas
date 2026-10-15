# Candidate temporal protocol — not yet research-approved

Config `configs/split.json` implements the plan's proposed vintage schedule:
train2006–2012; calibration2014; validation2016; final test2018.
The only available vintage is currently2012. Do not replace missing partitions with
random monthly-row splits or silently relax vintage/class-support requirements.

Information cutoffs: initial fitting January2014; calibration fitting January2016;
selection freeze January2018. Training/calibration/validation labels must be known
strictly before their respective cutoff. Same-month label observations are excluded,
because the table represents month-level observations rather than pre-fit publication times.
Scoring landmarks in each later partition must not precede the upstream fit cutoff.
Origination year determines the role, but actual landmark/label dates enforce temporal bounds.

Unique loan IDs must not overlap partitions. Labels lacking outcome or known-month evidence
are excluded with reasons. Unused vintages are retained in the assignment audit as unused.
Each final-test assignment is marked locked; no training consumer should use those rows.
This metadata flag is a workflow control, not a security boundary or proof that test data
has never been viewed. A final-test evaluation/access log remains to be implemented.

The candidate minimum of100positive and100negative observations per partition is an explicit
development guardrail, not a universal statistical sample-size theorem. It cannot replace
power/uncertainty analysis, subgroup support review or study-specific validation.
All required vintages, class support and protocol approval must pass before `training_ready`.

The permitted claim is **retrospective temporal validation using the latest source release**.
The pipeline rejects a strict-PIT claim; historical publication lags and source revisions
are not demonstrated by having an old reporting month in a current download.

Origination preprocessing is allowed to fit only included training rows. Future/terminal
columns cannot enter through config or automatic numeric selection. Actual real-data fitting
has not been performed; currently only synthetic engineering fixtures exercise preprocessing.

Remaining B08: load/qualify all candidate vintages, independent boundary review, model-B
shared-loan protocol, freeze/access logs and signed-off final research split manifest.
