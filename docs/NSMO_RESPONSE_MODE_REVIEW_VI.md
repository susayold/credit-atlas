# D02 — kênh phản hồi và tính tương đương giữa các wave

Cập nhật: 16-10-2026. Đây là kiểm tra thiết kế survey cho NSMO v7.0; không tạo
nhãn tín dụng, PD hay ước lượng mode effect.

## Phần dữ liệu tìm được

FHFA Technical Report v7.0 Table 3 công bố số survey gửi, không giao được, giao
được và hoàn tất qua thư, online tiếng Anh, online tiếng Tây Ban Nha cho 48 wave.
Script `scripts/audit_nsmo_survey_returns.py` trích bảng từ PDF chính thức, gỡ
hai superscript chú thích dính vào giá trị ở wave 27/30, kiểm tra từng dòng và
đối soát tổng với bảng in. Bản CSV công khai có 48 dòng, không có hồ sơ cá nhân;
receipt SHA của PDF nguồn giữ ở local private artifacts.

| Phạm vi | Gửi | Giao được | Hoàn tất | Mail / hoàn tất | Online / hoàn tất | Hoàn tất / gửi |
|---|---:|---:|---:|---:|---:|---:|
| Waves 1–46, khớp PUF v7.0 | 270.729 | 261.964 | 74.193 | 54,45% | 45,55% | 27,40% |
| Waves 1–48, báo cáo FHFA | 281.942 | 272.448 | 76.405 | 53,99% | 46,01% | 27,10% |

Trong 46 wave thuộc PUF, tỷ lệ online trong số survey hoàn tất là **23,87% ở
wave 1** và **64,93% ở wave 46**, tăng mô tả 41,06 điểm phần trăm. Đây là thay
đổi thành phần kênh ở cấp wave, không phải tăng xác suất phản hồi online của cùng
một borrower. Wave 30 có 1.576 survey hoàn tất; FHFA ghi nhận response giảm và
nêu vaccine COVID cùng môi trường lãi suất là các khả năng, không xác định quan
hệ nhân quả.

## Từ survey trả về đến record trong PUF

FHFA Tables 4–6 giúp chốt mẫu số, nhưng các bảng đo ba giai đoạn khác nhau:

| Giai đoạn, waves 1–46 | Số lượng | Ý nghĩa |
|---|---:|---|
| Survey hoàn tất/trả về, Table 3 | 74.193 | Có thư trả về hoặc response online; chưa đồng nghĩa usable |
| Usable sau quality rules, Table 4 | 63.151 | Loại 2.009 duplicate/ineligible; 4.102 trả lời “No” Q1; 2.592 breakoff; 2.339 wrong loan |
| Trong bảng origination 2013–2024, Tables 5–6 | 62.359 | Khớp tổng số mortgage trong PUF v7.0 |

Table 4 categories cộng đúng về 74.193. Khoảng cách 792 giữa usable và PUF được
đối soát theo wave: 295 ở wave 7 (Table 5 footnote nói Tables 5–6 loại special
remote-rural sample) và 497 ở wave 45–46, nơi Tables 5–6 chỉ bao phủ origination
2013–2024. Đây là phép reconciliation các tổng công bố; không nối hồ sơ hoặc
chứng minh nguyên nhân từng dòng. App và Excel giữ riêng returned, disposition,
usable, origination-scope usable và phần chênh để không nhầm 74.193 returns với
62.359 PUF rows.

Table 4 chỉ có disposition tổng hợp theo wave, không chia các nhóm quality rule
theo mail/online. Vì vậy ngay cả khi biết tổng trả lời theo mode từ Table 3, vẫn
không thể tính usable-rate theo mode hay điều chỉnh selection của mode.

## Điều dữ liệu không cho phép kết luận

PUF v7.0 có 587 biến; rà field name và SAS label không thấy biến lưu người trả
lời hoàn tất bằng mail hay online. Những biến có chữ `online` mô tả đặc điểm vay
hoặc counseling, không phải kênh trả lời NSMO. Vì vậy không thể nối Table 3 với
`NSMOID`, so sánh outcome/score/forbearance theo mode ở cấp mortgage, hay fit
điều chỉnh mode từ chính PUF. Dữ liệu hiện có cũng không tách được mode drift
khỏi wave, thời điểm origination, thay đổi sample mix, questionnaire, nonresponse
hay điều kiện thị trường.

Đây là **gap về khả năng nhận dạng**, không thể giải bằng cách suy ra mode từ
missingness. FHFA mô tả online questionnaire có thể tự bỏ qua câu hỏi không áp
dụng, trong khi bản giấy không có cùng cơ chế skip tự động ở một số questionnaire
wave. Do đó chênh lệch câu trả lời/missingness giữa wave không được xem như
proxy cho response mode.

## Sampling và trọng số

FHFA cho biết mẫu được chọn khoảng 6.000 khoản vay mỗi quý từ closed-end first
lien mới vào NMDB; tỷ lệ lấy mẫu thay đổi theo volume origination. Sampled
mortgage không được chọn lại ở wave sau. Sau chọn mẫu, một số trường hợp opt-out,
địa chỉ/tên không dùng được hoặc do-not-contact bị loại; khảo sát tự nguyện.
Người nhận có thể trả bản tiếng Anh qua thư hoặc hoàn tất online bằng tiếng Anh/
Tây Ban Nha.

Technical Report mục 8 mô tả nonresponse model logistic riêng từng wave và theo
single/multiple borrower, dự đoán usable response từ thông tin hành chính/credit
đã có cho respondent và nonrespondent; xác suất nhóm thành 5 nhóm, inverse
response rate tạo điều chỉnh rồi nhân với sample weight. Danh sách biến gồm loan
amount, age, underwriting income, combined LTV, purchase/refinance, rate spread,
credit score, Census Division và nhân khẩu học. Cách này điều chỉnh **khả năng
usable response**, không phải phân bổ mail/online và không chứng minh các mode có
cùng sai số đo.

Mục 9 khuyến nghị survey procedures vì simple-random-sample standard errors sẽ
thấp hơn thực tế. PUF chỉ có `Analysis_Weight`; không có PSU/strata/replicate
weights trong 587 trường đã rà. Bởi vậy mode-response percentages trong Table 3
là phần trăm đếm thô, không phải mode-adjusted population estimates. Weight hiện
có không đủ để kiểm định mode effect hoặc tính đầy đủ design variance.

## Hệ quả cho D02

- **D02-2:** wave availability và một nhóm common-item wording đã được kiểm tra;
  response-mode drift hiện được đo ở aggregate, nhưng equivalence theo respondent
  không kiểm định được vì thiếu mode field. Hãy giữ kết luận descriptive/trend
  như hiện tại; không dùng mode làm feature, control hay giải thích causal.
- **D02-3:** response-mode selection là một lớp selection bổ sung khi diễn giải
  respondent answers; nó không thay đổi logic trạng thái performance `C/1/2/3–9`,
  nhưng làm tăng lý do phải mô tả mẫu trả lời/censoring theo wave và vintage.
- **Predictor allowlist:** survey answers sau origination tiếp tục bị loại khỏi
  origination model. Chỉ dùng field có thời điểm đo rõ là trước/đúng lúc
  origination sau khi review leakage và tính sẵn có; `Analysis_Weight` không phải
  predictor.
- **Nếu cần mode-specific inference:** cần FHFA cung cấp mode indicator hoặc
  bảng chéo đã được họ phê duyệt (mode × wave × nhóm/target) cùng hướng dẫn trọng
  số/variance. Không có file công khai bổ sung nào trong release v7.0 để tự suy
  ra liên kết này; hiện chưa gửi yêu cầu dữ liệu tới FHFA.

App `/nsmo` có bảng 48 wave và KPI cho đúng 46 wave trong PUF. Waves 47–48 được
hiển thị nhưng đánh dấu ngoài PUF. Workbook D02 cũng có sheet `NSMO returns`.
API và workbook kiểm tra SHA, sequence, phạm vi release, phép cộng count và tổng
Table 3 trước khi dùng.

## Tái lập

PDF nguồn tải từ [FHFA NSMO v7.0 Technical Documentation](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf), Table 3 trang in 10–11; các định nghĩa phương pháp ở mục 3, 8 và 9. Trang dữ liệu FHFA nói người tham gia có thể trả questionnaire tiếng Anh qua thư hoặc online bằng tiếng Anh/Tây Ban Nha, PUF v7.0 có 62.359 mortgage và waves 1–46: [FHFA NSMO PUF](https://www.fhfa.gov/data/nsmo). Ví dụ questionnaire waves 15–18 mô tả skip logic cho bản online: [FHFA questionnaire waves 15–18](https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-15-to-18).

```powershell
python scripts\audit_nsmo_survey_returns.py `
  --source-pdf data\private\mortgage\nsmo-2026-05-27\source_docs\nsmo-technical-report-v70.pdf `
  --output-csv docs\data\nsmo-v70-survey-returns.csv `
  --receipt artifacts\private\nsmo-survey-returns-audit-20261016\receipt.json
```

> The opinions and analyses contained herein are solely of the users/authors of any data analyses or papers, and the FHFA cannot and does not attest to nor vouch for the quality, accuracy, or timeliness of the data, or analyses derived from these data after the data has been retrieved from FHFA.gov.
