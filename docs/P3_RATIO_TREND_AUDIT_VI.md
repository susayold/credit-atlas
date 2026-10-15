# P3.03 — audit ratios, annual trends và coverage

Checkpoint 15/10/2026. Yêu cầu P3.03 gồm ratio cards, actual/delta tables, numerator-first driver bridge, baseline statements, interest-coverage evidence, JSON và Analysis/Facts Excel. Audit này chưa tự đóng toàn bộ yêu cầu Excel.

## Ratios và trends đã kiểm tra

`artifacts/private/sec-ratio-trend-audit-80083cbd6087/receipt.json`: PASS.

- Toàn bộ 67 source statements × bốn ratios = 268 cells. 201 supported và 67 missing_or_ambiguous_input. Tử/mẫu đúng field definitions; annual start alignment, positive denominator và exact values khớp Fraction → Decimal precision 60. Không thay missing/ambiguous bằng zero.
- 48 actual API scopes: bốn issuers × bốn cutoffs (2000/2010/2018/2026) × cửa sổ 3/5/10 report periods. Independent selection dùng source statements đã được raw-to-canonical audit ở P3.02; không gọi production derive_trend/comparison/driver_bridge để tạo kết quả mong đợi.
- Original 10-K được chọn khi duy nhất; amendments giữ riêng. Baseline được xác định trước khi cắt cửa sổ; không skip period thiếu/ambiguous để chọn baseline đẹp hơn. Tập filings, selected statement và baseline khớp trong từng API period.
- 552 comparison cells theo scopes: 360 COMPARABLE, 154 UNSUPPORTED_RATIO_INPUT, 28 NO_PRIOR_PERIOD, 10 CONCEPT_MAPPING_CHANGED. Gap/kind/unit/duration gates còn được kiểm tra bằng synthetic tests khi corpus thực không có case tương ứng.
- 360 supported driver bridges: prior/current numerator/denominator, baseline/counterfactual/current ratio, numerator/denominator effects, total delta và rounding residual khớp Decimal và exact rational identities. Negative/nonpositive baseline không tạo relative growth; effects là arithmetic attribution, không causal explanation.
- 36 tests PASS: `artifacts/private/sec-ratio-trend-acceptance-tests.xml` (trends, driver bridge và coverage boundary cases).

Browser `artifacts/private/sec-trends-qa-eb2275a0fceb/receipt.json`: sáu nhóm PASS, gồm bốn issuers five-period UI/private exports, exact ratio/delta/bridge checks, 3-period/reload/mobile, controlled API outage/recovery, pre-source cutoff empty và holdout ledger không đổi. 67 supported ratio checks trong exports five-period là subset khác với 201 supported cells của full source; không cộng hai counts.

## Coverage đã hoàn tất phần source/API/browser

`artifacts/private/sec-coverage-scope-audit-feedcb985862/receipt.json`: PASS ba expense concepts × bốn issuers × năm cutoff/window choices (60 scopes). Đã kiểm tra 1.545 field cells, 801 candidate evidence entries và 618 ratio cells qua các scopes: 136 supported, 482 missing_or_ambiguous_input. Counts có lặp khi cùng period xuất hiện ở nhiều window/cutoff/concept, không phải unique source facts.

Raw candidate checks giữ interest expense và cash interest paid/net riêng; explicit concept không fallback/sum aliases hoặc infer EBIT/DSCR. Ratio statuses được suy độc lập theo support/alignment/positive-expense gates; unsupported value giữ null, negative supported numerator được giữ. Synthetic tests bao phủ period-mismatch/nonpositive-expense cases ngoài những statuses thực có trong corpus.

`artifacts/private/sec-coverage-qa-e8ff0e355242/receipt.json`: PASS actual UI/download cho bốn issuer, explicit expense selection, period selector/reload/mobile và API outage/recovery. AAPL/GM latest expense thiếu được giữ unavailable; Ford negative numerator không bị clip; ledger giữ nguyên. Source/canonical/production methods không thay đổi.

## Còn lại trước nghiệm thu P3.03

1. Ratio/trend và coverage receipts đã được ghi vào partial evidence của P3.03; chưa nâng trạng thái nghiệm thu.
2. Audit current Analysis/Facts Excel theo đầy đủ source/filter/formula/precision/missing contracts và kiểm tra UI/download. Native Excel baseline/representative checks đã có từ trước nhưng không tự là full qualification của mọi scope.
3. Đối chiếu tất cả outputs/acceptance của P3.03, giữ nguyên scope và chỉ nâng full_completion_proven khi đủ bằng chứng.

Operating-income/interest-expense và reported-OCF/interest-expense vẫn là explicit proxies. Chưa là standard EBIT ICR, DSCR, contractual covenant hoặc issuer PD. Current SEC API cutoff không chứng minh historical byte availability.
