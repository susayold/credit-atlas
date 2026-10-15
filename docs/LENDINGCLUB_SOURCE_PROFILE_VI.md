# LendingClub 2016–2020 — nguồn bổ sung cho Retail

Dictionary checkpoint mới: [LENDINGCLUB_DICTIONARY_REVIEW_VI.md](LENDINGCLUB_DICTIONARY_REVIEW_VI.md). Issuer workbook đã acquire và tích hợp API/UI; 86 exact names, 2 proposed aliases, 2 undefined fields. Các ghi nhận “cần dictionary” bên dưới mô tả checkpoint acquisition trước đó; contributor transforms, units và feature timing vẫn chưa qualified.

Ngày acquire/audit: 12/10/2026. Phạm vi: P1.02 application-data research, P1.05 affordability inputs và C1 temporal-data investigation. Không đóng các gates này chỉ bằng một file mới.

## Nguồn và tải dữ liệu

Mendeley Data version1, contributor David Maloney/Towson University, DOI10.17632/mvvd3dnfyz.1, published22August2022. Dataset page: https://data.mendeley.com/datasets/mvvd3dnfyz/1. Mô tả là contributor merge từ quarterly expired-loan files của LendingClub. Metadata CC BY4.0 có attribution và caveat về third-party content. Đây không phải original issuer download hoặc full original-file fidelity certification.

API public file inventory được xác định từ code của trang web (allowAnonymous). Root folder phải là `root`; request folder rỗng trả error400 đã được giữ trong discovery artifact. Không cần login/cookies hoặc computer use. CSV396,562,202bytes được stream xuống D:, size và SHA-256 khớp publisher metadata: `de4b17ea90bbd524de55a4b270650bcb2e764f8466bd279b10d194d000b6648a`.

Source folder `data/private/retail/lendingclub-source-2a2766348144`; acquisition receipt SHA `36f28b6635bd35b10759fb98dd1bfb55faf54199107996e9959eb0dc4bc86603`. File gốc giữ nguyên. Không fit/rescore model Retail đang frozen.

## Coverage đã kiểm tra

- 1,055,054 records,90columns,94,954,860raw cell positions.
- Booking issue dates2016-01-01 đến2020-06-01;105populated month/status cells. Không tự điền zero cho month/status absent trước khi định nghĩa completeness.
- Fully Paid838,429;Charged Off216,625. Chỉ hai terminal statuses trong file.
- `LoanStatus` là duplicate encoded outcome:1→Fully Paid,0→Charged Off. Không dùng làm predictor hoặc nhầm1 là bad.
- Individual979,065;Joint App75,989.
- Source IDs có1,055,054distinct values,0duplicate; điều này chưa chứng minh borrower identity hoặc original issuer loan-key lineage.

## Các inputs và vấn đề dữ liệu

| Trường | Quan sát nguồn | Giới hạn |
|---|---|---|
| loan_amnt |1,000–40,000;sum15,376,768,450|Raw source amounts; unit/convention phải có dictionary trước economics|
| annual_inc |0missing,1,180zero;max110,000,000|Zero khác missing; chưa chứng minh income verification hoặc disposable income|
| annual_inc_joint |75,989present,979,065missing|Không dùng missing joint income thành0 cho Individual|
| dti |1,204missing,2negative,min−1,max999|Chưa gán nghĩa sentinels hoặc loại tự động khi chưa có dictionary|
| dti_joint |75,987present|Hai Joint App records thiếu giá trị; không ép đủ coverage|
| int_rate |Raw0.0531–0.3099|Contributor có thể đã đổi format; không mặc định percent/fraction từ tên cột|
| EmploymentLength |8,518missing;values0–11,includesfractional|Derived representation; cần mapping của tác giả|
| issue_d |Valid booking dates,monthly source grain|Không phải application decision timestamp|

Nguồn có income,bureau,requested/booked amount-related fields nhưng thiếu rejected population,application decision date và event date. `grade`, `SubGrade`, `int_rate`, `installment` là decision/contract outputs cần separate availability review; chưa đưa vào application-time model. `loan_status`, `LoanStatus`, `id` luôn nằm trong candidate exclusions. Các predictor còn lại cũng chưa được mặc định qualified trước review dictionary/time.

## Vì sao chưa đóng application/OOT gates

File chỉ có paid/charged-off loans, phù hợp mô tả expired-loan selection. Không có unresolved/active exposure hoặc reject denominator. Terminal outcome có thể quan sát qua thời gian khác nhau; không có charge-off event date/horizon đủ để gọi là PD12. Booking-month split chỉ tạo cohort partition, chưa tạo mature fixed-horizon labels hoặc chứng minh OOT qualification. Không train một classifier rồi dùng accuracy để thay các điều kiện này.

Các nguồn khác đã khảo sát: FICO HELOC original challenge URL hiện redirect; IBM AIX360 repository không kèm raw `heloc_dataset.csv` trong tree hiện kiểm tra, chỉ có một prepared example. South German Credit UCI573 có code corrections và CC BY4.0 nhưng data1973–1975,oversampled bad,transformed amounts,không loan-level decision chronology. Không dùng hai nguồn đó để tuyên bố đã có later dated cohorts hoặc full underwriting.

## Verification

Streaming stdlibCSV/Decimal profile: `artifacts/private/lendingclub-profile-28db23b7bd0a/profile.json`, SHA `0ab0d8179811cec4499a83fd727e1d5cf7597f37b9b703f64af10774d9ed9e36`. Không malformed-width rows; source date validation không có lỗi. Missing tokens được ghi explicit; không impute.

Independent Arrow CSV engine audit: `artifacts/private/lendingclub-audit-4c9405321ec9/receipt.json` PASS. Kiểm tra publisher hash,rows,90column missingness,11numeric profiles/88checks,105monthly status cells,2label cross cells,date range,application types và IDs. Frozen holdout ledger unchanged. Numerical parser agreement chưa là semantic/leakage/source-original fidelity validation.

## Công việc tiếp

1. API/UI source explorer để xem coverage/missingness/cohorts và source qualifications, tách khỏi frozen Taiwan behavioral case.
2. Acquire source/contributor dictionary và preprocessing provenance; classify field availability/units, bắt duplicate outcome leakage.
3. Chốt population/target phù hợp hoặc bổ sung event/reject/full-booked data; chỉ fit khi target/split gates đạt.
4. Affordability/intake workflow giữ income,DTI,contract assumptions riêng và không suy disposable income hoặc reject outcomes từ nguồn này.

50capability states và C1/P1.02/P1.05 chưa được nâng từ checkpoint acquisition/profile.

## API/UI checkpoint 12/10/2026

Retail → LendingClub source đã tích hợp nguồn riêng. API `/api/lendingclub-source` và private JSON `/api/lendingclub-source-report` nhận from/to booking month,source status vàfield. Server kiểm tra acquisition/source/profile hashes trước trả dữ liệu; filters sai bị từ chối. Không expose record-level rows hoặc fit/rescore frozen Taiwan model.

Giao diện có source/window/selected record counts,terminal Charged Off share,monthly status chart/table,selected-field statistics,90-column whole-source missingness,duplicate-target encoding,qualification gates vàpublisher/licence/hash evidence. Month/status filter áp dụngcohort counts; numeric/missingness stats luônwhole-source vàghi rõscope. Source-status filter không đổi mẫu số của window share. Absent month-status cell giữnull,không thànhcertified zero. Non-numeric field không cónumeric profile.

Backend/HTTP `artifacts/private/lendingclub-http-tests-20261012.xml`:30testsPASS. Browser `artifacts/private/lendingclub-source-qa-c7baf1748a66/receipt.json`:4groupsPASS — source/API/export parity,filters/URL reload,whole-source statistics,mobile/non-numeric unavailable vàoutage/recovery. No browser errors;frozen holdout ledger unchanged. Desktop/mobile summary screenshots đãvisual-review. Browser đầu phát hiện lexical `history` variable shadowing URL history;đãrename local chart container vàrerun,không bỏ qua lỗi.

API/UI đã hoàn thành phần explorer nêu ở bước1; còn dictionary/preprocessing/event/decision/reject/target/OOT gates ở bước2–4. Không gọi terminal sample share làPD hoặcapp approval rate.

Retail source-quality regression: `artifacts/private/retail-source-quality-qa-d271669f6f69/receipt.json`,6groupsPASS. UCI source/API/UI/JSON/Excel,mobile,reload,unavailable-source handling và88KPI/22controls giữ nguyên;frozen holdout ledger unchanged. Không refit hoặc rescore final-test predictors.
