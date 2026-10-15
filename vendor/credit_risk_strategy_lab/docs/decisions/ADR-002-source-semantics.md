# ADR-002 — Source semantics corrections and development cohort

Status: adopted for development following user authorization to use technical judgment.
Date: 2026-09-10. Authority: July 2026 General User Guide, pp3,5,7–10,13,16–17.

1. Correct earlier notes calling annual samples acquisition vintages. The guide explicitly
   defines origination quarter; performance begins at acquisition. All sample2012 IDs
   carry year12, while first-payment dates span February2012 to March2015.
2. Raw HARP=Y is Relief Refinance. HARP subset requires original LTV>80.
   2012: 17,399 Relief Refinance loans, 11,121 HARP-subset loans.
3. No numeric VantageScore signal in 2012: all50,000 values are9999.
   DTI missingness largely follows source disclosure; do not invent an income proxy.
4. Primary development labels use an early-entry first-observed landmark, not assumed
   unobserved history from origination. Keep late-entry attrition visible.
5. Numeric D3, REO and credit/other exits are distinct. Whole-loan sales are not default.
6. Code09/02/03/15 actual-loss rows reconcile with signed components; all374 reported
   rows match exactly. Six missing losses have defect dates; one is recent disposition.
   Formula validation is not permission to train unconditional loss models on resolved loans.

The full multi-vintage/model/forecast/website/Excel objective is unchanged.
Only sample2012 is currently available. Expired Clarity authentication blocks further
downloads, not local engineering and descriptive analysis. No external accounts,
terms acceptance, raw redistribution or fake research results are authorized by this ADR.
