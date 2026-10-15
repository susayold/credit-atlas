# P3.02 — kiểm kê độc lập SEC normalization

Checkpoint này mô tả audit trước nghiệm thu. Cập nhật 15/10/2026: đã hoàn tất serving cache, API/browser/export evidence và đóng P3.02; xem [P3_SEC_NORMALIZATION_ACCEPTANCE_VI.md](P3_SEC_NORMALIZATION_ACCEPTANCE_VI.md). Các phần runtime còn phải làm phía dưới là lịch sử checkpoint, không phải trạng thái hiện tại.

Case `sec-case-33077fe45722`, nguồn `sec-source-13cf03606e0c`, bốn issuer AAPL/MSFT/Ford/GM. Source hiện có 14 HTTP JSON files; đây là current API snapshot, không phải certified historical publication archive.

## Audit đã thực thi

`artifacts/private/sec-normalization-acceptance-e466059ee35f/receipt.json`: PASS.

- 105.441 fact entries: raw JSON Decimal → canonical Parquet, exact row parity theo CIK/taxonomy/concept/unit/source ordinal; giữ native units và annotation/extra JSON.
- 13.374 unique filings và 13.374 occurrence records: tất cả submissions/history arrays đối soát với canonical filings và occurrence records. Conflicting occurrences không được chọn tùy ý.
- Toàn bộ concept definitions và source-quality metrics của bốn issuer khớp nguồn.
- 67 annual statements × 8 fields = 536 field states: 468 supported, 48 missing, 20 ambiguous. Candidate evidence được xây độc lập từ raw facts, không gọi production adapter/statement/verifier.
- Chọn đúng CIK/accession/form/filed date/end date, taxonomy us-gaap và unit USD. Instant không có duration; annual candidates đủ 330–400 inclusive days. Không ghép quarter/YTD hoặc lấy comparative từ accession khác.
- Equal-value/equal-period candidates giữ đủ evidence; differing values/periods ambiguous, không chọn alias đầu tiên. Missing/ambiguous giữ null, không zero fill hoặc FX-convert.
- Raw/canonical/receipt SHA kiểm tra trước và sau audit; code pin của canonical case giữ nguyên. Không fit/inference hoặc đọc Retail final predictors.

Audit lần đầu bị MemoryError khi chuyển toàn bộ Parquet thành Python list. Phiên bản cuối đọc batch 512 rows, vẫn so sánh tất cả records theo unique source keys và exact dictionaries, không sampling hoặc giảm scope. Source/canonical artifacts không thay đổi.

## Tests

`artifacts/private/sec-normalization-acceptance-tests.xml`: 33 PASS, gồm production normalization/views guards và independent-audit cases. Cases độc lập kiểm tra quarter/YTD, issuer filing/unit mismatches, equal/conflicting candidates, annual start conflicts, instant zero và unknown taxonomy.

## Runtime còn phải chứng minh

`scripts/browser_sec_normalization_acceptance.py` đang kiểm tra report API cho đủ 67 statements, bốn latest UI/export field tables, missing/ambiguous, cutoff, reload/mobile và origin/scope guards.

Lần đầu runtime QA gặp report HTTP 503; HTTP request sau đó đã trả 200 và report trực tiếp trong process riêng chạy PASS. Chưa đủ chứng cứ kết luận nguyên nhân của HTTP 503. Chỉ PASS receipt đầy đủ trên runtime mới có thể đóng phần này.

Lần chạy HTTP tiếp theo cũng dừng với 503, query `sec-view-b92d9914f1dc`, CIK `0000320193`, accession `0000320193-20-000096`, cutoff `2026-10-14`. Hai lần không tạo PASS receipt; các thư mục output chưa hoàn tất không dùng nghiệm thu. `scripts/diagnose_sec_sequential_reports.py` kiểm tra tuần tự tất cả report bằng production SecViews trong process riêng và lưu traceback khi có lỗi; đây là diagnostic, không thay thế browser acceptance. Cần xử lý runtime trước khi đóng P3.02.

P3.02 chưa được nâng full_completion_proven tại checkpoint này. Phần audit độc lập đã hoàn tất nhưng API/browser/export acceptance vẫn cần xác minh. Ratios/trends/debt/memo là các yêu cầu riêng, không được đóng chỉ từ kết quả normalization.
