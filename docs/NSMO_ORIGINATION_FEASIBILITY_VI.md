# D02-5 — Feasibility của endpoint quan sát neo theo tháng mở khoản vay

Cập nhật: 16/10/2026. Đây là audit tổng hợp trên NSMO PUF v7.0, không phải
target đã phê duyệt, tỷ lệ PD hay mô hình. Audit dùng duy nhất `open_year`,
`open_month` và các snapshot hiệu suất theo quý; không tạo nhãn ở cấp khoản vay.

## Câu hỏi

PUF có đủ support quan sát để thử một endpoint 90+ ngày trong khoảng 12 tháng
sau tháng mở khoản vay không? Phép thử loại bỏ quý mở khoản vay vì FHFA định nghĩa
mã `Q` là “loan opened during this quarter”, không phải trạng thái trả nợ quan
sát được. Sau đó chỉ xem các quý kết thúc sau quý mở khoản vay và không muộn hơn
12 tháng kể từ `open_year`/`open_month`.

Endpoint chính ứng viên là snapshot đầu tiên có mã `3`–`6` (90+ ngày). Mã `7`–`9`
được giữ riêng là trạng thái bất lợi cạnh tranh; `K`, `M`, `S`, ô trống và trạng
thái không quan sát được giữ là censor/thiếu theo đúng nguyên nhân. Khoản vay
đóng trước snapshot kế tiếp là competing censor; đóng cùng tháng snapshot là mơ
hồ thứ tự vì PUF chỉ có năm/tháng đóng.

## Kết quả tổng hợp

PUF có 62.359 khoản vay, 587 trường và 51 snapshot quý đến 2025Q3. Phân loại
unweighted cho phép thử này:

| Kết quả trong cửa sổ theo dõi | Số khoản vay |
|---|---:|
| Quan sát mã 3–6 ít nhất một lần | 65 |
| Mọi snapshot trong cửa sổ đều quan sát được, không thấy mã 3–6 | 53.184 |
| Chưa báo cáo bởi servicer (`K`) | 4.270 |
| Thiếu khoảng lưu trữ lịch sử (`M`) | 137 |
| Servicer suppress (`S`) | 216 |
| Đóng trước snapshot kế tiếp | 2.622 |
| Đóng cùng tháng snapshot, thứ tự chưa rõ | 1.569 |
| Trạng thái cạnh tranh 7–9 | 17 |
| Thiếu các snapshot cuối do giới hạn dữ liệu | 279 |
| **Tổng** | **62.359** |

Số outcome 90+ phân tán ít trong các vintage: 2013: 4; 2014: 3; 2015: 5;
2016: 6; 2017: 6; 2018: 5; 2019: 4; 2020: 2; 2021: 2; 2022: 9; 2023: 9;
2024: 10. Đây là số quan sát trong mẫu PUF, không phải số sự kiện độc lập đại
diện dân số hay event rate. 65 sự kiện là support quá mỏng để biện minh cho một
mô hình có nhiều predictor và đánh giá temporal ổn định.

Phần tổng hợp này đã được gắn vào workspace `/nsmo` dưới nhãn
**Origination-aligned · feasibility only**. Bảng vintage dùng chung bộ lọc
vintage với panel landmark; API `/api/nsmo-origination-feasibility` chỉ trả số
đếm đã qua reconciliation và kiểm tra SHA-256 nguồn. Edge headless QA trên PUF
thật đạt 8/8 checks, không có lỗi JavaScript; API/view tests đạt 20/20.

## Giới hạn phương pháp

- `open_month` không có ngày mở cụ thể. Cửa sổ +12 tháng chỉ chính xác ở cấp
  tháng; snapshot quý làm số mốc có thể dùng thay đổi giữa ba và bốn.
- Quý mở khoản vay có mã `Q`, nên không có performance status dùng được trong
  chính quý đó. Sự kiện có thể xảy ra giữa các lần báo cáo hoặc trước snapshot
  đầu tiên sau quý mở.
- Mã 3–6 là trạng thái 90+ tại snapshot; PUF không cung cấp chính xác ngày sự
  kiện. Không thấy mã 3–6 trong các snapshot quan sát được không chứng minh rằng
  khoản vay chưa từng quá hạn 90+ giữa hai quý.
- Không gán âm cho `K/M/S`, thiếu snapshot cuối, đóng khoản vay hay mã 7–9.
  Nguyên nhân đóng khoản vay không có trong trường đóng.
- Counts là unweighted support. Không dùng `Analysis_Weight` để suy ra tỷ lệ;
  hồ sơ variance design/replicate weights chưa đủ để suy luận thiết kế mẫu.
- NSMO là mẫu survey mortgage có response/weighting; phép thử này không chứng
  minh population application-time cho underwriting, không xác định feature
  availability tại thời điểm quyết định và không đại diện hồ sơ bị từ chối.

## Kết luận cho plan D02

One-shot origination-aligned snapshot endpoint **chưa đủ support cho model study**:
chỉ thấy 65 trạng thái 90+ trong toàn PUF, cùng thiếu chính xác ngày sự kiện,
censor/competing outcomes và thiếu variance method. Dynamic monitoring có support
nhiều hơn khi tái sử dụng quý gốc C, nhưng đó là estimand khác nhau và cũng chưa
được chốt. D02-5 vẫn mở: cần chốt câu hỏi nghiệp vụ, quần thể, competing-risk và
censoring strategy, survey-weight variance, cùng predictor timing/allowlist trước
khi bất kỳ model nào được tạo.

## Reproduction

Đầu vào PUF phải ở vùng private. Script chỉ ghi aggregate receipt và không lưu
nhãn hoặc dòng dữ liệu:

```powershell
python scripts/audit_nsmo_origination_feasibility.py `
  --puf-csv data\private\mortgage\nsmo-2026-05-27\puf\nsmo_v70_1324_puf.csv `
  --output artifacts\private\nsmo-origination-feasibility\receipt.json
```

Nguồn: [FHFA NSMO PUF](https://www.fhfa.gov/data/nsmo), [Official Notice/Terms gate](https://www.fhfa.gov/data/nsmo/puf),
và [SAS formats chính thức](https://www.fhfa.gov/document/d/nsmo/nsmo_v70_formats.sas).

> The opinions and analyses contained herein are solely of the users/authors of any data analyses or papers, and the FHFA cannot and does not attest to nor vouch for the quality, accuracy, or timeliness of the data, or analyses derived from these data after the data has been retrieved from FHFA.gov.
