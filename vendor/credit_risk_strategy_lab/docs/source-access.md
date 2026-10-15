# Source access — Release 47

Update 2026-09-10: authenticated access succeeded and the user downloaded
`sample_2012.zip` (70,532,871 bytes). Private annual ingestion passed on 50,000
loans and 4,510,559 loan-month rows. This resolves the original access blocker
for 2012 only; it does not approve public distribution. See data-qualification.md.

Official landing:
https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset

Annual samples:
https://claritydownload.fmapps.freddiemac.com/CRT/

The annual download route returned HTTP 401 to unauthenticated access during this run.
We did not attempt to bypass authentication.

The public Release 47 format example ZIP is accessible without that login.
It is **not assumed to be the official annual random sample**, even if its files contain
plausible loan records. Its selection design is not established.
It can validate parsing, but cannot pass the research/modeling gate.

## Required user action

1. Register/sign in to Clarity personally.
2. Review/accept applicable terms yourself if appropriate.
3. Download an annual sample (prefer 2012 for the first spike), not merely
   the 'Release 47 Sample Files' format example.
4. Keep the original ZIP; provide its path and release identity.
5. Confirm internal research use is permitted. Do not share credentials.
6. Run inspect-annual or ask the agent to run it using that file.

A single annual sample cannot approve all train/calibration/validation/test splits.
Additional years are selected only after the first actual qualification.

## Current source conventions

Use the official July 2026 layout and headers for Release 47.
Do not infer schema from origination vintage or guess a missing version.
Recoveries/gains have negative signs in the new release; loss/expense signs differ
from legacy releases. Loss arithmetic is not implemented by this source spike.

Reference:
https://www.freddiemac.com/fmac-resources/research/pdf/release_notes.pdf
