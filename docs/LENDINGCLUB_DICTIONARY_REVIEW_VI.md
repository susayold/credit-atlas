# LendingClub — dictionary và review đặc trưng

Ngày 12/10/2026. Đối chiếu dictionary của issuer với 90 cột trong bản dữ liệu Mendeley. Checkpoint này chưa đóng application underwriting hoặc OOT validation.

## 1. Nguồn và acquisition

URL https://resources.lendingclub.com/LCDataDictionary.xlsx trả HTTP 200 và chuyển sang resources.happen.com. Quan hệ đổi tên được xác nhận trên [website công ty](https://www.happen.com/company/media-center) và [hồ sơ SEC](https://www.sec.gov/Archives/edgar/data/1409970/000140997026000163/hapn-20260630.htm): ngày 22/06/2026, LendingClub đổi tên công ty và ngân hàng sang Happen.

Hai trang trên được đọc bằng công cụ nghiên cứu web. HTTP trực tiếp tới media page trả 403 và một URL IR PDF trả 404; không ghi nhận đã acquire bytes của các tài liệu đó. Workbook được tải qua URL resource công khai, không dùng login hoặc cookies.

Workbook nguyên gốc có 23.582 bytes. Source folder: `data/private/retail/lendingclub-dictionary-source-65e0222b7c42`. Receipt SHA-256: `2c38861ef1b62a92dc79c1d37195ccf6f1e5885ef8f0f17c15d3c830061460ca`. ZIP/container integrity được kiểm tra; source không bị chỉnh sửa. Folder acquisition chưa hoàn tất của lượt trước được giữ lại.

Workbook gồm LoanStats, browseNotes và RejectStats. Metadata ghi created 2013-01-15, modified 2017-09-28. Đây là metadata của file, không chứng minh ngày xuất bản hoặc historical availability. Nó cũng không chứng minh dictionary bao phủ mọi thay đổi đến năm 2020. License CC BY của dataset Mendeley không tự áp dụng cho dictionary của issuer; public release vẫn chưa được phê duyệt.

## 2. Độ phủ mapping

Có 280 định nghĩa trong ba sheets. Đối chiếu 90 cột prepared data:

| Mapping | Số cột | Diễn giải |
|---|---:|---|
| Trùng tên trực tiếp | 86 | Có định nghĩa tương ứng; chưa chứng minh prepared values hoặc thời điểm có sẵn |
| Alias đề xuất | 2 | SubGrade → sub_grade; EmploymentLength → emp_length |
| Chưa có định nghĩa | 2 | verification_status_joint; LoanStatus |

Mỗi mapping giữ tên sheet, số row và địa chỉ ô A/B. Alias không chứng minh phép đổi tên, encoding hoặc transformation của contributor. `application_time_qualified` và `contributor_transform_qualified` vẫn false ở từng dòng.

## 3. Những định nghĩa ảnh hưởng đến nghiên cứu

- **DTI:** tính từ nghĩa vụ trả nợ tháng, loại mortgage và khoản vay LC đang xin, chia cho thu nhập tháng tự khai. Không thể dùng trực tiếp như DTI gồm mọi nghĩa vụ. Scale và ý nghĩa sentinel −1/999 trong prepared file chưa được xác minh.
- **annual_inc:** thu nhập năm tự khai khi registration, chưa phải thu nhập ròng/disposable income được kiểm chứng.
- **loan_amnt:** số tiền ghi trong application có thể đã bị bộ phận tín dụng giảm; giá trị phản ánh khoản sau giảm. Chưa chứng minh số tiền xin vay ban đầu trước quyết định.
- **issue_d:** tháng khoản vay được funded. Ngày 1 trong prepared representation không chứng minh ngày booking thật hoặc thời điểm quyết định cấp tín dụng.
- **int_rate, installment, grade, SubGrade, term:** terms hoặc đầu ra quyết định cần review theo stage; không mặc định có sẵn trước approval.
- **EmploymentLength:** prepared values 0–11 và fractional values cần công thức chuyển đổi của contributor. Định nghĩa gốc của emp_length không tự giải thích encoding này.
- **LoanStatus, loan_status:** đều là outcome. Đối chiếu dữ liệu cho thấy 0 đi cùng Charged Off và 1 đi cùng Fully Paid. Không dùng làm predictors hoặc nhầm 1 là bad.

Danh sách loại khỏi application modelling trong lúc chờ review bổ sung loan_amnt, term, EmploymentLength và cột chưa có định nghĩa, cùng các outcomes/identifiers/decision outputs. Đây chưa phải trained feature set. Các bureau-like fields còn lại vẫn cần bằng chứng as-of. Không suy từ chữ “chargeoff” trong tên rằng mọi biến bureau history đều là outcome của khoản vay hiện tại.

## 4. Verification

Profile: `artifacts/private/lendingclub-dictionary-profile-9b8a25e34bf8/profile.json`.

SHA-256: `bf8415ed612602d0941b44ffffda81b912daa05832f7a4729ab594335a7072a3`.

Preparation dùng openpyxl read-only, giữ literal definitions và chặn formula definitions. Không edit workbook. Audit độc lập đọc OOXML trực tiếp, không dùng openpyxl hoặc production parser: `artifacts/private/lendingclub-dictionary-audit-3fe039b24405/receipt.json`, PASS 280 định nghĩa, 560 ô và mapping của 90 cột.

Backend/HTTP: `artifacts/private/lendingclub-dictionary-http-tests-20261012-fixed.xml`, 36 tests PASS. Test đầu giả định open_act_il không có định nghĩa; workbook cho thấy nó trùng tên trực tiếp. Test được sửa để kiểm tra verification_status_joint, đúng là cột chưa có định nghĩa. Failed XML được giữ lại; không sửa source hoặc loại bureau field chỉ vì giả định đó.

Browser: `artifacts/private/lendingclub-source-qa-330325d8c34f/receipt.json`, 4 nhóm PASS: định nghĩa và caveat, alias/undefined/outcome distinctions, API/export parity, filters/reload, mobile và outage recovery. Không browser errors; frozen holdout ledger không đổi.

## 5. API và app

LendingClub source API/private JSON trả thêm dictionary của field đang chọn, review 90 cột, coverage, metadata, caveats và exclusions đang chờ review. Server kiểm tra receipt, workbook và profile hashes trước khi trả kết quả.

Retail → LendingClub source có phần “Issuer dictionary & feature review”: định nghĩa, địa chỉ ô, mapping trực tiếp/alias/chưa có, vai trò đề xuất và link official XLSX. Caveat DTI, income và amount nằm cạnh field đang xem. Không fit hoặc rescore model đã chốt.

## 6. Phần còn thiếu

Cần contributor preprocessing recipe/version, application decision timestamps, rejected/all-booked populations, event dates/horizon, maturity/censoring protocol, feature availability và intended-use/OOT review. Dictionary không thay thế các đầu vào này. Trạng thái của 50 capability, P1.02/P1.05 và C1 chưa được nâng lên hoàn thành.
