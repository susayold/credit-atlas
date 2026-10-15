# P5 — static pool theo vintage và collection age

Ngày cập nhật11/10/2026. Đây là bổ sung lịch sử collateral/cohort cho P5.02/P5.10. Không đóng loan-level modeling, forward cashflow hoặc valuation.

## Nguồn mới

Source `pool-history-source-757ce3631134` trong `private evidence omitted from public release`, tổng3file/606.781bytes:

- Bản chụp [issuer index](https://www.worldomni.com/asset_securities.html).
- [StaticPool-WOART.xlsx](https://www.worldomni.com/abs/StaticPool-WOART.xlsx), linked trực tiếp từ index;10sheets.
- [ManagedPool-Retail.xlsx](https://www.worldomni.com/abs/ManagedPool-Retail.xlsx), linked trực tiếp;1sheet Historical.

HTTP downloader giới hạn16MiB/file, kiểm tra links/response/archive/CRC và giữ nguyên nguồn. Receipt ghi URL, timestamp, bytes, SHA. Không dùng cookies, không sửa workbook hoặc recalculate source formulas.

## Projection đã có

Ba sheets hiện đại: Delinquencies, Cumulative Losses, ABS Speed.21deal cohorts từ WOART2021-A đến2026-B;3.360 metric–deal–age positions, gồm1.998populated và1.362blank positions. Collection-age grid lấy các tuổi có nhãn số trong source, không tự tạo calendar months. Chỉ lấy cột có deal header tại row3; mirror ranges không có header dùng cho chart không được đếm thêm thành observations.

Reader đọc trực tiếp XML của XLSX để giữ numeric text, scientific notation, formula/cache và source sheet/cell. Blank/source cell absent trong age grid giữ `SOURCE_BLANK` và null; real zero giữ VALUE. Không zero fill, forward fill hoặc extrapolate vintage mới.

| Metric | Cách đọc |
|---|---|
| 61+ day delinquency | Source balance share theo pool definition ở A56, không borrower-count PD |
| Cumulative net losses | Source-reported fraction; chưa independently qualified denominator/loss components, không LGD |
| ABS speed | Non-scheduled runoff gồm cả prepayments/defaults; không pure default hazard |

Không cộng các tỷ lệ trên hoặc lấy pool maturity khác nhau để suy risk ranking. Cumulative net losses có thể giảm bởi recoveries; adapter không ép monotonicity. Age12/24 chỉ có giá trị nếu source có đúng tuổi đó.

WOART2025-A static-pool loss có18observed ages, latest0,75%; age12=0,49%, age24missing. Đây là coverage của source static workbook, không tự đồng bộ với20monthly servicer periods của case hiện tại. Retrieval date không chứng minh historical release date.

Managed workbook và6legacy individual-deal sheets (2003–2009) đã tải/inventory nhưng chưa được normalize vào3curve grids. Managed source có dollar amounts in thousands và các cột half-year/full-year khác nhau; không tự dùng tất cả reported rates như một annual series đồng nhất.

## App và API

P5 ABS → **Static pool**:

- Bộ chọn metric và deal; filters giữ trong URL khi reload.
- Biểu đồ theo collection age, không nối qua source blanks/gaps hoặc kéo đến tuổi chưa quan sát.
-21cohort summaries: observed age count, latest age/rate và age12/24.
- Bảng raw source theo age: exact text, missing status, sheet/cell.
- Source URLs/hashes, definitions, limitations và private JSON.

Static pool là bộ dữ liệu riêng; collection-month selector của báo cáo ABS phía trên không lọc age-grid này. Không coi các cohorts khác là collateral thuộc WOART2025-A.

API `/api/pool-history?metric=loss&deal=WOART%202025-A` và `/api/pool-history-report` xuất selected scope. Supported metrics: `loss`, `delinquency`, `speed`; unsupported filters/deals bị từ chối. Source bytes hoặc acquisition receipt thay đổi cũng bị từ chối. API unavailable làm sạch kết quả/export hiện tại, không fallback sang cached values.

## Kiểm tra đã hoàn tất

- `pool-history-tests-20261011.xml`:26testsPASS gồm source/receipt mutations, blank/zero, unsupported filters, invalid fractions, duplicate cohorts và ABSview regression.
- `pool-history-audit-a38fbe7ce809`:reader openpyxl readonly độc lập, không import projection module; đối chiếu63cohort–metric groups,1.998populated cells và1.362blank positions. Numeric text so với independent float reader ở tolerance10⁻¹⁵fraction; không có source cache recalculation claim.
- `pool-history-qa-5930436fbc94`:4groupsPASS choUI/API/JSON parity, metric/deal switching, URLreload/mobile, outage/recovery và frozen holdout ledger unchanged.
- Intermediate browser runs phát hiện selector chưa attach và long hash làm mobile overflow; đã sửa trước receiptPASS. Không dùng failed/intermediate runs làm bằng chứng nghiệm thu.

P5.02/P5.10 vẫn Một phần: cần loan/asset IDs, collateral-history adapter đầy đủ, fresh source/availability protocol và forecast/legal qualification. Tỷ lệ50capabilities không tăng chỉ từ acquisition/projection này.
