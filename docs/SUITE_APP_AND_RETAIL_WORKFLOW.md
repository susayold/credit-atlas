# App — catalog 5 workspace và Retail Behavioral Risk Lab

Ngày triển khai: 09/10/2026. App local/private tại `http://127.0.0.1:8770/`.
Các source/model artifacts tiếp tục nằm trên D:, không nhúng raw data vào JS.

## Các màn hình đã dùng được

1. **5 workspace · nguồn**: năm domain, trạng thái thực tế, khả năng dùng được
   và phần còn thiếu. Catalog có 20 files của batch đã tải, filter theo P1–P5,
   số dòng source-native, source links, rights và limitations. Metadata và
   dictionary là references, không cộng thành observations/khách hàng.
2. **P1 · Retail benchmark**: target, train-only feature dimension, frozen model,
   split/class counts, sáu development model/variant metric sets, final holdout,
   reliability bins và paired bootstrap intervals của validation.
3. Mortgage views giữ P2/D01 evidence và model-readiness gates riêng. Retail
   không mượn target, missing-vintage gate, unit USD hoặc filters của mortgage.

Retail và catalog có snapshot selector, URL state/reload và private aggregate
JSON export. Filter của mortgage bị ẩn/disabled khi xem suite/retail; findings
cho retail chưa được triển khai nên không ghi nhận xét dưới mortgage case.
Mở retail không cần completed mortgage run.

## Bằng chứng đã chạy

Current view `suite-view-74e07524f6d0` liên kết:

- Acquisition `suite-619b1ee9aa8c`: 20 files, 1.042.444.750 bytes.
- Warehouse `source-warehouse-281662304758`: 17 tables, 2.320.165 source rows.
- Case `retail-case-470bdb40682f`, assessment `retail-assessment-b8b96f471254`.
- Comparison `retail-comparison-b560ea676127`.
- Frozen model `retail-freeze-3dc86f5afe01`, boosting/raw.
- Holdout `retail-holdout-061c440ea867`: 3.001 clients / 664 events,
  ROC AUC 0,777878; Brier 0,136377.
- Business `business-sba-21c568f10f7d`: 2.190.504 SBA records, bốn marts,
  P3 descriptive UI và scoped report. Xem [BUSINESS_APP_WORKFLOW.md](BUSINESS_APP_WORKFLOW.md).

Projection build xác minh nguồn và warehouse, model lineage/freeze, holdout
artifact hashes, completed access ledger, saved score IDs/labels so với split
và aggregate metrics tính lại từ saved scores. Không đọc holdout predictors
hoặc score lại model khi tạo projection. Nguồn, model, encoder và raw IDs
không được trả cho browser; export chứa aggregate snapshot giống API.

`snapshot.json` là serving contract và `view-complete.json` giữ input/method
digests private. Khi cold load, tất cả input hashes được kiểm tra. Cached load
kiểm tra file size/mtime, small JSON hashes và serving snapshot hash; input
hoặc method thay đổi làm view unavailable thay vì hiển thị metrics cũ.
Không có cryptographic signing hoặc chống sửa file cho người có quyền OS.

## API và bảo vệ local

| Endpoint | Nội dung |
|---|---|
| `/api/suite-views` | Catalog verified/unavailable aggregate views |
| `/api/suite-view?view_id=…` | Verified aggregate snapshot |
| `/api/suite-report?view_id=…` | Cùng snapshot, private JSON attachment |
| `/api/business-report?view_id=…&program=…&dimension=…&bucket=…` | Scoped SBA aggregates; quality giữ whole-source |

Các route reuse loopback Host/Origin/Fetch-Site checks, `no-store`, CSP và
không có arbitrary file download. Invalid identifiers/path traversal bị
từ chối trước filesystem access. Không gọi export này là public-approved.
ICE OAS raw observations vẫn private; catalog chỉ nêu metadata và source scope.

## Chạy lại build và app

Từ `local machine path omitted`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_suite_view.py --warehouse source-warehouse-281662304758 --freeze retail-freeze-3dc86f5afe01 --holdout retail-holdout-061c440ea867 --business business-sba-21c568f10f7d
.\scripts\run.ps1
```

Build tạo view ID mới và kiểm tra evidence trước completion. Không tạo model
mới hoặc đánh giá lại final test. App URL có thể chọn view ID cụ thể:

- `http://127.0.0.1:8770/?view=suite&view_id=suite-view-74e07524f6d0`
- `http://127.0.0.1:8770/?view=retail&view_id=suite-view-74e07524f6d0`
- `http://127.0.0.1:8770/?view=business&view_id=suite-view-74e07524f6d0`

## Acceptance và phần chưa xong

Full software suite sau business UI/report: **545 passed** (375 engine,
170 application). Checks mới kiểm tra changed raw evidence, preserved-stat
snapshot tampering, modified completion receipt, identifier traversal, copy
isolation, local HTTP boundary và private aggregate export.

Browser suite acceptance kiểm tra nguồn thật, domain filter, holdout metrics,
disabled mortgage filters, independent navigation, URL reload, private export
không có individual IDs/scores hoặc model parameters, mobile page overflow
và retail availability khi mortgage run catalog rỗng. Screenshots/receipts
private dưới `private evidence omitted from public release`.

Latest actual suite browser receipt: `suite-browser-qa-f5d061d221cd/receipt.json`,
**16 checks PASS**, gồm business scope/reload/export/mobile và source/retail checks.
Mortgage regression receipt: `browser-qa-06f7e2d1aec0/receipt.json`, **24 checks
PASS** khi chạy riêng. Một lần chạy mortgage cùng lúc với suite QA trước đó
timeout ở cold transition computation; failure receipt
`browser-qa-adbd99454c4e/failed.json` được giữ, không thay bằng PASS.
Live endpoint cổng 8770 đã đối chiếu đúng 5 modules và 3.001 holdout clients.

App integration này chưa hoàn tất P1 hoặc toàn bộ 5 workspace. Retail còn
fairness/subgroup/intended-use review, economic-policy scenarios và monitoring.
P3 đã có SBA descriptive flow; Polish/SEC/model/workflow còn thiếu.
P4–P5 hiện có catalog nguồn, chưa có full bank/market analysis flows.
Additional acquisition và tất cả function/data/numerical/model gates trong
[PLAN_FIVE_WORKSPACES.md](PLAN_FIVE_WORKSPACES.md) vẫn thuộc phạm vi công việc.
