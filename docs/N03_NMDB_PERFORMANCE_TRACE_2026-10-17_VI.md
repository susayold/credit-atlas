# N03 — Trace KPI hiệu suất mortgage NMDB

**Rà soát:** 17/10/2026 · **FHFA release:** 30/09/2026 · **Dữ liệu đến:** 2026Q2.

## Kết luận định nghĩa

FHFA gắn series `P3089DL` với nhóm delinquency 30 và 60 ngày. Data Dictionary / Technical Notes phân loại delinquency theo bucket 30–59 ngày và 60–89 ngày; vì vậy nhãn đọc được trong app/Excel là **30–89 days delinquent (30–89 DPD)**. Không hiển thị “30–60 DPD”, vì cách ghi này có thể khiến người đọc hiểu đây là một dải liên tục chỉ tới 60 ngày.

Các tỷ lệ NMDB là trạng thái cuối quý trên mẫu số mortgage còn active. Project dùng tỷ lệ do FHFA công bố theo từng mortgage market và quý; không tự tính lại từ loan-level observations. `P90DL` là các nhóm 90/120/150/180+ DPD; `PFORECL` là foreclosure/bankruptcy/deed-in-lieu; `PFORB` là forbearance được báo cáo. Ba trạng thái `P3089DL`, `P90DL` và `PFORECL` là các nhóm performance riêng của FHFA. Không cộng bốn market với `All Mortgages`, không quy đổi các tỷ lệ này thành default probability, 12-month incidence hoặc loan-level target.

Nguồn: [FHFA NMDB Data Dictionary and Technical Notes](https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes) và [NMDB data page](https://www.fhfa.gov/data/nmdb). Hai quý gần nhất là provisional/revisable; NMDB là aggregate từ sample 5%; FHFA áp suppression cho cell nhỏ hơn 3 loan records; `PFORB` bắt đầu ở 2019Q4; các kỹ thuật stale-account khác nhau theo kỳ và FHFA cảnh báo undercount serious delinquency 2006–2012 do credit-history purge. Giữ mọi giới hạn này trong diễn giải.

## Kiểm tra actual data

Hai file public đã được receipt/hash bound:

| Geography extract | Grain | Rows | Blank/suppression evidence |
|---|---|---:|---|
| National | 4 market × 4 series × 98 quarter | 1,568 | 392 rows/series. `PFORB` có 284 ô blank trước 2019Q4; các blank là unavailable, không phải zero. |
| States + DC | 51 geography × 4 market × 4 series × 98 quarter | 79,968 | 68 rows mang `suppressed=1`, 17 mỗi series. `PFORB` có 14,484 ô blank trước 2019Q4. |

Đối chiếu trực tiếp state CSV: 68 suppressed rows đều tại Vermont × Government / Non-Conventional, trong 17 quý từ 2004Q1 đến 2008Q3; value luôn blank. Trong 14,484 blank `PFORB` trước 2019Q4, có 17 row đồng thời mang `suppressed=1` và 14,467 row `suppressed=0`. Đây là hai thuộc tính có thể chồng lên nhau, không phải hai nhóm blank cộng được. Code và workbook giữ nguyên value rỗng cùng cờ suppression. Không suy nguyên nhân khác ngoài những gì FHFA công bố.

Receipt: `docs/data/nmdb-performance-national-quarterly-2026q2-receipt.json` và `docs/data/nmdb-performance-state-quarterly-2026q2-receipt.json`. Nguồn quốc gia và bang là extract riêng; không gộp row counts hoặc thay thế nhau.

## Đường đi qua code, app và Excel

- API national: `src/credit_atlas/nmdb_performance.py` → `/api/nmdb-performance`; đọc native FHFA percentage, kiểm release/hash/schema/geography/coverage/key/range và báo release metadata.
- API state: `src/credit_atlas/nmdb_state_performance.py` → `/api/nmdb-state-performance?state=...`; trả 1 bang × 1,568 rows, giữ missing và suppression riêng.
- UI: `apps/web/nsmo.html` + `apps/web/nsmo.js`; cùng một selector definition cho national/state, quarterly table thể hiện missing/suppressed. Trend chart giờ flush polyline mỗi khi gặp `null`; nó không nối qua suppressed hoặc pre-series gap.
- Excel: `scripts/build_nmdb_performance_workbook.mjs` tạo workbook quốc gia `apps/excel/templates/CreditAtlas-NMDB-Performance.xlsx`; định nghĩa và KPI mới ghi 30–89 DPD. Workbook D02 lớn có thêm cùng định nghĩa trong `apps/excel/build_d02_data_reference.mjs` và `scripts/add_nmdb_state_to_reference_workbook.py`.
- Tests/browser QA: `tests/test_nmdb_performance.py`, `tests/test_nmdb_state_performance.py`, `tests/test_nmdb_performance_workbook.py` và `scripts/browser_nmdb_context_qa.py` kiểm labels, counts, cell suppression, đường ngắt chart và download.

## Trạng thái nghiệm thu và phần còn mở

Source/definition/data/code trace đã được ghi; labels quốc gia/bang/workbook và chart gaps đã được sửa. Runtime tests và Edge acceptance cần pass sau thay đổi. Native Excel desktop open/recalculate chưa được xác nhận trong lượt này. N03 còn các KPI khác; N05/N06 vẫn chưa đóng acceptance tổng chỉ nhờ nhánh NMDB performance này. Không nâng ledger capability 26/50 vì sửa định nghĩa và data presentation.
