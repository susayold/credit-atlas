# P3.02 — nghiệm thu SEC financial normalization

Đã đóng yêu cầu P3.02 trong scope source-native, filing-specific research đã nêu ở plan. Scope vẫn là bốn issuer AAPL/MSFT/Ford/GM, tám supported financial-field families; không phải complete statement/custom-XBRL parser, issuer rating/PD hoặc historical point-in-time archive.

## Dữ liệu và numerical evidence

Audit độc lập `private evidence omitted from public release` PASS toàn bộ 105.441 source fact entries, 13.374 filings và occurrence records, concept definitions và quality metrics. Raw JSON đọc Decimal, canonical Parquet đọc batch 512; so sánh exact full rows theo source keys, không sampling. Case/raw/receipt/method hashes giữ nguyên.

67 annual statements × tám fields = 536 field states: 468 supported, 48 missing, 20 ambiguous. Mọi candidate evidence và field values/status khớp independent raw-fact selection. CIK/accession/form/filing date/start/end/unit/taxonomy giữ riêng; annual candidates đủ 330–400 inclusive days, không ghép quarterly/YTD theo FY. Conflicting value/period không chọn alias đẹp hơn; missing/ambiguous giữ null; native EUR/shares/pure/USD-per-share không chuyển thành USD.

Chi tiết audit trước nghiệm thu: [P3_SEC_NORMALIZATION_AUDIT_VI.md](P3_SEC_NORMALIZATION_AUDIT_VI.md).

## Serving cache

`src/credit_atlas/sec_read_cache.py` bổ sung VerifiedSecReadCache ở HTTP handler cho production SecViews instances. Không sửa các pinned core modules sec_sources/sec_financials/sec_views/workspace.

Lượt đầu vẫn dùng nguyên verifier để rederive và đối soát toàn bộ source/canonical/projected view; đầu vào được hash trước và sau. Các lần đọc tiếp theo kiểm tra lại hashes của toàn bộ raw files, canonical files, receipts, view và core methods, chỉ reuse projection nếu graph byte-identical. File bị sửa, method bị sửa, verification thất bại hoặc dữ liệu đổi trong lần verify đều fail closed. Lock tránh nhiều cold verifications chạy đồng thời; projection trả về là deep copy; tối đa tám view entries trong cache.

`private evidence omitted from public release`: tám lượt đọc song song và 67 annual report parities PASS, original full-verifier call count = 1, đủ 28 pinned input paths được hash mỗi lần. Không model fit/inference hoặc mở Retail final predictors; holdout ledger giữ nguyên.

## API/app/export

`private evidence omitted from public release`: PASS trên server hiện tại:

- Cả 67 annual statement reports qua HTTP khớp exact saved statements và giữ historical_availability_qualified=false.
- Bốn issuer latest UI: 32 field rows khớp status/exact USD values/start/end/evidence counts; downloaded JSON khớp nguồn.
- Issuer/accession/cutoff phục hồi qua reload; mobile không page overflow và screenshot đã xem trực tiếp.
- Cutoff không có supported filing giữ absence, không lấy future fallback; invalid accession/cutoff scope và cross-origin bị reject.

42 SEC/cache tests PASS (`sec-read-cache-tests.xml`), gồm core/views và independent audit boundary cases. 31 HTTP regression tests PASS (`sec-cache-http-regression-tests.xml`), gồm các module khác và private/origin/export guards. Hai suite có overlap ở cache tests; không cộng chúng thành số unique tests.

## Sự cố đã ghi nhận

HTTP QA cũ gặp 503; direct sequential production verifier lại PASS đủ 67. Chưa có traceback đủ để kết luận nguyên nhân của 503 cũ. Khi dựng server diagnostic, server cũ vẫn giữ cổng 8770; các owned QA/server processes sau đó được dừng và chạy lại một server duy nhất với code hiện tại. Không dùng những lần QA này làm bằng chứng PASS.

Sau cache, QA đi qua đủ 67 HTTP reports nhưng assertion UI ban đầu thất bại vì test tự sắp xếp field alphabetically. App/API giữ source field order; đã sửa expectation đúng thứ tự nguồn. HTTP regression có một lần Fannie timeout khi chạy cùng các probe; lần chạy lại toàn suite sau đó PASS 31 tests, không thay timeout hoặc bỏ test.

Current PASS chứng minh scope runtime đã kiểm tra, không khẳng định mọi điều kiện tải/memory hoặc production operation đã qualified.

## Phần còn mở

Current SEC API không chứng minh byte availability tại lịch sử filing dates; custom/dimensional disclosures và complete accounting equivalence còn thiếu. Ratios/trends/interest coverage, debt service/covenants và corporate memo là các mục riêng P3.03/.06/.07/.08/.10, không tự đóng từ normalization.

Sau recorder kiểm tra evidence và ghi P3.02, tổng suite là 19/50 = 38%; original scope/checkpoint labels giữ nguyên. Goal 100% chưa hoàn thành.
