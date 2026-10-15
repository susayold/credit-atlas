# NSMO v7.0 — kiểm toán khả năng so sánh qua survey wave

Cập nhật: 15-10-2026. Đây là phần việc riêng của D02 NSMO; không ghép vào Freddie D01.

## Kết quả đã xác minh

- FHFA công bố questionnaire theo từng gói wave. Đã tải 22 gói không trùng lặp, bao phủ wave 1–46; bản PDF và receipt SHA-256 ở kho riêng, ngoài GitHub. Nguồn và trạng thái gói xem tại [FHFA NSMO](https://www.fhfa.gov/data/nsmo).
- Audit PUF đọc 62.359 dòng, 319 trường survey và 46 `survey_wave`; đủ **14.674/14.674** ô trường-wave, khớp miền value-format SAS, không có giá trị không ánh xạ. Chỉ xuất số lượng tổng hợp; không xuất ID hay hàng dữ liệu.
- Có **130/319** trường chứa wave mà mọi dòng trong wave được SAS mã `-3` (“Not asked in wave”); **188/319** có ít nhất một mã trả lời trong cả 46 wave; **76/319** có mã `-2` (“Not applicable”) ở ít nhất một wave. “Có câu trả lời trong mọi wave” chỉ là tính sẵn có của cột trong PUF, không chứng minh cùng cách hỏi hay cùng construct.
- `x14a` và `x14a_1` là ví dụ không được gộp mã thô: `x14a` dùng format PIMPFM (Important/Not important), xuất hiện ở wave 7–46; `x14a_1` dùng PVERYFM (Very/Somewhat/Not at all), xuất hiện ở wave 1–6. Code `1` không có cùng ý nghĩa giữa hai thang.
- `x20j` cho thấy nên dùng coverage thực tế theo SAS: câu hỏi dịch tài liệu sang ngôn ngữ chính có câu trả lời ở wave 13–24 và mã not-asked ở các wave khác. Trường `survey_wave_ranges` do trích xuất bảng codebook tự động có thể gom nhầm phạm vi từ câu hỏi lân cận; không dùng riêng cột này làm allowlist.
- Một pilot dò trực tiếp item trong cả 22 questionnaire PDFs tìm được sáu exact item phrases trong **22/22 gói**: `x05f` (familiarity với credit history/score), `x88d/e/f` (late-payment/default attitudes), `x93b` (khó khăn trả mortgage) và `x94a` (trả bill 3 tháng không vay). Các SAS format cũng cho cùng loại response scale xuyên versions: PVERYFM (Very/Somewhat/Not at all) cho `x05f`, `x93b`, `x94a`; PAGREEFM (Agree/Disagree) cho `x88d/e/f`. Đây là nhóm **common-item candidates có bằng chứng tốt để mô tả trend**, nhưng chưa phải measurement-invariance test: sample/nonresponse/weight mix, routing và survey mode vẫn cần kiểm định. Các câu trả lời vẫn được thu sau origination nên không được dùng làm predictor tại origination.

## Cách diễn giải questionnaire

Trình phân tích PDF tách block theo số câu để định vị biến thể, nhưng số thứ tự câu dịch chuyển giữa các phiên bản và một số PDF bố trí hai cột khiến text extraction trộn thứ tự đáp án. Trong 91 số câu nhận diện được, chỉ một số có một block text trùng tuyệt đối giữa các gói chứa cùng số câu (Q90 xuất hiện trong bốn gói đầu); điều này **không** có nghĩa chỉ một câu hỏi ổn định, mà cho thấy phép so khớp số câu và chuỗi chính xác chưa đủ để phân loại construct. Các cờ `MULTI_QUESTION_ID`, `DIFFERENT_SCALE`, `NOT_ASKED_IN_SOME_WAVES` của codebook là tín hiệu sàng lọc, không phải kết luận đo lường tương đương.

Muốn đưa một biến vào nhóm “so sánh xuyên wave”, cần đối chiếu ở cấp từng item: prompt, đối tượng (respondent/spouse), mốc thời gian câu hỏi, routing/skip, đáp án và nhãn SAS; với trường định lượng còn phải đối chiếu đơn vị, ngưỡng và cách bin. Nếu khác wording nhưng có thể có cầu nối, giữ các phiên bản riêng và chỉ chuẩn hóa sau khi có bằng chứng; không tự động map mọi code 1/2 hoặc gộp bằng tên biến.

Pilot crosswalk đã xuất thành [`nsmo-v70-wave-item-comparability.csv`](data/nsmo-v70-wave-item-comparability.csv); cột `assessment` ghi rõ candidate và biến không được gộp. File là metadata plus wave-range summaries, không chứa row data hay exact cell counts.

## Ý nghĩa cho credit-risk project

Các câu về hiểu biết tín dụng, trải nghiệm vay, cảm nhận khả năng trả nợ, khó khăn tài chính và sức chống chịu hộ gia đình là câu trả lời khảo sát sau thời điểm origination. Chúng có thể dùng cho mô tả trải nghiệm người vay hoặc phân tích khả năng dự báo tại đúng ngày khảo sát nếu thiết kế target và thời gian được đóng băng riêng. Chúng **không** là predictor tại origination cho D01 hay D02 chỉ vì nhãn có liên quan tín dụng. Những biến này cũng không thay thế lịch sử bureau, DTI/LTV tại thời điểm giải ngân, hay target hiệu suất khoản vay.

App `/nsmo` hiển thị thêm wave trả lời quan sát được, wave toàn bộ mã `-3`, wave một phần `-3`, wave có `-2`, tách khỏi phần wave được nhắc trong codebook. Màn này là dữ liệu coverage không trọng số; chưa có phân tích khác biệt nonresponse, design variance, DIF/measurement invariance, hoặc kiểm định trend.

## Tái lập trong workspace riêng

```powershell
python scripts\acquire_nsmo_questionnaires.py `
  --output-dir data\private\mortgage\nsmo-2026-05-27\questionnaires `
  --receipt artifacts\private\nsmo-questionnaire-acquisition-20261015\receipt.json

python scripts\audit_nsmo_questionnaire_variants.py `
  --acquisition-receipt artifacts\private\nsmo-questionnaire-acquisition-20261015\receipt.json `
  --output artifacts\private\nsmo-questionnaire-variant-audit-20261015\receipt.json

python scripts\audit_nsmo_wave_response_coverage.py `
  --puf-csv data\private\mortgage\nsmo-2026-05-27\puf\nsmo_v70_1324_puf.csv `
  --field-dictionary docs\data\nsmo-v70-field-dictionary.csv `
  --value-labels docs\data\nsmo-v70-value-labels.csv `
  --output artifacts\private\nsmo-wave-response-coverage-20261015\receipt.json `
  --public-coverage-csv docs\data\nsmo-v70-wave-coverage.csv

python scripts\audit_nsmo_key_item_versions.py `
  --acquisition-receipt artifacts\private\nsmo-questionnaire-acquisition-20261015\receipt.json `
  --field-dictionary docs\data\nsmo-v70-field-dictionary.csv `
  --value-labels docs\data\nsmo-v70-value-labels.csv `
  --wave-coverage docs\data\nsmo-v70-wave-coverage.csv `
  --output artifacts\private\nsmo-key-item-version-audit-20261015\receipt.json `
  --comparability-csv docs\data\nsmo-v70-wave-item-comparability.csv
```

Questionnaire PDFs, full question-text extracts and exact field-wave counts remain private. Public CSV contains sanitized field-level wave ranges only. Include FHFA's required disclaimer when publishing substantive analyses of the PUF.
