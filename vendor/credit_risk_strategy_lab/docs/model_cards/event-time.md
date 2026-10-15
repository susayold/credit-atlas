# Competing-event evidence card

`crsl.models.event_time.validate_curve` validates cumulative incidence rows for
D3, prepayment, and other exit. Each event probability stays in `[0, 1]`, the
sum stays within probability mass, and each mature segment is non-decreasing
over horizon. Immature cells are not filled.

`binary_vs_competing` makes the estimand difference explicit. A binary
12-month rate and a D3 cumulative incidence answer different questions when a
loan can prepay or leave for another reason before D3. The source currently
supports a verified descriptive 2012 curve, not a cross-vintage covariate
hazard model.
