# P3.03 — Analysis/Facts Excel audit, checkpoint 15/10/2026

Đã tạo và đối soát toàn bộ 36 export scopes: bốn issuer × cửa sổ 3/5/10 report periods × ba expense concepts tại cutoff 15/10/2026. Workbooks được tạo qua API hiện có bằng bundled Node và Artifact Tool; scripts/node_modules là junction đến bundled dependencies, không dùng library authoring khác. Các XLSX/JSON đều giữ private trên D:.

## Source/API/formula checks

`artifacts/private/sec-workbook-scope-audit-1133f2bb3c7b/receipt.json`: PASS 36 scopes. Mỗi downloaded XLSX được SHA đối sánh với immutable server capture và filters của trend/coverage. Independent XML/Fraction/Decimal audit kiểm tra ratio/delta caches, linked Facts numeric/exact text, missing-input guards, ordered bridge effects/counterfactual/residual, hai sheets và không formula-error cells. Source/code/builder hashes không đổi trong run; holdout access ledger không đổi.

`artifacts/private/sec-analysis-excel-acceptance-tests.xml`: 43 PASS, gồm workbook/filter/source capture, trends/driver bridge và coverage boundaries.

## Native Excel

`artifacts/private/native-excel-qa-sec-1a75771ee189/receipt.json`: PASS đủ 36 workbooks bằng Excel 16.0, CalculateFullRebuild trên disposable read-only copies. Đối chiếu toàn bộ 73.656 populated cells và 14.040 formulas của Analysis/Facts; không lưu bản sao, source bytes giữ nguyên. Formula comparison chỉ bỏ optional quoting quanh hai tên sheet đơn giản; không đổi references/logic. Typed ISO UTC dates đối chiếu bằng native Excel serial/OADate.

Hai lần comparison đầu thất bại được giữ riêng:

- `representation-failure-receipt.json`: khác date-string versus serial và optional sheet quoting; đã phân loại toàn bộ 16.310 mismatches, không có loại khác.
- `timezone-comparison-failure-receipt.json`: PowerShell ConvertFrom-Json đã chuyển ISO value thành DateTime UTC; chuyển lại thành string rồi parse DateTimeOffset gây lùi 7 giờ. Đã xác nhận với cutoff: native 46310, cách parse sai 46309.7083333333; dùng trực tiếp UTC DateTime.ToOADate khôi phục đúng serial.

Các sửa đổi thuộc audit comparison code, không sửa workbook, nguồn SEC, production builder hoặc công thức. Lần chạy cuối 0 failed checks.

## Phần còn lại để đóng P3.03

1. Kiểm tra độc lập toàn bộ Facts metadata/candidate completeness, report dates, source labels/hashes và summary links, không chỉ cached arithmetic.
2. Native input perturbations trên những bản sao hiện tại để chứng minh blank/zero/negative/text và output-summary propagation; baseline recalculation không tự thay thế test input changes.
3. Render trực tiếp hai sheet của current exports, xem source/summary/calculation ranges; kiểm tra lại actual UI download/outage và scope binding.
4. Ghi đầy đủ bằng chứng vào original requirement và chỉ nâng nghiệm thu khi các phần trên hoàn tất.

P3.03 chưa full_completion_proven. Tổng suite vẫn 19/50 = 38%; ratios/coverage là research proxies, chưa EBIT ICR/DSCR/covenants hoặc issuer PD.
