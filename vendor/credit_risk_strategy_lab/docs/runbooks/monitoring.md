# Research monitoring runbook

## Purpose

This runbook describes checks that would run after a release. It is a
research/QA workflow, not proof that a production lender service exists.

## Checks

1. Verify source freshness against the declared as-of date and maximum age.
2. Validate schema and required-field missingness with explicit support,
   warning, and block thresholds.
3. Compare categorical distributions against a frozen reference population.
   The divergence score is not interpreted when either sample is below the
   minimum support.
4. Calculate outcome rate only for mature, known labels. Immature observations
   are excluded, not treated as zero events.
5. Review policy mix and model calibration only when the associated target and
   evaluation cohort are available.

## Synthetic incident flow

`triage_incident` accepts named check results and current/previous config hashes.
Any failed check selects the previous config and records a rollback action. The
fixture is explicitly marked synthetic and cannot be called a production
incident. A real deployment would add an owner, ticket, approval, audit log,
and a post-rollback verification.

## Current project boundary

The one-vintage 2012 source does not provide production monitoring data or
validated model outputs. The project therefore ships the deterministic
monitoring primitives and tests, while model calibration/drift gates remain
unavailable until multi-vintage model evaluation is completed.
