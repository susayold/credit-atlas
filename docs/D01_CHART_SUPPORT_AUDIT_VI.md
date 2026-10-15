# D01 descriptive chart and support audit

Date: 2026-10-15. Case: `d01-a24484b21a21`, pipeline `pipeline-307c354f3d74`.

This audit checks the values and denominators supplied to the descriptive charts against the frozen snapshot and their service projections. It complements browser QA, which checks that the chart series render and the selected views, filters, and support cards remain usable. It does not qualify a predictive model or establish that the supplied sample represents the mortgage market.

The six checks passed:

| Chart or view | Audit result |
|---|---|
| Monthly active stock and D3 stock share | 513 total and segment month-points; count and UPB shares reconcile to state-usable active denominators. A missing D3 balance remains unavailable when D3 loans exist; no D3 loans yields a known zero share. |
| Vintage competing incidence | All 9 segment × horizon rows (3 segments × 6/12/24 months) have valid support; source, eligible, excluded, observed event, and at-risk counts stay within their contracts. |
| Origination profile | All 26 segment × dimension groups have count and opening-UPB shares summing to one with stable within-group denominators. |
| Annual transition matrices | 1,091 rows across 214 year/segment/origin groups reconcile pair counts and count probabilities. |
| Lifetime transition comparator | 94 rows across 15 segment/origin groups reconcile; balance probability coverage preserves missing opening balances. Frozen-engine reconciliations pass. |
| Signed observed-loss bridge | 374 resolved loans reconcile to $18,659,957.55; 7 unresolved terminal loans remain separate and expected loss remains unavailable. |

Browser acceptance also confirms the portfolio stock/share charts, all three competing-incidence series and their risk-set support, and the signed loss component chart render together with the relevant denominator or unresolved-support text. It clicks a sparse transition cell and confirms the distinct-loan warning. The expanded run passes 39 browser checks, including 390px mobile overflow checks for portfolio, vintage, transitions, loss, and models plus fail-closed stale-evidence, missing-run, unlisted-run, connection-failure, and malformed-JSON states.

Evidence: [chart/support receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [browser QA receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). Re-run with `PYTHONPATH=src python scripts/audit_d01_chart_support.py` and `PYTHONPATH=src python scripts/browser_qa.py`.

This closes the specific pending chart/support audit under M01-024. It does not close M01-024 overall: actual mortgage model fitting/validation remains blocked by missing vintages and readiness gates, and multi-vintage descriptive comparisons remain open.
