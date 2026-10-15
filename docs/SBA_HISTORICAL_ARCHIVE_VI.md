# SBA historical archive — snapshot 31/03/2026

Đã tải sáu CSV qua HTTP từ host chính thức `data.sba.gov`, tổng 885.226.430 bytes. Ngày snapshot được kiểm tra trên toàn bộ nội dung, không suy từ filename hoặc HTTP Last-Modified. Các bytes được lưu riêng trong `data/private/business-archive/sba-march-candidate-cf08cefd5f53`; acquisition receipt giữ nguyên trạng thái trước profiling để bảo toàn lịch sử.

## Dữ liệu thực đã bổ sung

| Segment | Source records |
|---|---:|
| 504 FY1991–2009 |111.059|
| 504 FY2010–Present |116.345|
| 7A FY1991–1999 |337.033|
| 7A FY2000–2009 |690.333|
| 7A FY2010–2019 |545.751|
| 7A FY2020–Present |373.981|
| Tổng |2.174.502|

Ngày `AsOfDate` gốc là `3/31/2026` trên toàn bộ records. Program gốc ` 7A` có leading space; bản report giữ source counts gốc trong từng segment và trim chỉ để kiểm tra chương trình. Grain vẫn là source record, không phải số khoản vay hoặc doanh nghiệp duy nhất.

## Audit và report

- Profile DuckDB: `artifacts/private/sba-candidate-profile-080b005671c4/profile.json`.
- Audit độc lập Python CSV/Decimal: `artifacts/private/sba-historical-audit-e953b55508eb/receipt.json`, PASS toàn bộ sáu file. Đối soát headers, row widths, raw dates, status/program counts, known/blank counts và tổng GrossApproval/GrossChargeOffAmount chính xác.
- Report tổng hợp hiện tại: `artifacts/private/sba-historical-report-f94f2ec47265/report.json`; receipt cùng thư mục. Report builder kiểm tra lại toàn bộ SHA raw bytes, acquisition/profile/audit bindings và audit method trước khi xuất. Report `dca117e2566d` giữ lại làm checkpoint trước API/UI.
- Tests: `artifacts/private/sba-historical-archive-http-tests.xml`, 21 PASS. Bao gồm exact decimal vượt độ chính xác float, missing không thành zero, raw statuses, date/program/coverage gates, audit/profile/acquisition/method/raw tamper rejection, query scope, private export và origin guard.
- Actual browser: `artifacts/private/sba-archive-browser-9f81f814d663/receipt.json`, 5 nhóm PASS. Đối soát program/status rows và exact amounts với API; download parity; reload/tab; June case giữ nguyên; mobile; lỗi API/retry. Holdout access ledger không đổi. Desktop/mobile screenshots đã lưu và mobile đã được xem trực tiếp.
- Code: `src/credit_atlas/business_archive.py`; build bằng `.venv\Scripts\python.exe -X utf8 scripts\build_sba_historical_archive.py` từ project root.

## Phạm vi phân tích

Report tách 504 (227.404 records) và 7A (1.947.098 records), có native status counts, từng segment, amount coverage, exact sums và source URLs/digests. Không đưa borrower names/addresses hoặc raw rows vào report.

GrossApproval 7A là full approved loan amount; 504 là SBA/CDC component, không phải toàn bộ project financing. Không cộng hai scope để tính pooled severity. Approval amount không phải current EAD. Chargeoff tổng lịch sử không phải LGD đã hiệu chỉnh.

Schema March có lowercase headers và thêm `subprogram`: 43 fields cho 7A, 40 cho 504. June dictionary/adapter hiện có 42/39 fields; chưa đủ chứng cứ semantics của subprogram để tự chuyển vào schema June. Báo cáo archive giữ riêng và chưa sửa frozen business case.

## Còn phải làm

1. Đã tích hợp `/api/business-archive` và `/api/business-archive-report`, nhận đúng `view_id` đăng ký cho business case; extra filters bị reject. Trong app mở Business → Nguồn & giới hạn → SBA historical archive. Bảng archive không dùng bộ lọc June; API kiểm tra lại raw source hashes trước mỗi report.
2. Nghiệm thu P3.01/P3.05/P3.09 theo toàn bộ điều kiện của plan, bao gồm current June source và runtime/browser evidence.
3. Chưa qualify loan identity, cross-snapshot transitions, fixed-horizon PD hoặc historical publication-time availability. Có hai snapshot không tự chứng minh các điều kiện này.

Đây là evidence bổ sung dữ liệu và archive workflow end-to-end; chưa đủ để tăng số yêu cầu full_completion_proven của toàn bộ Business source/cohort/concentration scope.
