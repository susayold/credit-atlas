# HMDA — dated lender names and county reference work, 09/10/2026

Đã tải bằng HTTP/code danh sách lender Maryland cho activity years 2023,
2024, 2025. Receipt `hmda-reference-99d45a87b712` có **4 files / 286.874 bytes**:
ba JSON filer và một HTML API documentation. Các file có URL, HTTP 200,
retrieval timestamp, size và SHA-256; bind với source receipt
`hmda-source-979e0862af13`. `labels.json` giữ tên theo đúng năm + LEI,
độ phủ trên từng public CSV và explicit contract. Source và các snapshot
ứng dụng trước đó được giữ nguyên.

## Độ phủ thật trên cohort hiện tại

| Activity year | Source records | Lender keys trong CSV | Reference keys | Records có tên duy nhất | Records thiếu tên |
|---|---:|---:|---:|---:|---:|
| 2023 | 113.089 | 704 | 861 | 113.089 | 0 |
| 2024 | 116.150 | 667 | 829 | 115.989 | 161 |
| 2025 | 117.817 | 663 | 804 | 117.378 | 439 |

Tổng **346.456/347.056** rows có tên, **600** rows chưa match. Đây là
records, không phải số borrower/loan duy nhất. Có 4 lender keys thiếu năm
2024 và 16 năm 2025; mọi key và row count nằm trong `labels.json`.
Không có ambiguous names trong actual downloaded references. Bộ đọc vẫn
giữ toàn bộ candidates nếu cùng năm + LEI có nhiều tên khác nhau.

API filer listing dùng scope MD/year rộng hơn cohort home purchase/site-built;
`count` trong JSON không thay thế count của application cohort. Release hiện
tại của filer listing và static LAR có thể khác nhau. Chưa chứng minh nguyên
nhân thiếu tên; không suy diễn merger, closure hoặc reporting error. Không
mượn tên từ năm khác, fuzzy match hoặc loại unmatched records.

## County và giới hạn acquisition

Đã xác nhận các official Gazetteer download links cho Maryland 2023–2025
qua trang Census. 2023/2024 dùng tab, 2025 dùng pipe và thêm GEOIDFQ.
Bộ đọc xử lý định dạng theo năm, giữ `24005` Baltimore County riêng với
`24510` Baltimore city, kiểm tra FIPS/state/ANSI/qualified key và duplicate
keys. Đây mới là parser được kiểm tra bằng fixtures, **chưa có actual county
payload tải thành công về workspace**.

HTTP trực tiếp đến official state files, national ZIP và trang Census đã
trả 403 trong session này. Probe ACS county-name API trả 302; chưa tải một
response JSON hợp lệ hoặc xác nhận redirect destination. Không claim county
acquisition completed. Failed package `hmda-reference-1bb89378d333` giữ riêng
failure receipt; không được coi là complete.

Actual receipt có scope `lender_only`, status
`VERIFIED_DATED_HMDA_LENDER_REFERENCES`, `county_names_acquired=false` và county
references rỗng. County counts ghi UNMATCHED, giữ nguyên FIPS/NA. Việc thiếu
reference hoàn toàn không thay đổi denominator, amount hoặc source records.

## Validation và rerun

Primary verifier đọc lại source CSV qua `verify_source`, kiểm tra reference
hashes/methods/source receipt, rồi tái tạo toàn bộ labels và coverage.
Independent audit `hmda-reference-audit-3f7c065534b9` **PASS 15 checks**:
DuckDB trực tiếp đọc raw filer JSON và CSV, kiểm tra toàn bộ name candidates,
year + LEI joins, status counts, unmatched keys, record totals và unique key
counts. Audit không gọi parser/projection để tính expected results, và không
chứng nhận county reference hoặc legal entity continuity.

Validation checkpoint: **73 related HMDA tests PASS / 16,45 giây**, gồm 21
reference/auditor tests và 52 source/canonical/view tests. Các tình huống có
wrong-year LEI, malformed keys, ambiguity, missing names, distinct city/county,
wrong delimiter, duplicate FIPS, payload corruption, forged labels, False→0,
source rebinding và independent-auditor false projection. Checkpoint full
suite trước đó vẫn là 870; chưa chạy lại full suite cho source-only addition.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/acquire_hmda_references.py --source hmda-source-979e0862af13 --lenders-only
.\.venv\Scripts\python.exe -X utf8 scripts/acquire_hmda_references.py --verify hmda-reference-99d45a87b712
.\.venv\Scripts\python.exe -X utf8 scripts/audit_hmda_references.py --reference hmda-reference-99d45a87b712
```

Không có historical availability, boundary equivalence, PD/default labels
hoặc identity continuity qualification. Download dùng exact URLs, bounded
size/time, HTTPS, không tự follow redirect. Tất cả artifacts giữ private.

## Source-bound API/UI checkpoint

Đã tích hợp reference vào app, giữ nguyên `hmda-view-89499c7d1d02` và các
frozen source/canonical/view methods trước đó. Overlay riêng
`HmdaReferenceViews` lần đầu tái xác minh raw source/reference, sau đó giữ
receipt/payload hashes và kiểm tra lại bytes của tất cả pinned files mỗi lần
đọc. Reference thuộc source khác bị từ chối. Cached payload trả bằng deep
copy; sửa response không làm đổi cache. Không có cross-year name fallback.

API mới:

- `/api/hmda-references?source_id=...`: catalog reference cho đúng source.
- `/api/hmda-reference?reference_id=...&source_id=...`: dated name candidates
  và whole-year coverage, private/no-store.
- `/api/hmda-labeled-aggregates?view_id=...&reference_id=...&year=...`: cùng
  các bộ lọc của aggregate API; thêm `display_label` vào lender/county buckets
  và `reference` metadata, không sửa counts/denominators/rates/amounts.
- `/api/hmda-labeled-report?...`: attachment JSON chính xác cùng kết quả.

App có reference selector, URL `hmda_reference_id`, lender options theo năm
hiện chọn; tên đi với LEI. MATCHED dùng một tên, AMBIGUOUS giữ all candidates,
UNMATCHED ghi “Chưa có tên”. Khi đổi activity year, options dùng reference của
năm đó; report/export chỉ đổi khi submit. Lender breakdown dùng năm đã submit.
Whole-year name coverage tách rõ khỏi filtered quality/denominator. County
names chưa có nên FIPS vẫn được giữ trên UI và export mang UNMATCHED labels.

**897 full-suite tests PASS** (375 engine + 522 application),321,14giây.
Sáu tests mới kiểm tra dated labels, ambiguity, county missingness, unchanged
base numbers, exact export, source/origin/filter guards, deep-copy cache và
timestamp-preserved tampering. Browser artifact
`hmda-browser-qa-933388f8532a` **PASS 12 checks**, gồm actual 2025 missing-name
option, reference/source binding, year-refresh label, source intersections,
exact labeled export, URL reload, empty subset, mobile390px0overflow và các
workspace navigation. Desktop/mobile screenshots đã được xem trực tiếp.

Live server8770 đã restart theo đúng process identity và labeled aggregate
API trả HTTP200: actual2025records117.817,decided denominator72.103,
reference`hmda-reference-99d45a87b712`,unmatched439,public_release_approved=false.

## Phần triển khai tiếp theo

1. Hoàn thiện county source acquisition và name coverage investigation; các
   HMDA reference API/UI và lender labels đã có ở checkpoint trên.
2. Tải county reference từ official accessible endpoint khi có, tạo receipt
   đầy đủ riêng; kiểm tra raw FIPS join và `NA`, không fill missing geography.
3. Mở rộng actual county API/UI/export acceptance khi có source; current lender
   display/export đã kiểm tra bằng actual artifacts ở checkpoint trên.
4. Tiếp tục D08 coverage/product/occupancy/findings và D01 R0–R4 cùng toàn bộ
   5-workspace/50-capability plan. Đây là checkpoint reference acquisition,
   không phải completion của P2 hoặc toàn bộ CreditAtlas.
