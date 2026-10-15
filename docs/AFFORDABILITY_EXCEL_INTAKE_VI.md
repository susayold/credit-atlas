# Affordability — nhập dữ liệu từ Excel

Checkpoint 12/10/2026. P1.05 có adapter XLSX, API và file picker trong tab Retail → Affordability. File nhập đưa giá trị vào form để analyst xem/sửa và tính lại DTI/residual. Nguồn chứng từ, mức đầy đủ nghĩa vụ và policy vẫn chưa được xác minh.

## Cấu trúc file

File `.xlsx` tối đa 2MB, đúng hai sheets dưới đây. Dòng đầu là headers; không dùng công thức trong ô input. Những workbook công ty có schema khác cần bước mapping riêng, chưa tự nhận mọi workbook bất kỳ.

Mẫu đã có tại `apps/excel/templates/CreditAtlas-Affordability-Input.xlsx` và nút **Tải mẫu affordability Excel** trong app. Customer/policy inputs để trống; coverage mặc định false. Có dropdown scope/members/group/period/coverage. DTI threshold cell hiển thị phần trăm nhưng underlying value là fraction (40% = 0,4). Không có số liệu hồ sơ giả trong mẫu.

Cột D của Control và H của Items là hướng dẫn, phải có header `Guidance`; không đi vào assessment. Cột C/G là khoảng trống. Các ô ngoài input/guidance có nội dung bị từ chối; ô chỉ có format và trống được bỏ qua. Không thêm financial inputs vào guidance.

### AffordabilityControl

Headers tại A1:B1: `key`, `value`. Mỗi key có đúng một dòng; không lặp và không thêm key ngoài contract.

| Key | Giá trị |
|---|---|
|case_ref|Mã hồ sơ giả danh, không chứa tên hoặc credentials|
|as_of|Ngày đánh giá ISO `YYYY-MM-DD`|
|currency|Một currency code ba chữ in hoa|
|scope|`individual` hoặc `household`|
|scope_ref|Mã cá nhân/hộ giả danh|
|members|Số nguyên 1–100; individual bằng 1|
|policy_ref|Mã policy khai báo; trống nếu không có policy|
|max_total_dti_fraction|Ngưỡng DTI dạng fraction; trống thì comparison unavailable|
|min_monthly_residual|Residual floor theo currency; trống thì comparison unavailable|
|coverage_gross_income|`true` hoặc `false`|
|coverage_net_income|`true` hoặc `false`|
|coverage_recurring_expenses|`true` hoặc `false`|
|coverage_debt_payments|`true` hoặc `false`|
|coverage_proposed_payments|`true` hoặc `false`|

Optional sensitivity chỉ được thêm khi đủ cả ba keys: `gross_income_reduction_fraction`, `net_income_reduction_fraction`, `extra_monthly_expense`. Reduction fractions trong 0–1; expense là amount không âm. Không có cả ba thì sensitivity không bật.

Ngày trong phiên bản contract này dùng **text ISO**, không nhận số serial Excel vì workbook date system/number formats chưa được adapter diễn giải. Boolean Excel được nhận và chuẩn hóa thành true/false. Amount nhận số Excel hữu hạn tối đa 15 significant digits hoặc text decimal theo giới hạn engine. Numeric exponent trong OOXML được chuẩn hóa về decimal; text exponent không được nhận.

### AffordabilityItems

Headers tại A1:F1: `group`, `ref`, `amount`, `period`, `evidence_ref`, `valid_through`.

| Cột | Ý nghĩa |
|---|---|
|group|gross_income / net_income / recurring_expenses / debt_payments / proposed_payments|
|ref|Mã dòng duy nhất trong nhóm; cost refs không lặp giữa expenses/debt/proposed|
|amount|Giá trị gốc không âm; ô trống là missing, không thành zero|
|period|monthly / annual / quarterly / weekly / biweekly / semimonthly|
|evidence_ref|Mã chứng từ khai báo hoặc trống; chưa xác minh nội dung|
|valid_through|Text ISO hoặc trống; hết hạn chặn kết quả phụ thuộc|

Tối đa 500 items/nhóm, tổng 2.500 items. Không có items và coverage true là **người nhập khai báo known zero**, không phải adapter chứng minh không có nghĩa vụ. Gross/net giữ riêng; expenses phải loại các khoản debt payments để tránh đếm hai lần.

## App, API và evidence

Trong tab Affordability, chọn file ở “Nhập affordability Excel”. App hiển thị số dòng, SHA256 và bảng original source cells; giá trị được đưa vào các ô form và assessment tính lại. Sửa form làm mất assessment/export cũ. Các ô nguồn hiển thị giá trị nguyên bản; assessment sau sửa dùng giá trị form hiện tại.

POST `/api/affordability-excel-import` nhận JSON `filename`, `content_base64`, cần same-origin, application/json và `X-CreditAtlas-Client: local`. Body tối đa 3MB cho base64 của file tối đa 2MB. Không nới giới hạn 64KB của assessment/report thông thường. Response private/no-store, gồm intake, assessment, file hash/bytes/item counts và cell lineage. Không lưu upload vào database hoặc URL.

GET `/api/affordability-excel-template` trả XLSX attachment, không nhận query filters, kiểm tra hash mẫu trước khi serve. Không mở đường dẫn workbook tùy ý. SHA256 mẫu: `5c88cf6a9685db9bef9defd7c6f0d6e31352e499ec8d8fb3d76cb8224a64b979`.

CLI lưu bản nguồn và intake/assessment có lineage vào thư mục private mới để review:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m credit_atlas.affordability_excel D:\duong-dan\ho-so.xlsx
```

Không chạy CLI với đường dẫn chưa có file thực. Adapter không đọc formulas/cached results làm actual; chặn macros, embedded files, external relationships, XML entities, trùng sheets/rows/cells/keys, zip vượt bounds và input vượt precision. Không follow links hoặc execute mã trong workbook.

## Kiểm chứng

- `affordability-excel-tests-20261012-final.xml`: **50 tests PASS**, gồm adapter, assessment và HTTP suite. Numerical parity: annual gross 60.000 → monthly 5.000; total debt 2.000 → DTI 0,4; residual 500, bằng declared boundaries. Đây là inputs QA synthetic.
- `affordability-excel-qa-38d197be777d/receipt.json`: **4 nhóm browser PASS**. Upload → form → calculation/export parity; sửa amount invalidates; payment thiếu giữ unavailable; mobile; formula upload bị từ chối và không giữ assessment cũ. Ledger không đổi, không pageerrors.
- Form regression `affordability-qa-560a56b59b5a/receipt.json`: **4 nhóm PASS** sau khi thêm Excel picker; manual input/sensitivity, missing payment, export guard và outage/retry giữ hoạt động.
- Lần test đầu có lỗi setup do pytest tự tạo parameter ID từ hơn 2MB bytes, gây giới hạn filesystem Windows; đã sửa explicit short IDs. Không nới parser để làm test pass; XML lần đầu giữ nguyên.

## Checkpoint template và native Excel

- `affordability-template-tests-20261012-final.xml`: **53 PASS**, gồm intake/engine/HTTP, blank template, hash-tamper guard và guidance column contract.
- `affordability-template-roundtrip-20261012/audit.json`: **2 nhóm PASS**. Saved OOXML có hai sheets, năm validation definitions, không formulas, customer/policy fields trống. Bản QA điền bằng Artifact Tool đọc lại khớp gross monthly 5.000, total debt 2.000, DTI 0,4 và residual 500.
- `affordability-excel-qa-5db4d5f8f7f8/receipt.json`: **5 nhóm browser PASS**, gồm tải mẫu khớp hash và upload bản QA được điền từ mẫu thật. Sửa amount, missing input, mobile/formula rejection và ledger unchanged giữ đúng.
- `native-excel-qa-affordability-c541484f16e5/receipt.json`: **38 cells / 2 workbooks PASS** trong Microsoft Excel native read-only; kiểm tra giá trị/blank/text/no-formula parity, sources unchanged/copies not saved. Không chứng nhận đã exercise mọi dropdown interaction hoặc verified source documents.

Lần kiểm tra template đầu phát hiện importer từ chối các ô gutter chỉ có format; đã sửa để bỏ qua ô ngoài input **chỉ khi trống**, vẫn chặn nội dung/công thức. Một test LendingClub HTTP gặp socket timeout 5 giây trong run cùng tải IO; lần chạy lại suite giữ nguyên timeout đạt 53 PASS. Browser cold load đầu vượt click timeout 30 giây; dùng explicit visible wait 60 giây trước click và run sau PASS. Native audit đầu thiếu Get-FileHash do subprocess module path; chọn Windows PowerShell và module path hệ thống, không thay file audit hay dữ liệu. Failed outputs vẫn giữ.

P1.05 vẫn chưa nghiệm thu đầy đủ. Còn source-document verification, household completeness/semantic-overlap review, ownership và financial records thực. Không có credit approval/rejection hoặc verified-income conclusion từ import này.
