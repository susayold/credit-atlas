# ADR-001: Separate mortgage flagship

Status: ACCEPTED by user approval to implement V4, 2026-09-09.

Create a new local project at outputs/credit-risk-strategy-lab.
The previous project has no Git repository at its root; do not initialize or modify it.
Initialize version control only inside the new project. No remote push or publication.

Keep the Prosper project, data, virtual environment and running website unchanged.
Do not reuse Prosper status, label, cohort, model or loss logic.

Consequences:
- Explicit U.S. mortgage domain in all future artifacts.
- Source and publication gates precede research/model release.
- Research dataset access may require direct user action.

