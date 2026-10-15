# D02-3/5 — Feasibility screen cho target snapshot 12 tháng

Cập nhật: 16/10/2026. Đây là phép kiểm tra khả năng quan sát endpoint trên PUF
NSMO v7.0, chưa phải quy trình target đã được phê duyệt. Dataset riêng D02; không
gộp với Freddie Mac D01.

## Câu hỏi và định nghĩa thử

PUF có đủ lịch sử theo quý để nghiên cứu một endpoint quan sát được trong 12
tháng sau một snapshot gốc không? Audit thử bốn snapshot quý kế tiếp (xấp xỉ 12
tháng), với ba tầng trạng thái gốc tách biệt:

- `C`: đang hiện hành — cohort ứng viên chính.
- `1`: trễ 30–59 ngày và `2`: trễ 60–89 ngày — chỉ là hai cohort nhạy cảm riêng,
  không gộp vào cohort hiện hành.
- Mã `3`–`6` (90 ngày trở lên) là endpoint chính ứng viên. Mã `7` (bankruptcy
  Chapter 13), `8` (foreclosure/surrender), `9` (các trạng thái giải quyết khác)
  được giữ thành trạng thái cạnh tranh riêng, không gộp thành một loại vỡ nợ.

Một snapshot chỉ được phân loại `four_quarters_observed_no_event` khi cả bốn quý
đều có mã quan sát được, không xuất hiện mã 3–9 và không bị đóng khoản vay trước
hay trong các snapshot đó. `A/B/K/M/P/Q/S` và ô trống không được coi là đang trả
nợ tốt; chúng dừng quan sát. Khoản vay có ngày đóng trước quý gốc không đủ điều
kiện. Vì chỉ có năm/tháng đóng, đóng trong cùng tháng với snapshot được gắn
`termination_same_month_ambiguous`, không phán thứ tự đóng hay sự kiện.

Định nghĩa này là **endpoint snapshot quan sát được**, không phải ngày phát sinh
quá hạn lần đầu: các quý có thể bỏ lỡ biến cố giữa kỳ. `Close_Status` chỉ nói mở/
kết thúc, không cho biết lý do nên không được diễn giải là trả trước hạn.

## Kết quả audit trên PUF thật

Audit streaming đọc 62.359 hồ sơ, 587 cột và 51 quý. Tất cả 147 tổ hợp quý × tầng
gốc có mặt được xuất dưới dạng tổng hợp private. Audit bổ sung group theo năm
origination để đếm baseline snapshot và support khoản vay duy nhất; receipt
ràng buộc SHA-256 của PUF tại
`artifacts/private/nsmo-target-unique-vintage-20261016/receipt.json`.

| Trạng thái gốc | Baseline snapshot có đủ 4 quý tiếp theo trong PUF | 90+ ngày quan sát được | Đủ 4 snapshot quan sát được, không thấy 90+ | Đóng cùng tháng, thứ tự không rõ | Kết thúc trước snapshot tiếp theo | Mất quan sát M/S |
|---|---:|---:|---:|---:|---:|---:|
| `C` | 872.888 | 2.174 | 738.773 | 42.236 | 83.092 | 6.196 |
| `1` | 4.022 | 756 | 2.641 | 126 | 203 | 259 |
| `2` | 1.202 | 504 | 502 | 21 | 69 | 93 |

Các số là **baseline-quarter snapshots**, không phải số khoản vay duy nhất. Một
khoản vay có thể xuất hiện ở nhiều quý gốc; các hàng không độc lập. Mã 7/8/9
xuất hiện riêng trong receipt và không nằm trong cột 90+ ngày. Các nguyên nhân
censor trên cũng không cộng thành một mẫu độc lập: mỗi snapshot nhận đúng kết
quả đầu tiên theo quy tắc tuần tự. Hai quý gốc cuối (2025Q2–Q3) không có đủ cửa
sổ quan sát; chúng được ghi thiếu theo dõi, không gán nhãn âm.

## Support duy nhất và khác biệt theo vintage

Đếm theo `open_year` cho thấy có khoảng **59,7 nghìn khoản vay duy nhất** có ít
nhất một baseline C với đủ cửa sổ bốn quý; những khoản vay này tạo ra 872,9 nghìn
snapshot C do lặp landmark qua thời gian. Khoảng **750 khoản vay duy nhất** có ít
nhất một baseline C mà trong bốn snapshot sau xuất hiện mã 3–6. Đây là support
cho thiết kế nhiều-landmark; cùng một khoản vay có thể được gán dương ở nhiều
landmark và cũng có thể mang phân loại khác ở landmark khác. Nó không phải số
default độc lập hay event rate.

Để thấy tác động của anchor, audit còn thử đúng một lần cho mỗi khoản vay: lấy
**C đầu tiên có đủ bốn quý theo dõi**. Quy tắc này cho 59.703 khoản vay, nhưng chỉ
156 khoản vay được phân loại 90+ trong cửa sổ sau anchor đó. Mã `7/8/9`, đóng
khoản vay, cùng-tháng và M/S được tách riêng; mỗi khoản vay chỉ có một kết quả
trong phép thử này. Chênh lệch 156 so với khoảng 750 khoản vay “ever positive” ở
mọi landmark cho thấy support phụ thuộc rất mạnh vào cách chọn thời điểm gốc.
Đây không phải hai cách ước lượng cùng một risk; chúng tương ứng với estimand
khác nhau. Anchor đầu tiên cũng không tương đương với ngày origination và không
được chọn làm chuẩn chỉ để tạo mẫu dương lớn hơn.

Vì vậy, trước modeling cần quyết định business question: (a) one-shot origination
risk, với origination date/quarter làm landmark, hay (b) dynamic quarterly
monitoring, với quy tắc landmark và lặp khoản vay được khai báo rõ. NSMO PUF có
survey/performance series, nhưng target này chưa chứng minh được một outcome
“default” chuẩn; trạng thái 90+ theo quý chỉ là proxy observed-delinquency. Với
one-shot C-first diagnostic chỉ có 156 positive outcomes trước temporal split,
không đủ căn cứ để hứa hẹn calibration ổn định hay mô hình nhiều biến.

Tỷ trọng snapshot C bị censor/ambiguous thay đổi theo năm origination. Các số
trong bảng được làm tròn; censor/ambiguous gộp khoản vay đóng trước snapshot kế
tiếp, đóng cùng tháng chưa rõ thứ tự và mã M/S. Mỗi tỷ trọng dùng denominator là
mọi full-horizon C baseline snapshots trong vintage band.

| Vintage origination | Khoản vay duy nhất có ≥1 C baseline | Full-horizon C baseline snapshots | Censor/ambiguous snapshots |
|---|---:|---:|---:|
| 2013–2016 | ~24.5k | ~511k | ~15% |
| 2017–2019 | ~14.7k | ~182k | ~23% |
| 2020–2021 | ~10.9k | ~130k | ~8% |
| 2022–2024 | ~9.6k | ~49k | ~10% |

Đây là khác biệt quan sát, chưa xác định nguyên nhân: vintage, thời gian trên
sổ, điều kiện thị trường và việc khoản vay đóng có thể cùng liên quan. Chênh lệch
này làm complete-case training có rủi ro đổi thành phần mẫu theo vintage; không
thể bỏ các khoản censored rồi diễn giải mẫu còn lại như ngẫu nhiên.

`Analysis_Weight` được lưu dưới dạng tổng mô tả theo nhóm, không áp lên kết quả
để tạo tỷ lệ. Không có thiết kế mẫu/replicate weights và variance method trong
audit này; không gọi các số trên là PD, incidence, default rate hay ước lượng
đại diện dân số.

## Trọng số và sai số lấy mẫu: hệ quả với model

Technical Documentation v7.0, mục 8, mô tả Analysis Weight là sampling weight
nhân với non-response adjustment. Điều chỉnh non-response được ước lượng logistic
riêng từng wave và theo single/multiple borrower; score xác suất chia thành năm
nhóm response, sau đó inverse response rate nhân với wave sample weight. Mục 9
cảnh báo phân tích giả định simple random sample sẽ đánh giá thấp standard error
và khuyến nghị survey procedures tính đến differential sampling và nonresponse
adjustment. Vì thế `Analysis_Weight` không thể bị hiểu là một trọng số tùy chọn
chỉ để đổi count sang tỷ lệ.

Trong 587 trường của PUF v7.0, audit schema thấy `Analysis_Weight` nhưng không
thấy cột PSU, strata hay replicate weights. Cũng chưa có thiết kế variance theo
wave/performance follow-up trong public file. Do đó:

- Không báo CI, p-value, significance, hoặc calibration uncertainty từ standard
  errors của simple random sample.
- Không giả vờ cluster-robust theo khoản vay đã khắc phục đầy đủ variance survey
  design; nó chỉ có thể xử lý lặp observation trong cùng khoản vay.
- Trước suy luận thống kê, cần FHFA xác nhận thiết kế/replicate information
  thích hợp cho endpoint v7.0. Nếu không có, giữ kết quả ở mức mô tả và nêu rõ
  giới hạn.
- Nếu thử model để học quy trình, chỉ báo score/calibration trên temporal split
  như hiệu năng nội bộ sample; không gọi là population PD và đánh giá sensitivity
  riêng khi có/không có Analysis_Weight.

Technical report cũng nêu mỗi quý lấy mẫu khoảng 6.000 khoản vay mới vào NMDB,
trong khi tỷ lệ lấy mẫu thay đổi theo số lượng origination; vì vậy phải giữ
cohort/vintage gốc khi chia train và đánh giá theo thời gian.

## Đánh giá và bước quyết định

**Kết luận feasibility:** PUF có đủ một số snapshot C với bốn quý theo dõi được
để tiếp tục đánh giá endpoint, nhưng target chưa đủ điều kiện freeze cho model.
42.236 baseline snapshot C có thứ tự đóng/snapshot không rõ trong cùng tháng,
83.092 bị censor do khoản vay kết thúc trước snapshot kế tiếp, và còn 6.196 mất
quan sát qua M/S. Cần xác thực lại thứ tự event-versus-termination cùng tháng,
phân tích mẫu còn quan sát so với bị censor, và xác lập variance/design weights.

Trình tự khuyến nghị trước khi model:

1. Đóng băng cohort chính `C`; giữ `1` và `2` thành phân tích sensitivity riêng.
2. Chốt policy cho mã `7`, `8`, `9`: competing outcomes riêng, không coi là
   negative hay gộp vào endpoint 90+.
3. Xác minh quan hệ `Close_Year/Month`, performance snapshot và code `A` trong
   documentation FHFA; nếu không lấy được ngày chính xác, giữ cùng-tháng là
   ambiguous/censor như audit này.
4. Quyết định estimand: endpoint tích lũy quan sát được trong bốn snapshot hay
   mô hình multi-state/survival có competing risk. Không gọi endpoint quarterly
   là 12-month PD.
5. Đánh giá attrition/censoring theo cohort, vintage, trạng thái gốc và nhóm mẫu;
   chọn xử lý censoring có căn cứ, không tự động bỏ nhóm censored khỏi mẫu rồi
   tuyên bố kết quả không lệch.
6. Xác định sample design, weight, strata/PSU/replicate weights và cách tính
   uncertainty. Nếu không có variance method phù hợp, giới hạn báo cáo ở mô tả
   không suy luận.
7. Sau review trên mới tạo target tái lập, split theo thời gian, kiểm tra leakage
   và tính calibration/threshold metrics.

Hiện trạng D02-5: **preliminary candidate assessed; protocol not frozen; no
target labels/model/PD created**. Audit code là
`scripts/audit_nsmo_target_feasibility.py`; synthetic edge tests là
`tests/test_nsmo_target_feasibility.py`.

## Hạn chế nguồn

Mã trạng thái lấy từ SAS formats chính thức trong gói FHFA v7.0; các mô tả từ
Appendix C có thể có sai khác release như ghi chú termination-field version
trong `NSMO_D02_CASE_BUILD_PLAN_VI.md`. Nguồn và disclaimers chính thức:
[FHFA NSMO](https://www.fhfa.gov/data/nsmo), [technical report v7.0](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf),
[Appendix C v7.0](https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-c-v70.pdf).
