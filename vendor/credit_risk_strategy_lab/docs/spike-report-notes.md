# Source report design and QA

Audience: technical; delivery: private portable HTML in Codex local runtime.
No public hosting or external distribution of real-data output is approved.
Question: can annual sample 2012 support the next engineering blocks?
Answer: initial integrity passes; cohort/label/loss/multi-vintage gates remain.

Structure maps technical specification: title, technical summary, definitions,
event findings, coverage chart, missingness, methods, limitations, next steps,
open questions. Definitions precede evidence to avoid confusing monthly states
with loans or cumulative observations with default12m.

Chart contract: one native line chart, 15 calendar-year observations, x=year,
y=distinct observed loans. Single blue series, no redundant legend. Question is
coverage evolution, not a risk trend. Source rows retain monthly volume, D3 state
rows and populated-loss rows. The partial 2026 year and changing survivor set are
explicitly flagged. Other exact audit counts remain prose/table in technical docs;
they have different denominators and should not be ranked against each other.

Canonical report builder validated/rendered but rejected desktop overflow twice.
One targeted correction wrapped provenance SQL without changing evidence/content.
No final HTML was delivered and no verifier was disabled. The artifact JSON,
generator and failure screenshots remain for follow-up. Data/SQL/notebook results
are independent of the presentation failure.
