# Behavioral early-warning research card

## Question

Which funded loans have a higher observed probability of reaching D3 in the
next 12 months, conditional on being observable and not already in D3/REO at
the landmark?

## Feature contract

`crsl.behavioral.build_landmark_features` creates one row per eligible
loan-month. Current delinquency state, current UPB availability, trailing
3/6/12-month state counts, usable-state share, current streak, history gaps,
and change from the prior observed UPB are calculated from observations at or
before the landmark. A changed future row must not change a past landmark row.

The target is 1 only when D3 is observed before a competing exit. It is 0
after a complete horizon with no D3, or after a competing exit observed before
D3. Gaps, unknown states, and administrative censoring remain unavailable.

## Baseline and optional model

`current_state_baseline` is the primary descriptive baseline. It reports the
observed event rate and support by current state and excludes unavailable
targets from both numerator and denominator. `BehavioralLogistic` is a tested
optional challenger with a fixed numeric feature list and current-state
indicators. It requires unique one-landmark-per-loan training rows, a date
cutoff, both classes, and explicit evidence class.

## Current evidence status

The available Freddie Mac source is one 2012 annual sample. That is enough to
test feature lineage and produce a descriptive development table, but not to
claim out-of-time performance, intervention uplift, production monitoring, or
collections effectiveness. The real model fit remains gated until additional
qualified annual vintages and a frozen temporal protocol are available.

Already-event landmarks are excluded. A behavioral priority signal is not an
approval decision, adverse-action reason, or treatment recommendation.
