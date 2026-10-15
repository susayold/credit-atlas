# Canonical contract — Release 47

Source authority: cached `guide.pdf`, General User Guide July 2026, pp4–17;
official header and XLSX layout positions were checked in the source spike.
This is a local research data contract, not a lending production schema.

## Tables and provenance

- `dim_loan`: one row per source loan_id, per release. No borrower identity claim.
- `fact_loan_month`: one row per loan_id and month, per release.
- Every original source field remains as `raw_<field>`; source line and release persist.
- Canonical fields keep source names. Months become DATE at month start, not exact transaction dates.
- USD fields use DECIMAL(18,6); integer-coded measures are checked before casting.
- Interest rates, DTI/LTV/CLTV/MI and ELTV remain percentage points, NOT fractions.
  A 4.5 interest rate means 4.5%, not 450%; consumers must divide by 100 explicitly.
- Source IDs, postal codes, MSA and seller/servicer attributes remain private.
- Acquisition is observation entry, not the annual sample vintage label.
  Origination year/quarter follows the documented loan ID components.
  First payment date can differ from vintage; never replace the source vintage with it silently.

## Field-specific missingness

| Fields | Null sentinel | Preserve |
|---|---|---|
| Classic FICO, VantageScore | 9999 | Valid 300–850 |
| MI, original LTV/CLTV/DTI, ELTV | 999 | MI=0, DTI=0 are real values |
| Units, borrowers, property type | 99 | Pre-2018Q2 borrowers=2 means more than one, not exactly two |
| First homebuyer, occupancy, channel, purpose | 9 | Source categories retain their original semantics |
| Property valuation, MI cancellation | 7 | Not available/not applicable, not category 7 model input |
| Postal code | 000 | Other strings retain leading zeroes |
| Other fields | blank only | Dollar amount 999 or actual loss 0/-10 stays numeric |

MSA blank may mean outside MSA or unknown. It cannot be labeled simply as a broken field.
Missing disaster/assistance before 2014 and MI cancellation before 2015 are structural
availability limits; do not impute those historical blanks as observed negative evidence.
ELTV is populated only from April 2017; property valuation only for origination from 2017.

## Independent state and termination axes

Numeric delinquency 00/01/02/03–99 maps CURRENT/D1/D2/D3PLUS; RA maps REO,
XX maps UNKNOWN. Do not fabricate exact days by multiplying the source code by 30.
For periods through September 2025, 00 may include the cycle before first payment.

Termination 01 = PREPAID_OR_MATURED; 02/03/09 = CREDIT_TERMINATION;
15/16/96 = OTHER_TERMINATION. Whole-loan sales (15) are not automatically default.
Preserve delinquency and termination side by side rather than overwriting one with the other.

`is_relief_refinance` = raw HARP indicator Y. `is_harp_subset` additionally requires
original LTV >80; unknown LTV propagates unknown rather than guessing membership.
Guide p5 says all HARP DTI is unavailable; measured 2012 Relief Refinance group has
17,399 of 17,399 DTI nulls, plus 1 non-Relief record with DTI null.

## Assertions and limitations

Unknown source enum, nonintegral integer input, duplicate keys, missing parent/child
history and join fan-out fail closed. Staging and raw values are not overwritten.
Date/type checks already passed at ingestion; casts add a second failure point.
Canonical completion certifies this transformation, not all B03/risk model gates.
Legal/privacy review, source revisions and complete range validation across vintages remain separate.
