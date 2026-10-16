# D02 / NSMO — đánh giá risk set và khả năng lập target

Ngày đánh giá: 16/10/2026  
Nguồn: FHFA NSMO Public Use File v7.0, cập nhật 27/05/2026. FHFA hiện vẫn
liệt kê bản này là phiên bản mới nhất; PUF có 62.359 mortgage gốc trong các
vintage 2013–2024 và 51 snapshot hiệu suất theo quý đến 2025Q3. Đây là một
population riêng, không phải vintage Freddie Mac và không được nối hay gộp
loan-level với D01. [Trang nguồn NSMO của FHFA](https://www.fhfa.gov/data/nsmo)

## Câu hỏi và phạm vi

Đánh giá xem PUF có đủ quan sát để xây một nghiên cứu **behavioral risk theo
quý** hay không. Kết quả dưới đây là feasibility screen tổng hợp: không tạo
nhãn loan-level, không ước lượng tỷ lệ rủi ro/PD, không fit model và không
đưa ra suy luận cho toàn bộ thị trường mortgage Mỹ.

Raw PUF và receipt chi tiết nằm ở D: trong vùng private. Auditor ghi số liệu
tổng hợp, không ghi NSMOID. Ba lần chạy dùng cùng file nguồn 62.359 × 587,
51 cột performance; SHA-256 nguồn giống nhau. Receipt private:

- `artifacts/private/nsmo-first-entry-risk-set-20261016/receipt.json`
- `artifacts/private/nsmo-target-feasibility-postopen-20261016/receipt.json`
- `artifacts/private/nsmo-horizon-sensitivity-postopen-20261016/receipt.json`

## Quy tắc thời gian đã áp dụng

PUF chỉ ghi tháng mở khoản, không có ngày. Vì vậy baseline quarter-end chỉ
được xét **sau quarter chứa tháng mở khoản**. Quarter chứa tháng mở bị loại do
không biết snapshot được ghi trước hay sau ngày mở. Auditor 12 tháng và horizon
sensitivity áp dụng cùng điều kiện này; kiểm thử regression khóa trường hợp
snapshot cùng quarter với ngày mở.

Với feasibility target, baseline là trạng thái `C` (current), primary event
là snapshot `3`–`6` (90+ DPD), còn `7`–`9` được giữ thành nhóm adverse riêng.
Horizon lần lượt là 2, 4 hoặc 8 snapshot kế tiếp (xấp xỉ 6, 12 hoặc 24 tháng).
Event được tính khi xuất hiện trước censor/termination; non-observation không
được đổi thành negative. Khoản đóng trước quarter snapshot là competing
censor; đóng cùng tháng với snapshot là ambiguous vì không có ngày để sắp thứ
tự.

Đây là một **cấu hình ứng viên để đo feasibility**, chưa phải target contract
được freeze. Mỗi mortgage chỉ được lấy baseline `C` đủ horizon sớm nhất trong
phân tích one-landmark; không lấy nhiều landmark lặp để thổi phồng support.

## Kết quả theo ba cách nhìn

| Cách nhìn | Quan sát đã xác nhận | Ý nghĩa và giới hạn |
|---|---:|---|
| Một baseline `C` sớm nhất, horizon 6 tháng | 61.645 mortgage; 41 quan sát 90+; 58.232 hoàn tất quan sát mà không gặp event; 209 censor do `M/S`; 1.921 close trước snapshot; 1.236 close cùng tháng; 6 trạng thái adverse khác | Chỉ 41 event trên anchor duy nhất; chưa đủ căn cứ cho model hoặc market rate |
| Một baseline `C` sớm nhất, horizon 12 tháng | 59.703 mortgage; 156 quan sát 90+; 51.836 hoàn tất quan sát không gặp event; 357 censor `M/S`; 4.674 close trước snapshot; 2.656 close cùng tháng; 24 adverse khác | 156 là số event support thô, không phải PD. Chưa xử lý thiết kế survey/variance, selection và nonresponse |
| Một baseline `C` sớm nhất, horizon 24 tháng | 55.701 mortgage; 302 quan sát 90+; 41.240 hoàn tất quan sát không gặp event; 618 censor `M/S`; 8.748 close trước snapshot; 4.740 close cùng tháng; 53 adverse khác | Horizon dài làm mất support do termination/censoring; không được coi các trường hợp này là negative |
| First-entry dynamic screen từ `C/1/2` | 57.311 khoản vào screen; 887.861 mortgage-quarter intervals; 695 first observed 90+; 23.802 kết thúc hành chính; 20.557 termination trước snapshot kế; 10.645 tie cùng tháng; 363 `M`, 1.152 `S`, 97 adverse `7–9` | Là chuỗi exposure độ dài khác nhau; 695 event không phải kết quả binary cố định 12 tháng, cũng không phải tỷ lệ event |

Ở anchor 12 tháng, số event 90+ theo origination vintage là: 2013 **10**,
2014 **15**, 2015 **16**, 2016 **19**, 2017 **13**, 2018 **15**, 2019 **6**,
2020 **5**, 2021 **4**, 2022 **20**, 2023 **21**, 2024 **12**. Từng vintage
đều có ít event để tách train/calibration/validation/final OOT theo protocol
độc lập. Những số này là unweighted feasibility counts.

Các horizon sensitivity cho thấy event anchor lần lượt là **41 / 156 / 302**
ở 6 / 12 / 24 tháng. Snapshot lặp trên cùng mortgage có thể tăng số hàng,
nhưng tạo phụ thuộc trong loan; phải định trước landmark selection, split
theo mortgage và clustered uncertainty trước khi xem đó là thêm support.

## Quyết định nghiên cứu hiện tại

1. Giữ NSMO là D02 riêng; không gọi đây là Freddie PD12, không trộn loan IDs,
   labels, model artifacts hoặc population với D01.
2. Dùng trang hiện tại cho descriptive monitoring, source/codebook evidence
   và sensitivity. Chưa fit model và chưa công bố event rate hay PD.
3. Nếu tiếp tục target research, dùng “first observed 90+ (`3`–`6`) within the
   next four quarterly snapshots from one earliest eligible current (`C`)
   landmark” làm **ứng viên để review**, không tự động đóng băng. `7`–`9`,
   `A/B/K/M/P/Q/S`, blank/unknown và administrative end phải giữ phân loại
   competing/censor riêng theo codebook và source timing.
4. Trước khi freeze cần review item-level wording, wave routing, respondent
   role, answer scale và vintage comparability cho feature; hoàn thiện survey
   weight/nonresponse/design variance; đối chiếu semantics termination; định
   trước cách xử lý same-month closure, competing risks, missingness và
   landmark selection.
5. Sau các bước trên, quyết định lại support. Với 4–21 anchor events mỗi
   vintage, kỳ vọng hợp lý hiện tại là D02 descriptive/feasibility, không phải
   model validation. Chỉ mở external comparison nếu common feature contract,
   target estimand và support được chứng minh riêng.

## Kiểm chứng kỹ thuật

Hai auditor target/horizon đều reconcile 62.359 dòng, 587 cột và 51 status
quarters. Regression suite liên quan chạy **17/17**. Điều kiện post-origination
không đổi các tổng anchor hiện tại vì PUF đã đánh dấu giai đoạn trước mở bằng
`P`; thay đổi này làm rõ và kiểm tra điều kiện bằng thời gian thay vì ngầm
trông cậy vào code trạng thái. `target_created=false` vẫn được giữ ở cả ba
receipt. Không có sửa đổi model readiness hay completion count của D01.

