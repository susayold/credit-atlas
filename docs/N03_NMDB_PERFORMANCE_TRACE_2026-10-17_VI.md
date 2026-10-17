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

Full-geography archive đã được profile trực tiếp từ ZIP có receipt tại private workspace: **261.856 aggregate cells**, 98 quý (2002Q1–2026Q2), 4 markets × 4 series và 6 geography levels. Coverage lần lượt: National 1.568 rows/1 geography; Rural/Non-Rural 3.136/2; Census Region 6.272/4; Census Division 14.112/9; State 79.968/51; Metro 156.800/100. Archive có 48.028 `VALUE1` blank/dot và 764 `SUPPRESSED=1`; hai thuộc tính có thể chồng lấn. Đây vẫn là estimates theo từng geography/market do FHFA công bố, không phải nhóm để cộng gộp.

## Đường đi qua code, app và Excel

- API national: `src/credit_atlas/nmdb_performance.py` → `/api/nmdb-performance`; đọc native FHFA percentage, kiểm release/hash/schema/geography/coverage/key/range và báo release metadata.
- API state: `src/credit_atlas/nmdb_state_performance.py` → `/api/nmdb-state-performance?state=...`; trả 1 bang × 1,568 rows, giữ missing và suppression riêng.
- UI: `apps/web/nsmo.html` + `apps/web/nsmo.js`; cùng một selector definition cho national/state, quarterly table thể hiện missing/suppressed. Trend chart giờ flush polyline mỗi khi gặp `null`; nó không nối qua suppressed hoặc pre-series gap.
- Excel: `scripts/build_nmdb_performance_workbook.mjs` tạo workbook quốc gia `apps/excel/templates/CreditAtlas-NMDB-Performance.xlsx`; định nghĩa và KPI mới ghi 30–89 DPD. Workbook D02 lớn có thêm cùng định nghĩa trong `apps/excel/build_d02_data_reference.mjs` và `scripts/add_nmdb_state_to_reference_workbook.py`.
- Full-geography API: `src/credit_atlas/nmdb_performance_geographies.py` → `ResearchService.fhfa_nmdb_performance_geographies` → `/api/fhfa-nmdb-performance-geographies`. Route xác minh receipt/hash/profile và đọc lại source ZIP; lọc theo level, geography, market, series, quarter; giới hạn tối đa 5.000 row/query; không tổng hợp, impute hay forecast.
- Full-geography UI/Excel: `apps/web/nsmo.html` + `apps/web/nsmo.js` thêm explorer trên trang `/nsmo`; bảng giới hạn hiển thị 500 dòng nhưng export Excel chứa toàn bộ selection tối đa 5.000 rows. Query-scoped XLSX có `Start Here`, `Selected data`, `Definitions`, `Quality & lineage`, ghi receipt/hash, period, filter, source definition và missing/suppression.
- Tests/browser QA: `tests/test_nmdb_performance.py`, `tests/test_nmdb_state_performance.py`, `tests/test_nmdb_performance_workbook.py`, `tests/test_nmdb_performance_geographies.py` và `scripts/browser_nmdb_context_qa.py` kiểm label, counts, filter contract, cell suppression, chart gap, Excel values/lineage, URL/API và mobile behavior.

## Trạng thái nghiệm thu và phần còn mở

Source/definition/data/code trace đã được ghi; labels quốc gia/bang/workbook, chart gaps và full-geography filter/export đã được nối. Ngày 17/10, **15 focused tests pass** cho report, receipt profile, fallback, source blanks/suppression, workbook, aggregate route và source register. Edge acceptance pass **9/9 checks**: 6 national/state checks trước đó cùng 100 metro geographies, trọn trend 98 quý của một bang và filtered Excel giữ Vermont suppressed blank, bốn sheet/lineage; không có JavaScript errors. Receipt chỉ lưu local-private tại `artifacts/private/nmdb-geography-browser-qa-20261017/receipt.json`. Harness pin đúng checkout `src`; native Excel desktop open/recalculate chưa được xác nhận. N03 vẫn chưa trace các KPI mortgage khác; NMDB route QA không đóng toàn bộ N05/N06. Không nâng ledger capability 26/50 vì thay đổi này hoàn thiện route/data presentation, không thêm capability acceptance mới.
