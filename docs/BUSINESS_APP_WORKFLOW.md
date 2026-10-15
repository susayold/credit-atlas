# P3 Business Credit Source Lab — SBA app và scoped report

Ngày triển khai: 09/10/2026. Mở local:
`http://127.0.0.1:8770/?view=business&view_id=suite-view-74e07524f6d0`.

## 1. Dữ liệu đã liên kết

Current aggregate snapshot `suite-view-74e07524f6d0` liên kết tới verified SBA
case `business-sba-21c568f10f7d`, batch nguồn `suite-619b1ee9aa8c`, cùng retail
benchmark và source warehouse hiện có. Build kiểm tra lại business method,
receipt/source lineage, output hashes và denominators trước khi lưu view.
Business facts/row identifiers không gửi tới browser.

P3 có **2.190.504 source records**, sáu typed files và bốn dimensions:
program/status, approval fiscal year, project state và NAICS two-digit.
Semantics, dictionary, exact Decimal precision và quality evidence ở
[SBA_BUSINESS_DATA_CONTRACT.md](SBA_BUSINESS_DATA_CONTRACT.md).

## 2. Các thao tác đã dùng được

1. Mở **P3 · Business credit** từ navigation; chọn verified suite snapshot.
2. Chọn **SBA program**: cả hai, 7(a) hoặc 504.
3. Chọn **SBA dimension** và **SBA bucket** để xem đúng nhóm records.
4. Đọc snapshot status shares với denominator là tổng source records cùng
   program/bucket. Không gắn chúng nhãn PD, default forecast hoặc LGD.
5. Xem reported approval, known approval-record counts và reported charge-off.
   7(a) total-loan amount và 504 SBA/CDC component tiếp tục tách theo program.
6. Xem **Quality findings · toàn nguồn**: số dòng giữ lại, excess source
   duplicates, dates after snapshot, disbursement before approval, charge-off
   thiếu date và charge-off > approval. Bộ lọc aggregate không lọc bảng này.
7. Xem dictionary cho cả hai chương trình và limitations/model/data gaps.
8. Xuất private JSON report theo bộ lọc đang chọn. Report giữ Decimal strings;
   display trên app format USD làm tròn cho dễ đọc.

Program/dimension/bucket được giữ trong URL và khôi phục khi reload. Chọn
program hoặc dimension mới reset bucket thành `all` để không mang bucket
khác grain sang scope mới. Invalid/unknown filters bị từ chối hoặc hiện
unavailable thay vì tạo số liệu giả. Controls mortgage được ẩn/disabled; header
P3 và unit USD/as-of riêng. Chưa có P3 finding workflow; không ghi nhận xét
business dưới mortgage case.

## 3. Scoped report contract

Endpoint:
`/api/business-report?view_id=…&program=504&dimension=approval_fiscal_year&bucket=2020`.

Report giữ view/case ID, business receipt digest, filters, selected record
count, selected aggregate rows, program amount scopes, contract và limitations.
Quality được giữ toàn bộ sáu segments, với
`quality_scope=whole_source_all_six_segments_not_filtered_by_aggregate_controls`.
Không có borrower name/address, source-record keys, loan-level scores, model
parameters hoặc private filesystem paths. `public_release_approved=false`,
`fixed_horizon_default_target_qualified=false`, `model_training_performed=false`.

Route reuse loopback Host/Origin/Fetch-Site checks và no-store headers.
Query chỉ chấp nhận view_id/program/dimension/bucket; row-level filters hoặc
unknown dimensions/buckets bị từ chối. Empty supported scope trả empty rows,
không tạo zero money observations. Snapshot input/method thay đổi làm evidence
unavailable. Historical snapshots không tự chuyển thành latest verified result.

## 4. Actual verification

Full software suite: **545 passed** (375 engine + 170 application).
Tests mới cover scope/precision preservation, whole-source quality, copy
isolation, empty cohorts, invalid/row-level filters, acquisition mismatch và
HTTP scoped attachment/local boundary.

Browser receipt: `suite-browser-qa-f5d061d221cd/receipt.json`, **16 checks PASS**.
Coverage bao gồm source catalog/retail regressions và P3 actual records,
504/FY2020 filtering, scoped export reconciliation, reload/filter restoration,
390px mobile layout và không có JavaScript/console errors. Desktop/mobile
screenshots cùng private scoped export được giữ dưới QA folder này.

Actual 504/FY2020 selection có **7.119 records trong 5 aggregate status cells**.
Browser export rows và counts khớp chính xác verified snapshot rows; quality
vẫn whole-source. Live API cổng 8770 đã kiểm tra cùng scope và counts này.
Không có model fit hoặc mở lại retail holdout predictors trong projection build.

## 5. Build/run và phạm vi còn lại

Từ `local machine path omitted`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_suite_view.py --warehouse source-warehouse-281662304758 --freeze retail-freeze-3dc86f5afe01 --holdout retail-holdout-061c440ea867 --business business-sba-21c568f10f7d
.\scripts\run.ps1
```

Build tạo view ID mới. `--business` là case ID đã kiểm tra, không phải đường
dẫn tùy ý. Nếu snapshot không chứa business evidence, P3 hiện unavailable và
không bật export. Các view method cũ được giữ làm historical artifacts;
catalog không gọi chúng là current verified khi source/method hashes đổi.

P3 SBA descriptive app/report đã có. Polish ratio/horizon adapter và benchmark,
SEC issuer/filing/units/memo, covenant/debt/financial statement workflow,
model target/availability và findings/review vẫn chưa hoàn tất. P4/P5 cùng
additional source tracks tiếp tục theo [PLAN_FIVE_WORKSPACES.md](PLAN_FIVE_WORKSPACES.md).
