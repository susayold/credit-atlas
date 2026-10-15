# B10: portfolio anatomy evidence

The private run `portfolio-profile-8f848e0a5609` uses the hash-verified
`canonical-f7322e3f7bc4` `dim_loan` table. It produces 102 aggregate buckets
across 13 origination dimensions and the observed `relief` / `non_relief`
segments. Every dimension reconciles back to its segment loan count. Count share
and opening-principal share are calculated independently; missing or unavailable
values are retained as explicit buckets.

## Measured observations

- The sample contains 32,601 non-Relief and 17,399 Relief loans. This is a
  funded-loan sample split, not a customer or application-funnel population.
- Classic FICO below 680 represents 3.2% of non-Relief loans versus 13.4% of
  Relief loans. The corresponding opening-principal shares are 2.5% and 13.2%.
- Original LTV at 96+ represents 41.8% of Relief loans and 47.7% of Relief
  opening principal, while it is 0.1% of non-Relief loans by count. This is a
  descriptive mix difference, not evidence that Relief caused the mix.
- Original DTI is unavailable for all 17,399 Relief loans in this sample. It is
  therefore not a valid Relief-versus-non-Relief comparison variable here; the
  missingness itself must be shown and may reflect source disclosure rules.
- Primary occupancy is 90.8% of non-Relief loans and 87.3% of Relief loans. The
  principal shares are 92.0% and 87.4%, respectively.

These findings are deliberately descriptive. The most plausible alternative
explanations for the Relief mix differences include program eligibility and
selection, refinancing timing, origination-year composition within the sample,
and source disclosure/suppression. The profile cannot distinguish these causes,
and it contains no borrower linkage or counterfactual treatment outcome.

## Reproduction and delivery

```powershell
python -m crsl.portfolio_profile --canonical-run artifacts/private/canonical-f7322e3f7bc4
python -m crsl.workbook_data --pipeline-run artifacts/private/pipeline-83667cc64126 `
  --segmented-run artifacts/private/segmented-transitions-5f034c3464c3 `
  --profile-run artifacts/private/portfolio-profile-8f848e0a5609
```

The aggregate is displayed on the local Portfolio page, appended to the
`03_Portfolio` worksheet, included in the private report contract and exported
as `data/aggregate/portfolio-profile.csv`. The profile Parquet and all loan-level
inputs remain private.
