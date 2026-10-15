# P5: nguồn ABS trực tiếp từ nhà phát hành

ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. See ABS_EE_MIRROR_COVERAGE_VI.md.


Checkpoint Managed Pool11/10/2026: tab/API/JSON có7kỳ,30chỉ tiêu/kỳ,210giá trị nguồn,105đối soát và14raw ratios; units nghìnUSD/signedrecoveries/source duration giữ riêng. Backend21PASS, independent source auditPASS, browser4groupsPASS. P5.02/P5.10 vẫn Một phần; xem MANAGED_POOL_ANALYTICS_VI.md.


Checkpoint staticpool11/10/2026: new issuer index +StaticPool-WOART/ManagedPool-Retail workbooks,3files606781bytes. P5 Static pool tab/API/JSON has21cohorts2021–2026 ×3metrics,1998populated and1362blank positions, source cells andage12/24 support. Backend26PASS, independent63group source auditPASS, browser4groupsPASS pool-history-qa-5930436fbc94. No loan-level target/LGD/forecast claim; Managed/6legacy sheets pending normalization. P5.02/P5.10partial unchanged. See STATIC_POOL_HISTORY_VI.md.


Checkpoint SOFR11/10/2026: acquired443New York Fed SOFRAI observations andSIFMA2025/2026US calendar,5files925844bytes. P5 ABS SOFR nguồn tab/API/privateJSON compares20periods;20/20at declared source binary precision,20/20interest cents. Raw exact19/20SOFR,15/20coupon preserved; historical15:00vintage/conforming changes/unscheduled notices remain unverified. Backend40PASS, independent20-period auditPASS, browser6groupsPASS. P5.05conditional/P5.10partial unchanged. See ABS_SOFR_BENCHMARK_VI.md.


## Bộ đã tải và kiểm tra

World Omni Auto Receivables Trust 2025-A, CIK 0002046523, auto retail
installment receivables. Trang chính thức liên kết prospectus và hai workbook:
https://www.worldomni.com/asset_securities.html

Source `abs-source-e67abf50bb2c` nằm trong `private evidence omitted from public release`:
4 file, **2.156.553 bytes**. Bao gồm bản chụp index HTML, prospectus PDF,
`WOART_2025-A_2025.xls` và `WOART_2025-A_2026.xls`.
Mỗi file có URL, HTTP200, thời điểm tải, kích thước, SHA256 trong receipt.
Download tuần tự, giới hạn 16 MiB/file, không redirect, không cookies.

Inventory hiện tại `abs-inventory-57a286117455` trong `private evidence omitted from public release`:
**20 kỳ collection Jan2025–Aug2026 / 20.132 ô lưu trữ** gồm 8.993 ô có nội
dung, 11.079 styled blanks và 60 empty-text cells. Inventory ban đầu
`abs-inventory-4be0c8a1fa03` gọi tất cả 20.132 ô là `nonempty_cells`; tên
counter đó không chính xác. Giữ receipt lịch sử, sửa inspector và tạo receipt
mới; không thay đổi workbook nguồn.
`source-cells.json` giữ tên file/sheet, dòng/cột, kiểu, giá trị và number format.
Workbook gốc không bị thay đổi, không recalculate. Reader xlrd 2.0.2 ở
`.cache/xls-reader` trên D:; dùng bundled Python để đọc legacy XLS vì
artifact-tool importXlsx không cung cấp reader XLS trong workflow này.

Kiểm tra nguồn cho mỗi kỳ:

1. Deal name và Monthly Servicer Certificate chính xác.
2. Bố cục các dòng principal/default/repurchase/ending YSOA/pool phù hợp.
3. Receivables beginning − principal payments − defaulted receivables −
   repurchases = ending pool balance + ending yield supplement
   overcollateralization amount. Sai số USD cho phép 0,01 do cache binary float.
4. Accounts beginning − principal-paid accounts − defaulted accounts −
   repurchased accounts = ending accounts, phải khớp tuyệt đối.

**20/20 kỳ PASS**, không có collection-period trùng giữa hai workbook.
Đây là pool reconciliation; không chứng nhận waterfall hoặc toàn bộ workbook.

## Phân biệt dữ liệu

Collection period và distribution date là hai mốc khác nhau. Jan2025 là kỳ
đầu có collection bắt đầu 03/01/2025; không tự đổi thành full calendar month.
Pool balance đã trừ YSOA, khác gross receivables balance và note balance.
Monthly source values có nhiễu binary float (ví dụ 269.824 bytes là kích thước
file, còn currency trong XLS có thể là x.1499999). Giữ raw value; adapter
tiền tệ sau này cần rounding policy riêng kèm provenance.
Defaulted receivables không tự biến thành loan-level default labels/LGD.
Source native delinquency percentages và source denominator phải được giữ;
không suy ra denominator chỉ từ tiêu đề hoặc thay bằng pool balance.
Source caches không chứng minh formula recalculation. Formula lineage chưa
được extract. Current retrieval không chứng minh historical availability.

## Canonical và kiểm tra kế toán đã triển khai

Case hiện tại **`abs-case-fcbaa9573ac3`**:

- `source_cells.parquet`: 20.132 rows, exact schema; file/sheet/row/column,
  source cell type, raw value representation, number format. Các styled blank
  được giữ, không gọi chúng là populated data.
- `reported_metrics.parquet`: **2.980 rows** / 149 chỉ tiêu mỗi kỳ, có collection
  end, section, source note slot, metric, unit, value/status, source row/column,
  label/raw value/type. Section pool/flow/distribution/notes_total/note_slot/reserve.
- Monetary USD chuẩn hóa ROUND_HALF_UP đến cent chỉ khi cache lệch cent
  không quá 0,00001 USD; material sub-cent bị từ chối. Source raw string vẫn giữ.
  Counts/days là nonnegative integers, ratio giữ source fraction precision.
- **40 NULL** là coupon trống tại D/E source template slots; không thành zero.
  Không công nhận D/E là issued tranches chỉ vì có dòng trong report template.
- Collection/accrual/report/payment dates riêng, validate các date labels,
  class/section/priority labels; missing/nonadjacent collection months không
  tự tạo continuity. Duplicate metric bị từ chối.
- **1.155 checks / 0 failed**: pool money/accounts, delinquency detail, net
  losses, funds inflow/distributions, tranche balances/payments, reserve,
  adjacent period continuity. Interest/principal giữa flow và notes sections
  khớp nhau; source subtotal không cộng thêm vào detail.

`verify_case` đọc lại XLS và rederive, đối chiếu schema/values/digest của cả
hai Parquet, source receipt, methods, period/check reports và qualifications.
Receipt đổi hash để che sửa values/schema không được chấp nhận. Các case
thử trước khi adapter chốt được giữ lịch sử; chỉ dùng case hiện tại trên.

Independent audit **`abs-audit-0065fd9be21c` PASS**:
đọc lại Excel bằng reader riêng, so multiset hai chiều bằng SQL EXCEPT ALL
với raw canonical: **0 different rows**. **940 independent source arithmetic
checks / 0 failed**, fixed source cells và DuckDB Decimal sums thay vì đọc
saved adapter checks. 4.046 numeric, 40 date, 4.967 text cells (gồm 60 empty
text) và 11.079 styled blanks. SQL kiểm tra không chứng nhận prospectus
terms, formula recalculation hoặc projected/contractual waterfall.

23 targeted contract tests PASS: blank/zero, signed currency/binary noise,
material sub-cent, invalid units/counts/types, source fraction/date interval,
subtotal conservation, damaged balances/counts/funds/reserve, missing/duplicate
inputs, period gap, altered Parquet schema/values with updated digest và
false qualification claims. Full-suite regression được ghi ở status document.

## Kế hoạch triển khai tiếp từ bộ dữ liệu này

Selected prospectus terms + numerical checks đã có ở
[ABS_PROSPECTUS_TERMS_AND_NUMERICS.md](ABS_PROSPECTUS_TERMS_AND_NUMERICS.md):
`abs-terms-4367aa1a54a3`,7issuedtranches,626source-termchecksPASS,
baseinterest/daycount và fundedprincipal priority/pro-rata engine.
Full contractual waterfall/legalstate/benchmarkfixing chưa certified.

1. Canonical cells/periods, typed pool/note/distribution/reserve và selected
   issued-tranche terms đã có. D/E template không phải issued notes.
2. Selected prospectus interest/day count, SOFR spread, OC/reserve, priority
   principal và review-trigger conventions đã kiểm tra. Executed agreements,
   amendments, legal events, benchmark fixing/fallback và clean-up instructions
   còn cần evidence; không suy ra chúng từ source paid-zero.
3. Independent raw-cell/accounting, selected-terms/interest và waterfall
   conservation audits đã có. Source shortfalls không tự là realized losses.
4. [ABS period app](ABS_APP_WORKFLOW.md) đã có collection/payment selector,
   adjusted pool, reserve, tranche balances/payments, due/paid cash ledger,
   source comparisons, terms và private export. Delinquency/review-trigger
   explorer, loan-level collateral và findings/review còn tiếp tục.
5. [Reported cash-flow replay](ABS_WATERFALL_WORKFLOW.md) đã có theo declared
   pre-acceleration assumptions; maturity/terminal engine scenario branches
   riêng. Scenario input app, automated carryover, acceleration, collateral
   forecasts/tranche losses, security valuation và positions còn tiếp tục.

Bộ này chưa thay ABS-EE loan-level panel. Không huấn luyện loan-level model
từ 20 dòng tháng hoặc coi hoàn thành toàn bộ P5.

## Các nguồn cần xác thực hoặc bị từ chối

Freddie Mac Clarity: người dùng chưa có phiên đăng nhập, các annual samples
ngoài 2012 vẫn conditional. Không yêu cầu lại cookies khi chưa có session.
SEC data.sec.gov submissions API HTTP200 cho CIK0002100629; URL Exhibit102
Auto Lease XML trực tiếp trên www.sec.gov/Archives trả HTTP403 trong lần
kiểm tra này. Không coi metadata API là collateral đã tải, không bypass403.
Ginnie bulk production homepage và JavaScript HTTP200; download service
trong mã public kiểm tra isAuthenticated rồi validateToken trước download.
Không coi việc tải index/schema là đã có production loan data.

## Lệnh chạy lại

Acquisition tạo source mới, không ghi đè nguồn hiện có:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\acquire_worldomni_abs.py
```

Inventory dùng bundled Python từ load_workspace_dependencies và xlrd ở D:,
truyền source ID; chỉ đọc file có SHA256 khớp receipt:

```powershell
& '<bundled-python>' -X utf8 .\scripts\inspect_worldomni_abs.py abs-source-e67abf50bb2c
```

Canonical/audit dùng project Python và optional `structured` dependency
xlrd 2.0.2 (đã cài vào D: project venv và pin trong lock):

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\prepare_abs_servicer.py abs-source-e67abf50bb2c
.\.venv\Scripts\python.exe -X utf8 .\scripts\audit_abs_servicer.py abs-case-fcbaa9573ac3
```

Tất cả artifacts private, public_release_approved=false. Acquisition và
inventory là tiến độ source track; full suite và full P2 R0–R4 vẫn mở.
