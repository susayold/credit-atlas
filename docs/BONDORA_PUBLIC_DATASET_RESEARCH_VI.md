# Nghiên cứu bộ Loan Dataset công khai của Bondora / Go & Grow

Ngày tải và profile: 15/10/2026. Nguồn được tải từ liên kết “Download Loan Dataset” do trang thống kê chính thức của Go & Grow công bố. Bản gốc được giữ riêng trong `data/private/retail/bondora-source/`; không đưa ID khoản vay hoặc từng dòng lên giao diện hay tài liệu công khai.

## Nguồn và dấu vết tải

- Trang giới thiệu và liên kết tải: [Go & Grow Public Statistics](https://goandgrow.eu/en/public-statistics/).
- File XLSX công khai: [Loan Dataset](https://sabanners001.blob.core.windows.net/statistics/public/loan_dataset_investor.xlsx).
- Trang hiện ghi rõ đây là dữ liệu về khách hàng tín dụng và các khoản vay; pháp nhân Go&Grow OÜ cũng ghi rõ mình không phải đơn vị cho vay và không phát hành khoản vay. Vì vậy nên gọi đây là dữ liệu loan-level của nhóm Bondora, được phân phối qua trang Go & Grow; không diễn giải Go & Grow là lender.
- Máy chủ blob trả `Content-Length=162618206`, `Content-Type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Last-Modified=2026-08-10T06:05:47Z`, `ETag=0x8DEF6A56BF40FAD`. SHA-256 của bản tải: `a75db03e24747aa8462f6f429b6cbdd2f7010be03da020a4bbd3536c4e1a07bf`.
- Receipt profile và số liệu tổng hợp: `artifacts/private/bondora-public-dataset-profile/receipt.json` và `profile.json`. Script có thể chạy lại bằng bundled Python có `openpyxl`: `scripts/audit_bondora_public_dataset.py`.
- Trang public cung cấp file tải nhưng nghiên cứu này chưa xác nhận quyền tái phân phối, công bố lại dữ liệu từng dòng hoặc dùng thương mại. Giữ bản sao nội bộ; kiểm tra điều khoản áp dụng và xin phép trước khi phát hành dữ liệu hoặc dịch vụ dựa trên file.

## Cấu trúc và quy mô đã đo

Workbook có hai sheet: `Loan Dataset` (789.144 dòng dữ liệu, 31 cột) và `Dataset Dictionary` (31 định nghĩa). Có 789.144 `loan_id` duy nhất, không thấy ID trùng trong bản tải. Ngày phát hành khoản vay trải từ 28/02/2009 đến 30/06/2026; ngày hành động được ghi mới nhất trong các dòng là 20/07/2026.

Số khoản vay theo quốc gia trong file: Finland 427.133; Estonia 240.987; Netherlands 66.005; Spain 34.221; Latvia 11.557; Denmark 8.888; Slovakia 346; Lithuania 7. Đây là phân bố của file xuất, không phải market share hay population đại diện của các quốc gia.

Trạng thái hiện tại trong file gồm Repaid 357.125; Active 321.945; Defaulted 105.822; Returned 4.243; InPostFundingReview 9. Các số này là trạng thái ở snapshot; không nên cộng thành tỷ lệ default phát sinh, vì cohort, thời gian quan sát và định nghĩa event khác nhau.

## Các trường có giá trị cho nghiên cứu

File có ngày phát hành, quốc gia, số tiền đã giải ngân, lãi suất ban đầu, kỳ hạn, thu nhập tổng hợp, hạng rủi ro tại thời điểm phát hành, trạng thái, dư nợ gốc, tổng gốc/lãi đã trả, ngày phát sinh nợ, số ngày quá hạn, tháng trong default và cờ `has_default_within_12_months`.

Từ điển định nghĩa `has_default_within_12_months` là Boolean cho biết đã quan sát default trong 12 tháng kể từ ngày booking; NULL nếu chưa đo được do chưa đủ thời gian. Bản profile tìm thấy true 86.618, false 520.246 và NULL 182.280. Không được đổi NULL thành non-default. Theo năm phát hành, năm 2026 có 96.365 khoản vay và cả 96.365 nhãn NULL; năm 2025 có 182.056 khoản vay, trong đó 85.915 nhãn NULL. Năm 2024 có 147.255 khoản vay và không có nhãn NULL theo cột này. Những con số này là kiểm kê của file hiện tại, chưa phải xác nhận độc lập về cửa sổ theo dõi hoặc quy tắc gán nhãn.

Các cột tổng gốc/lãi đã trả, trạng thái, dư nợ hiện tại, ngày hành động gần nhất, quá hạn, tháng trong default, khoản trả tiếp theo, trả sớm, `projected_npv_return` và phần lớn trường phí là thông tin sau khi giải ngân hoặc cập nhật trong vòng đời khoản vay. Chúng phù hợp cho nghiên cứu servicing/collections, trạng thái danh mục và kiểm tra nhãn; không được dùng làm feature cho quyết định cấp tín dụng tại thời điểm nộp đơn.

## Kiểm tra từ điển và chất lượng

- Từ điển có một sai khác tên: mô tả `principal_dept`, trong khi sheet dữ liệu dùng `principal_debt`. Cần giữ nguyên tên gốc và ghi nhận ánh xạ có kiểm soát; không tự sửa file nguồn.
- `combined_income` thiếu 273.160 dòng (34,6%); `customer_risk_rating` thiếu 338.509 (42,9%); `projected_npv_return` thiếu 276.076 (35,0%); `has_default_within_12_months` thiếu 182.280 (23,1%).
- `loan_last_recorded_action_date_local` thiếu 427.767 dòng (54,2%); `next_payment_date_local` thiếu 459.155 (58,2%); `months_in_default` thiếu 681.608 (86,4%). Việc thiếu có thể phụ thuộc trạng thái khoản vay; không coi là missing ngẫu nhiên.
- Từ điển nói thu nhập được kết hợp từ bank statement và registry, nhưng không cung cấp ngày đo, thời điểm sẵn có cho quyết định hay quy trình phiên bản hóa. Vì vậy chưa chứng minh được `combined_income` là application-time feature.
- Trang chính thức từng công bố các thay đổi về export, trường phần trăm, đơn trùng hồ sơ và các nhãn hủy/trả sớm trong [bài cập nhật dataset năm 2015](https://goandgrow.eu/en/blog/improvements-to-the-datasets/). Đây là cảnh báo rằng định nghĩa/format có thể đổi theo thời gian; bài viết cũ không thay thế changelog của file 2026.

## Ánh xạ vào plan Credit Atlas

**P1.02 Application underwriting — bổ sung được performance booked, chưa đủ để nghiệm thu.** Cờ default 12 MOB và một số thuộc tính tại thời điểm phát hành có thể bổ sung nghiên cứu cohort đã giải ngân. Nhưng file không có ngày nộp đơn/ngày quyết định, số tiền yêu cầu, kết quả phê duyệt, hồ sơ bị từ chối, bureau hoặc lịch sử feature theo đúng timestamp. `issued_amount` không đồng nghĩa `requested_amount`; `combined_income` chưa có chứng cứ thời điểm; `customer_risk_rating` tại issue chưa đủ định nghĩa để dùng thay feature đầu vào. Do đó không fit application score từ nguồn này và không tính approval rate/reject inference.

**P1.08 Collections workflow — ứng viên dữ liệu nghiên cứu, cần đánh giá riêng.** Có trạng thái, quá hạn, ngày nợ, tháng trong default và tổng thanh toán; tuy nhiên đây là snapshot tổng hợp, không phải chuỗi đầy đủ từng lần liên hệ, promise-to-pay, hành động, chi phí và thời điểm xử lý. Chưa thể đo hiệu quả treatment hoặc cure attributable.

**P1.09/P1.10 — dùng làm nguồn ngoài cho đối chiếu có giới hạn.** Có country, một số outcome và risk rating, nhưng không có định nghĩa demographics, source provenance theo từng thời kỳ hay dataset vintage/changelog đầy đủ. Không gộp thẳng vào validation UCI/LendingClub vì khác lender, quốc gia, sản phẩm, population và định nghĩa label.

Không ánh xạ nguồn này sang mortgage P2, doanh nghiệp P3, danh mục sở hữu P4 hay ABS P5. Nó là unsecured consumer-loan snapshot của nguồn khác, không phải mortgage servicing, borrower-level owned portfolio, facility/covenant data hay asset-backed security collateral tape.

## Bước tiếp theo

1. Giữ workbook nguyên bản trong private research storage, cùng hash và dictionary.
2. Trước khi modeling, hỏi nguồn phát hành về snapshot as-of, định nghĩa default 12 MOB, ngày bắt đầu/kết thúc quan sát, quy tắc censoring, thay đổi schema theo vintage, và việc có thể dùng nghiên cứu/tái phân phối hay không.
3. Nếu chỉ dùng cho nghiên cứu mô tả, phân tách theo vintage và country, loại toàn bộ biến hậu booking khỏi feature set; ghi riêng cohort maturity và NULL-label.
4. Tiếp tục tìm nguồn application-level có decision timestamp, requested terms, accepted/rejected applications, bureau/feature snapshots và booked performance nối bằng ID hợp lệ. Đây mới là đầu vào quyết định để hoàn thành P1.02.

### Nguồn kế tiếp đã rà soát: Prosper

Tài liệu API chính thức của Prosper định nghĩa nhiều trường listing ở lúc được tạo, gồm `AmountRequested`, `CreationDate`, `DebtToIncomeRatio`, `StatedMonthlyIncome`, dải credit score và các trường lịch sử tín dụng. Tài liệu cũng phân biệt listing với khoản vay được tạo khi listing được cấp đủ vốn. Đây là schema tiềm năng để nghiên cứu feature tại lúc listing và kết quả của những listing thành khoản vay.

Tuy vậy, Prosper hiện hướng người dùng có tài khoản hợp lệ sang API để tải dữ liệu loan-level; file Loan Level Monthly cần yêu cầu sau khi ký Data License Agreement. Listing bị withdraw/expired/cancelled không đồng nghĩa với toàn bộ đơn bị lender từ chối. Chưa có dữ liệu listing-to-loan liên kết được cấp quyền trong workspace, nên chưa thể dùng nguồn này cho modeling hoặc reject-rate.

- [Prosper API object definitions](https://www.prosper.com/Downloads/Services/Documentation/ProsperAPI_Objects_Details.html)
- [Prosper data export field definitions](https://www.prosper.com/Downloads/Services/Documentation/ProsperDataExport_Details.html)
- [Prosper instructions for downloading loan data](https://help.prosper.com/hc/en-us/articles/210013083-Where-can-I-download-data-about-loans-through-Prosper)

Kết luận nguồn: Prosper có thể lấp thêm phần application/listing-time fields và booked performance nếu có quyền truy cập phù hợp; hiện tại đường dữ liệu lịch sử theo tháng nằm sau thỏa thuận dữ liệu. Không lấy bản sao không rõ license làm nguồn thay thế.

**Kết luận nghiệm thu:** nguồn đã được tải và profile đầy đủ về cấu trúc, số dòng, định nghĩa, missingness và maturity của cờ 12 MOB. Nó cải thiện evidence cho nghiên cứu consumer credit, nhưng không thay đổi trạng thái P1.02: yêu cầu application-time và reject population vẫn chưa được đáp ứng.
