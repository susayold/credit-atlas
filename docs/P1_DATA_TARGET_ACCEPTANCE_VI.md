# P1.01 — dữ liệu và target của Retail benchmark

Đã bổ sung data contract trong **Retail → Model & evidence**: 30.000 source clients, 180.000 history observations, mapping sáu tháng, source categories, predictor exclusions, split support và JSON export. Nghiệm thu chỉ áp dụng UCI350 historical Taiwan behavioral benchmark; không nâng thành Vietnam PD hay application underwriting.

## Định nghĩa và source coverage

[UCI350](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) mô tả lịch sử April–September 2005 và target source-defined next-month payment default. Monetary fields dùng NT dollar/TWD. Sáu history rows cùng client không tạo sáu independent target labels.

| Reference month | Status | Bill statement | Previous payment |
|---|---|---|---|
|2005-09|PAY_0 / X6|BILL_AMT1 / X12|PAY_AMT1 / X18|
|2005-08|PAY_2 / X7|BILL_AMT2 / X13|PAY_AMT2 / X19|
|2005-07|PAY_3 / X8|BILL_AMT3 / X14|PAY_AMT3 / X20|
|2005-06|PAY_4 / X9|BILL_AMT4 / X15|PAY_AMT4 / X21|
|2005-05|PAY_5 / X10|BILL_AMT5 / X16|PAY_AMT5 / X22|
|2005-04|PAY_6 / X11|BILL_AMT6 / X17|PAY_AMT6 / X23|

Nguồn có 3.932 negative statement cells; giữ nguyên, không clipping. PAY -2/0, education0/5/6 và marriage0 không có nghĩa đầy đủ trong simplified dictionary, giữ separate categories. Không tự đổi thành missing, current hoặc DPD0. Parser-missing khác dictionary ambiguity.

19 raw model predictors gồm 13 numeric và 6 payment-status categorical fields. Source ID, target, SEX/EDUCATION/MARRIAGE/AGE excluded; demographic exclusion không tự chứng minh fairness. Split random/stratified/client-disjoint được ghi rõ, không phải temporal OOT.

| Partition | Positive | Negative | Clients |
|---|---:|---:|---:|
|Train|3981|14018|17999|
|Calibration|996|3505|4501|
|Validation|995|3504|4499|
|Final test — saved support|664|2337|3001|

## Bằng chứng và giới hạn audit

- `retail-data-contract-audit-b3bb54ab0deb/receipt.json`: current byte hashes của raw CSV, source/metadata/case outputs và method; 2 Parquet footers khớp counts; 23 mappings; 133 aggregate category counts; split support tính độc lập bằng cumulative floors từ target counts.
- Full-row source/client/history reconciliation là **receipt trước freeze đã hash-verify**, không phải fresh semantic scan trên final-test rows. Source/client/history bytes hiện tại khớp đúng byte hashes đã được reconcile. Endpoint và audit không đọc predictor rows.
- `retail-data-contract-tests.xml`: 22 tests PASS, gồm inconsistent aggregate, source hash, ID/target exclusions, unknown code meanings, scope và source-quality regression.
- `retail-data-contract-browser-da8a969e3028/receipt.json`: 6 month rows, 4 split rows, 23 field mappings, 133 categories và JSON export khớp; reload/tab navigation, mobile, cross-origin/scope rejection và outage/retry PASS; retail holdout ledger không đổi.
- `retail-source-quality-qa-228bfa9a3dc9/receipt.json`: monitor/API/JSON/Excel source-quality regression PASS; 690.000 raw predictor cells có parser-missing0; 88 business KPI và 22 controls được giữ; outage trả null và không giữ stale source reference. Đây là source-profile regression, không xác thực toàn bộ native Excel features.
- `source-run-browser-acceptance-3883e6d66a75/receipt.json`: mortgage Sources/run/evidence/readiness/exports regression PASS sau bổ sung route/UI Retail riêng.

API `/api/retail-data-contract[-report]?view_id=...` chỉ nhận suite-view scope đã verify. Không hỗ trợ client_id hoặc final-test partition query. Chỉ đọc pinned pre-freeze metadata/aggregate JSON, không materialize predictors hay fit/rescore.

Đã tải metadata và dataset-page hiện tại qua HTTP vào `data/private/retail-reference/uci350-reference-6d33854afcef`. Metadata `data` object không có khác biệt với bản đã pin. Hai tài liệu mới không thêm client rows hoặc temporal cohorts; creation/update/retrieval dates không thay observation months hoặc chứng minh historical availability.

## Phần còn thiếu

Temporal cohorts, population deployment, actual economic inputs và intended-use review chưa có. Source label không phải independently validated regulatory default. P1.02 underwriting, affordability verification, limit/pricing và collections data vẫn giữ gates riêng. Mục tiêu toàn dự án chưa đạt 100%.
