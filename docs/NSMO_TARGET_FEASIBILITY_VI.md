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

### Status trong snapshot trùng tháng đóng

Audit bổ sung đối chiếu performance code của đúng quý có tháng kết thúc trùng
tháng snapshot. Cả 42.236 trường hợp baseline `C`, 126 baseline `1`, và 21
baseline `2` đều có code `A` tại snapshot bị buộc cùng-tháng. Theo Appendix C,
`A` là performance history không còn được báo cáo, trong đa số trường hợp sau
khi khoản vay đóng; codebook cũng yêu cầu đọc `A/B` cùng các trường close status,
year và month. Phân bố này giải thích trạng thái được lưu tại các quan sát
tied-month, nhưng vẫn không cung cấp ngày trong tháng để xác định thứ tự snapshot
so với termination. Do đó các trường hợp vẫn là ambiguous/censor, không được
chuyển sang nhóm không quá hạn hoặc event.

Dashboard hiển thị các tổng này và bảng theo vintage/state. Bộ lọc vintage dùng
chung với các feasibility panel khác. Bảng chỉ phân tích mã quan sát được trong
quý bị buộc cùng-tháng; nó không thay đổi risk-set hoặc outcome protocol.

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
`tests/test_nsmo_target_feasibility.py`. Phần aggregate-only được phục vụ qua
`GET /api/nsmo-target-feasibility`, hash-bound với cùng PUF SHA-256 như profile;
trang `/nsmo` so sánh anchor, lọc vintage, xem support theo quý và giữ warning
không diễn giải thành PD.

## Sensitivity theo độ dài horizon: 6, 12 và 24 tháng

Cập nhật 16/10/2026: audit aggregate-only mới so sánh 2, 4 và 8 snapshot quý
kế tiếp từ mỗi baseline `C`. Chỉ xét baseline có đủ số quý theo dõi đến cuối
horizon; giữ 90+ (`3`–`6`), competing adverse (`7`–`9`), kết thúc trước kỳ,
cùng-tháng ambiguous và M/S censor thành các nhóm riêng. Mỗi mortgage được
deduplicate trong bộ nhớ khi đếm support unique; receipt không ghi ID.

| Horizon | Baseline C snapshots đủ cửa sổ | Mortgage unique có ≥1 baseline đủ cửa sổ | Snapshot 90+ quan sát được | Mortgage unique có ≥1 snapshot 90+ | Kết thúc trước kỳ tiếp theo | Đóng cùng tháng ambiguous | M/S censor |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 quý (~6 tháng) | 926.331 | 61.645 | 964 | 623 | 44.695 | 22.849 | 3.437 |
| 4 quý (~12 tháng) | 872.888 | 59.703 | 2.174 | 753 | 83.092 | 42.236 | 6.196 |
| 8 quý (~24 tháng) | 770.257 | 55.701 | 3.683 | 735 | 140.280 | 71.229 | 9.937 |

Số mortgage unique có 90+ là **outcome support trong tập baseline đủ horizon**,
không phải số sự kiện độc lập và không phải tỷ lệ. Các tập baseline của ba
horizon không lồng nhau: horizon dài loại các baseline ở cuối PUF vì thiếu follow-up;
vì vậy 735 unique ở 24 tháng thấp hơn 753 ở 12 tháng không mâu thuẫn và không
cho thấy risk giảm. Mortgage có thể xuất hiện ở nhiều baseline quý và cùng loan
có thể xuất hiện ở các outcome class khác nhau theo từng baseline quý.

Khi horizon tăng, competing termination/cùng-tháng ambiguity tăng đáng kể, còn
follow-up đủ quan sát giảm. Đây là trade-off thiết kế quan trọng: cửa sổ ngắn có
ít tín hiệu 90+ hơn; cửa sổ dài có nhiều thời gian để thấy 90+ nhưng cũng tích
lũy thêm censor và làm cohort khả dụng nhỏ hơn. M/S censor và termination không
được chuyển thành negative. Không tính tỷ lệ, CI, PD hay model từ bảng này.

Receipt riêng, aggregate-only và source-hash-bound:
`artifacts/private/nsmo-horizon-sensitivity-20261016/receipt.json`.
Tái lập bằng `scripts/audit_nsmo_horizon_sensitivity.py`; edge tests nằm trong
`tests/test_nsmo_horizon_sensitivity.py`. Kết quả sensitivity củng cố quyết định
hiện tại: D02-5 vẫn mở để chốt estimand/cohort/censoring; chưa tạo target labels
và chưa bắt đầu D02-6 modeling.

## Đối chiếu chuyển tiếp kề quý và lần đầu quan sát 90+

Cập nhật 16/10/2026: một audit độc lập đếm mọi chuyển tiếp kề snapshot từ C/1/2
sang mã 3–6, rồi đối chiếu với số mortgage duy nhất và trạng thái ngay trước
lần đầu tiên 3–6 xuất hiện trong chuỗi. Audit xác nhận 62.359 `NSMOID` không
trùng, 0 dòng sai độ rộng, trên cùng PUF SHA-256. ID chỉ tồn tại trong bộ nhớ
để kiểm tra uniqueness/deduplicate; receipt không ghi ID hoặc dòng dữ liệu.

| Trạng thái ngay trước snapshot 90+ | Số chuyển tiếp kề quý (có lặp) | Mortgage duy nhất có ≥1 chuyển tiếp | First-observed 90+ ngay sau trạng thái này |
|---|---:|---:|---:|
| `C` hiện hành | 322 | 296 | 252 |
| `1` trễ 30–59 ngày | 363 | 322 | 275 |
| `2` trễ 60–89 ngày | 393 | 330 | 278 |

Trong 859 mortgage có lần đầu **được quan sát** ở trạng thái 3–6 trong chuỗi,
805 có quý ngay trước đó ở C/1/2; 4 có trạng thái 7–9 trước đó; 50 không có
trạng thái quan sát liền trước (bao gồm history bắt đầu tại 90+ hoặc khoảng trống
trước đó). Phân hoạch 805 + 4 + 50 = 859 được kiểm tra trong receipt. Các tổng
theo vintage và từng trạng thái nguồn nằm trong bảng lọc trên `/nsmo`.

Đây là một mô tả bổ sung, không thay đổi kết luận về support: nhiều chuyển tiếp
của cùng mortgage phụ thuộc nhau; first-observed 90+ không khẳng định ngày/lần
quá hạn đầu tiên thật vì quarterly snapshots bỏ qua diễn biến giữa kỳ. Audit
chưa lọc competing termination hoặc xác lập risk set, chưa xử lý survey variance,
không tính rate/PD và không tạo target. Vì vậy D02-5 vẫn chưa đóng băng và D02-6
vẫn chưa được bắt đầu.

Audit tái lập:

```powershell
$env:PYTHONPATH = 'src'
python scripts\audit_nsmo_first_observed_transition_support.py `
  --puf-csv data\private\mortgage\nsmo-2026-05-27\puf\nsmo_v70_1324_puf.csv `
  --output artifacts\private\nsmo-first-observed-transition-support\receipt.json
```

## Dynamic risk-set: một lần vào đầu tiên sau origination

Cập nhật 16/10/2026: thêm một feasibility audit riêng cho cách nhìn dynamic.
Mỗi mortgage chỉ được vào risk set tại snapshot C/1/2 đầu tiên sau quý mở khoản
vay; quý mở (Q) bị loại. Các quý tiếp theo chỉ đóng góp interval khi hai snapshot
kề nhau đều quan sát được và khoản vay chưa thoát risk set. Audit trên 62.359
mortgage cho thấy 57.311 đủ điều kiện vào; trạng thái entry là C: 57.233, 1: 69,
2: 9. Tổng support là 887.861 loan-quarter intervals, không trọng số.

Lần thoát đầu tiên sau entry gồm 695 snapshot 90+; 97 competing states 7–9;
1.515 lần censor do mã M/S; 20.557 kết thúc trước snapshot kế tiếp; 10.645 đóng
cùng tháng nên thứ tự đóng/snapshot không xác định; và 23.802 hết cửa sổ dữ liệu.
Các nhóm cộng lại bằng 57.311 entry. Trước entry, 4.270 khoản bị loại do K,
133 do M/S, 8 có competing state 7/9, 2 đã quan sát 90+, 413 đóng trước baseline
và 222 đóng cùng tháng trước baseline. Các nhóm này là population accounting,
không phải tỷ lệ sự kiện.

Kết quả này làm rõ quy mô dữ liệu có thể hỗ trợ phân tích nhiều trạng thái với
delayed entry, nhưng không giải quyết selection: khoản vay phải còn quan sát và
chưa rơi vào các trạng thái loại trừ để sống tới entry. Quarterly status 3–6 chỉ
là snapshot, không cho ngày bắt đầu quá hạn; close month không cho thứ tự chính
xác. Vì vậy không diễn giải 695 là incidence/default rate hay PD, không dùng
interval lặp như quan sát độc lập, và chưa có target/model. Cần phân tích
selection/censoring theo vintage và entry state, xác nhận estimand cùng policy
cho competing termination, và chốt survey design/variance trước khi cân nhắc
đóng protocol.

Workbook/API/UI chỉ cung cấp aggregate unweighted support; receipt source-bound
với SHA-256 PUF và không chứa ID hoặc loan rows. Bảng này xuất hiện trong `/nsmo`
như feasibility panel, với bộ lọc entry state và vintage.

### Entry selection by origination vintage

Audit mới đối chiếu toàn bộ population PUF với lý do trước-entry, theo năm mở
khoản vay. Entry share ở đây là `mortgages entered / mortgages in that PUF
origination vintage`; nó chỉ mô tả selection vào risk set của audit. Nó không
phải tỷ lệ delinquency, incidence hay PD.

| Vintage | PUF mortgages | Entered C/1/2 | Entry share | Pre-entry non-observation | Closed before / same-month entry | Pre-entry 90+ / adverse 7–9 |
|---|---:|---:|---:|---:|---:|---:|
| 2013 | 6,063 | 5,071 | 83.64% | 965 | 13 / 11 | 1 / 2 |
| 2014 | 6,250 | 5,434 | 86.94% | 759 | 28 / 29 | 0 / 0 |
| 2015 | 6,169 | 5,537 | 89.76% | 584 | 32 / 13 | 0 / 3 |
| 2016 | 6,269 | 5,726 | 91.34% | 476 | 39 / 28 | 0 / 0 |
| 2017 | 5,148 | 4,700 | 91.30% | 408 | 29 / 10 | 0 / 1 |
| 2018 | 4,687 | 4,360 | 93.02% | 282 | 35 / 10 | 0 / 0 |
| 2019 | 5,004 | 4,727 | 94.46% | 208 | 43 / 24 | 0 / 2 |
| 2020 | 5,637 | 5,459 | 96.84% | 136 | 23 / 19 | 0 / 0 |
| 2021 | 5,379 | 5,127 | 95.32% | 200 | 34 / 18 | 0 / 0 |
| 2022 | 3,854 | 3,636 | 94.34% | 179 | 22 / 17 | 0 / 0 |
| 2023 | 3,936 | 3,714 | 94.36% | 131 | 68 / 23 | 0 / 0 |
| 2024 | 3,963 | 3,820 | 96.39% | 75 | 47 / 20 | 1 / 0 |

The entry share ranges from 83.64% to 96.84%; 2013 has the most pre-entry
non-observation (965), versus 75 for 2024. This is consistent with the risk-set
definition removing loans whose prior history is unknown, but does not identify
why missingness differs or establish that the excluded loans have different
risk. The apparent vintage pattern therefore needs sensitivity analysis before
any outcome comparison. The app's “Entry selection by origination vintage” table
shows the full partition and filters with the shared vintage selector. The
separate code table retains K/M/S: PUF-wide pre-entry counts are 4,270 K, 64 M,
and 69 S. For 2013 the split is 951/6/8; for 2024 it is 65/6/4. Other
pre-entry missing codes and the administrative/no-baseline exclusions are zero
in this PUF, and remain separate fields in the aggregate API.

Rebuild the private aggregate receipt after obtaining the current PUF:

```powershell
python scripts\audit_nsmo_first_entry_risk_set.py `
  --puf-csv data\private\mortgage\nsmo-2026-05-27\puf\nsmo_v70_1324_puf.csv `
  --output artifacts\private\nsmo-first-entry-risk-set-20261016\receipt.json
```

Receipt riêng tư hiện tại: `artifacts/private/nsmo-first-observed-transition-support-20261016/receipt.json`.
API `/api/nsmo-first-observed-transition-support` xác minh receipt với SHA-256
PUF trước khi trả aggregate cho `/nsmo`; browser acceptance mở rộng đạt 10/10
checks, gồm totals, bộ lọc vintage, bảng 36 vintage/state groups và cuộn bảng
trên màn hình mobile. Focused API/view/audit tests đạt 19/19.

## Hạn chế nguồn

Mã trạng thái lấy từ SAS formats chính thức trong gói FHFA v7.0; các mô tả từ
Appendix C có thể có sai khác release như ghi chú termination-field version
trong `NSMO_D02_CASE_BUILD_PLAN_VI.md`. Nguồn và disclaimers chính thức:
[FHFA NSMO](https://www.fhfa.gov/data/nsmo), [technical report v7.0](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf),
[Appendix C v7.0](https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-c-v70.pdf).
