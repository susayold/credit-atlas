# Retail — profile chất lượng nguồn trong KPI monitor

Ngày cập nhật: 11/10/2026. Đây là bổ sung B1 quality controls; không đóng Retail OOT hoặc toàn bộ P1.

## Dữ liệu và phép tính

Monitor P1 đọc profile đã lưu khi acquisition UCI350, được hash-pin trong verified suite view. Profile có 30.000 source clients, 23 predictor columns X1–X23; ID và target Y không vào mẫu số.

- Tử số: tổng số ô được acquisition CSV parser nhận diện là missing trên 23 predictor columns.
- Mẫu số: 30.000 × 23 = 690.000 ô.
- Kết quả ở nguồn hiện tại: 0/690.000 = 0%.
- Quy tắc parser: strip khoảng trắng rồi so với chuỗi rỗng, `?`, `.`, `NaN`, `nan`.

Đây là whole-source aggregate trước freeze, không phải missingness của 3.001 final-test clients. Không mở lại predictor rows, fit lại model hoặc dùng final holdout để điều chỉnh model. Zero parser-missing không chứng minh semantic completeness, valid categories, drift hoặc khả năng triển khai theo thời gian.

## App, API và export

Trong Monitor chọn P1 Retail, xem **Chất lượng dữ liệu & phạm vi kiểm tra**. Có bảng 23 biến với source field, feature name, population, missing cells và share; bảng lineage giữ URL/retrieval/source SHA/profile receipt SHA.

API `/api/retail-source-quality?view_id=...` và private JSON `/api/retail-source-quality-report?view_id=...` chỉ nhận verified suite scope. Profile receipt phải khớp hash trong suite inputs; profile lỗi shape/counts bị từ chối. API lỗi thì missingness giữ Unavailable, không fallback về 0.

Monitor JSON giữ toàn bộ source profile. Review/Excel export capture thêm nguồn `source_quality` cùng suite ID, từ chối nguồn quality thuộc suite khác. KPI workbook sử dụng quality scope cho quality rows; business rows giữ business scope. App vẫn có 88 business KPI và 22 quality controls.

## Kiểm tra

Backend: `retail-source-quality-tests-20261011.xml`, 27 tests PASS gồm source projection, nonzero denominator, mutated hash, invalid counts, scope/API privacy, review capture và regression workbook/reviews.

Browser regression cả 5 domain: `kpi-inspector-qa-0b9964df5e79`, 9 nhóm PASS. Source-quality browser QA kiểm tra API/UI/JSON, Excel zero actual/source scope, reload, mobile, outage-null và frozen holdout ledger. Receipt `retail-source-quality-qa-594921ea7ac8`:6 nhóm PASS; Excel110-row actual/comparison/formula/error regression PASS.

Native Microsoft Excel recalculation chưa được kiểm tra. P1.01 vẫn Đã có trong scope benchmark; P1.09/P1.10 vẫn Một phần. Không tăng tỷ lệ hoàn thành 50 capabilities từ bổ sung này.
