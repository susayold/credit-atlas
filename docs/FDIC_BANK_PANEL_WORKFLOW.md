# P4 — FDIC historical bank panel

09/10/2026. Current acquisition: `fdic-history-3e5ccce29513`; verified panel:
`bank-panel-13a7ad74220f`. Historical descriptive foundation và
[P4 observatory app](BANK_APP_WORKFLOW.md) đã chạy; chưa có bank-failure model.
Freddie Mac thêm vintage vẫn chờ Clarity login.

## Coverage và nguồn

**42/42 quý 2016-03-31–2026-06-30**, **214.809 bank-quarter records**, **6.290
CERT khác nhau** trong cả giai đoạn. 42 financial JSON + definitions/OpenAPI =
**40.046.591 bytes**. Raw ở
`data/private/bank-history/fdic-history-3e5ccce29513/` với start, per-source và
completion receipts: URL, SHA-256, bytes, retrieval time, counts và field contract.

API chỉ filter REPDTE, không thêm ACTIVE/INSURED/class: population này không
đồng nhất với tập ngân hàng hiện đang hoạt động hoặc một dashboard khác.
Returned rows phải bằng meta.total, dưới 10.000, CERT×REPDTE unique và đúng quý.
Nếu đạt 10.000 cần review pagination; hiện tất cả 42 responses complete.
HTTP downloader dùng official FDIC HTTPS hosts, không credentials/computer use,
không automatic redirects; tối đa hai workers, 32 MiB/file, timeout 120 giây.

Nguồn chính thức:

- [API documentation](https://api.fdic.gov/banks/docs).
- [Financial field definitions](https://api.fdic.gov/banks/docs/risview_properties.yaml).
- [OpenAPI](https://api.fdic.gov/banks/docs/swagger.yaml): DEP example dùng thousands of dollars.
- [Official monetary display](https://banks.data.fdic.gov/bankfind-suite/financialreporting/report?reportPeriod=20260630&unitType=%24): Values in Thousands USD.

Link YAML tương đối có thể resolve sai nếu thiếu `/docs/`; dùng official path
đã đọc được. Attempt `fdic-history-43e3e6c96219` dừng trước khi tải quarters
vì trang giao diện HTTP chỉ trả JavaScript shell. Failure receipt giữ nguyên.
Đợt thành công lưu downloaded OpenAPI và reviewed official-display provenance.

## Contract

| Field | Meaning / canonical |
|---|---|
| CERT | Institution certificate; cert int64, không phải loan ID |
| REPDTE | report_date: quarter-end, chưa biết historical publication date |
| NAME | Institution name |
| ASSET | assets_usd_thousands; on-balance-sheet assets |
| DEP | deposits_usd_thousands; gồm foreign-office deposits |
| EQ | equity_usd_thousands; stock/surplus/undivided profits, book equity |
| ROA | roa_annualized_percent; after-tax annualized income / average assets |
| CERTCONS | consolidating_parent_cert khi parent consolidates institution financials |

Money phải integral int64; fractional values bị từ chối, không silently round.
Null/blank giữ NULL, signed values giữ nguyên. ROA finite double, không scale
1.000. EQ/ASSET×100 và DEP/ASSET×100 chỉ tính khi numerator biết, ASSET dương.
Book equity ratio không phải CET1/Tier 1/RWA. Official ROA formula dùng
NETINCA/ASSET5; không thay bằng ending assets.

Custom contemporaneous asset bands: dưới $100m; $100m–dưới $1bn;
$1bn–dưới $10bn; $10bn–dưới $100bn; từ $100bn; unknown/nonpositive riêng.
Đây không phải FDIC regulatory peer groups. Marts dùng unweighted bank median
ROA với nonmissing counts, không gọi ending-ASSET weighted mean là industry ROA.

## Outputs và kiểm tra thật

Trong `artifacts/private/bank-panel-13a7ad74220f/`:

- `bank-quarter.parquet`: 214.809 rows × 12 typed canonical fields.
- `peer-quarter.parquet`: quarter/asset band, records, money sums/known counts,
  median ROA/book-equity ratio và consolidation/quality counts.
- `matched-quarter-changes.parquet`: 208.518 matched adjacent-quarter records,
  paired asset known counts và exact asset change. Không nối qua quarter gaps.
- `field-contract.json`, `panel-complete.json`: definitions/units/lineage/digests.
- `bank-panel-audit-29a7dbdd5fa2.json`: independent audit **PASS**.

Typed source → saved canonical bidirectional EXCEPT ALL: **0 differing rows**.
Independent audit dùng DuckDB đọc nguyên JSON, explicit projection tám fields
và đối chiếu với saved Parquet từng quý: **42 quý đều 0 differing rows**.
Không dùng Python normalize tạo independent expectation. Tổng peer denominators
= canonical records = unique CERT×REPDTE = 214.809.

| Quality check | Actual | Interpretation / handling |
|---|---:|---|
| Duplicate bank-quarter | 0 | Grain valid cho acquired panel |
| ASSET/DEP/ROA missing | 0 | Chưa thấy missing ở ba fields |
| EQ missing | 714 ≈ 0,3324% | Medium equity-summary risk; giữ NULL và known counts |
| Negative EQ | 217 ≈ 0,1010% | Giữ signed values, không gán failure label |
| Nonpositive ASSET | 0 | Ratio denominators dương trong acquired panel |
| Parent consolidation records | 722 ≈ 0,3361% | High risk nếu coi sums là industry totals |

722 parent/child records có thể overlap consolidated balance sheets. Marts
chỉ ghi `reported_*` sums theo một quý, chưa claim industry totals. Không cộng
stocks qua nhiều quý. Matched changes chưa điều chỉnh mergers/acquisitions;
CERT continuity không chứng minh stable economic entity. Số reports từ 6.193
ở 2016Q1 còn 4.313 ở 2026Q2 không được diễn giải thành số bank failures.
Chưa đủ bằng chứng giải thích từng missing/negative EQ record.

Historical observations là latest revised lúc retrieval, không historical
as-of availability. Không có borrower PD, loan book, bank failure forecast
hoặc regulatory capital adequacy qualification.

## Rerun

PowerShell tại `D:\data\Codex\credit-atlas`, TEMP/TMP trên D: theo setup:

```powershell
.\.venv\Scripts\python.exe scripts/acquire_bank_history.py
.\.venv\Scripts\python.exe scripts/prepare_bank_panel.py --acquisition fdic-history-3e5ccce29513
.\.venv\Scripts\python.exe scripts/audit_bank_panel.py --panel bank-panel-13a7ad74220f
.\scripts\test.ps1
```

Reruns tạo new IDs, không overwrite raw/receipts. Verifier từ chối changed
source/output bytes, incomplete coverage, changed per-source receipts hoặc
current panel implementation. `bank-panel-68bbef72b5d4` là historical build
trước khi tăng verification checks; giữ audit, không current verified case.

Checkpoint: **560 tests pass** (375 engine + 185 application), 49,92 giây;
15 checks mới về FDIC coverage/units/nulls/duplicates/invalid values/definition
drift/actual pipeline/modified artifacts/HTTP boundaries. UI không thay đổi
ở checkpoint này nên không claim P4 browser acceptance.

## Các bước P4 tiếp theo

1. P4 snapshot/private exports, quarter/custom-peer/timeline đã có trong
   BANK_APP_WORKFLOW.md; shared source registry cần tích hợp additional tracks.
2. Bank-specific findings/review và consolidated-industry population semantics.
3. Institution history/consolidation review để định nghĩa industry population;
   FDIC failures vẫn separate event data, không borrower defaults.
4. Country observatory; typed exposure imports có currency/date/score semantics.
5. EL/ECL/stress cần đúng PD/EAD/LGD/cash-flow/policy contract hoặc explicit
   assumptions-only scenarios; FDIC ratios không thay loan book.

Full five-workspace plan vẫn còn hiệu lực. Historical foundation này chưa
hoàn thành full P4/country/portfolio-loss workflows hoặc toàn bộ CreditAtlas.
