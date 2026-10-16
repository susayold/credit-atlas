# Nissan 2024-B — event, DPD và recovery exception ledger

Cập nhật: **17/10/2026**. Mục tiêu N08 là tái tạo các ngoại lệ theo thời gian và thử candidate rule trên toàn panel, không tìm quy tắc để làm đẹp một tháng riêng lẻ.

## Kết luận điều hành

Nissan 2024-B có 23 kỳ liên tục từ 31/10/2024 đến 31/08/2026, gồm 1.154.259 asset-month rows và 63.688 asset keys trong panel đã audit. Hai trust Toyota trước đó không đại diện cho issuer khác; Nissan dùng field definitions riêng trong EX-103 nên không được bê nguyên mapping Toyota sang.

Các đối soát tổng thể tái lập từ audit đã pin như sau:

| Chỉ tiêu | Đạt chính xác |
|---|---:|
| Ending pool balance ↔ certificate pool balance | 23/23 |
| Asset dương ending balance ↔ certificate contract count | 23/23 |
| Positive charge-off rows ↔ certificate event count | 20/23 |
| ABS-EE charge-off amount ↔ certificate gross defaulted principal | 21/23 |
| First `zeroBalanceCode=4` count ↔ certificate event count | 21/23 |
| First-code-4 charge-off amount ↔ certificate amount | 20/23 |
| DPD bucket count + balance, quy tắc literal | 178/184 |
| ABS-EE recoveredAmount ↔ certificate recoveries | 17/23 |

Đây là source/parser reconciliation, chưa phải external model validation, event-label sign-off hay LGD qualification.

## Ngoại lệ charge-off tháng 07/2025

Trong ABS-EE có 36 asset rows với charge-off dương, tổng **USD 655,185.56**. Trong đó có 33 first-code-4 rows cộng **USD 577,420.34** và ba rows lặp code 4/charge-off từ tháng trước cộng **USD 77,765.22**. Certificate ghi **1 defaulted receivable** và principal **−USD 59,000.49**. Hai amount được giữ riêng với raw sign; chưa có transaction-level mapping đủ để coi chúng là cùng một measure rồi quy phần dư cho reversal, correction hay event timing. [SEC 10-D EX-99.1 của kỳ 31/07/2025](https://www.sec.gov/Archives/edgar/data/2035264/000119312525187356/d930039dex991.htm) · [ABS-EE filing của cùng report date](https://www.sec.gov/Archives/edgar/data/2035264/000095013125003344/0000950131-25-003344-index.html).

Certificate recovery là **USD 257,636.52**, khớp ABS-EE recoveredAmount. Certificate monthly net loss **−USD 316,637.01** cũng bảo toàn đúng quan hệ signed: `−59,000.49 − 257,636.52 = −316,637.01`; current net-loss ratio công bố là **−0.39%**. Đây là phép kiểm tra nội bộ certificate, không giải thích khoản charge-off dương USD 655,185.56 ở ABS-EE.

> Không dùng một event rule duy nhất để “giải” tháng 07. Tháng 08/2025, 54 positive charge-off rows và USD 860,007.75 khớp certificate count/amount, trong khi chỉ 24 là first-code-4 keys và 30 rows lặp code 4 cộng USD 522,608.93. Ngược lại, tháng 01/2025 có 31 first-code-4 keys nhưng một key có amount bằng zero; tháng 02 có 37 keys, hai key amount bằng zero và amount positive còn lại cao hơn certificate USD 44.66. Positive-amount count, first-code-4 count và event amount đo các trạng thái khác nhau; chưa có anchor nào khớp toàn bộ lịch sử.

## Ngoại lệ DPD tháng 06/2025

SEC certificate ghi collection period từ **01/06/2025 đến 30/06/2025**; bảng DPD là các bucket 31–60, 61–90, 91–120 và trên 120 ngày. [June 2025 Servicer’s Certificate](https://www.sec.gov/Archives/edgar/data/2035264/000119312525166251/d44534dex991.htm) ghi rõ ngày kỳ ở đầu tài liệu và giá trị/count bucket ở phần cuối.

So với certificate, các giá trị literal theo asset rows có residual:

| Bucket | Count delta (asset − certificate) | Balance delta |
|---|---:|---:|
| 31–60 ngày | +2 | +USD 50,837.98 |
| 61–90 ngày | −1 | −USD 28,108.10 |
| 91–120 ngày | −1 | −USD 22,729.88 |
| Trên 120 ngày | 0 | USD 0.00 |
| **Tổng** | **0** | **USD 0.00** |

Hai source rows ở 60 DPD cộng USD 50,837.98; một row ở 90 DPD có balance USD 22,729.88. Dời mỗi ranh giới candidate sớm một ngày làm tháng 06 khớp **8/8** bucket checks, so với **2/8** theo literal. Nhưng khi chạy cùng candidate trên toàn 23 kỳ, exact checks giảm từ **178/184** xuống **86/184**. Vì thế candidate này chỉ là diagnostic giải thích cấu trúc residual tháng 06; không áp dụng làm rule hệ thống nếu chưa có xác nhận định nghĩa/cutoff từ servicer.

## Sáu recovery amount exceptions

Recovery khớp 17/23 kỳ; sáu residual trong 12/2024–05/2025 đều dương:

| Report date | ABS-EE recoveredAmount | Certificate recoveries | Delta |
|---|---:|---:|---:|
| 31/12/2024 | USD 25,270.57 | USD 25,244.84 | +USD 25.73 |
| 31/01/2025 | USD 254,690.54 | USD 254,542.68 | +USD 147.86 |
| 28/02/2025 | USD 164,618.80 | USD 164,393.82 | +USD 224.98 |
| 31/03/2025 | USD 582,297.29 | USD 576,703.40 | +USD 5,593.89 |
| 30/04/2025 | USD 370,616.12 | USD 369,451.11 | +USD 1,165.01 |
| 31/05/2025 | USD 354,135.17 | USD 352,433.41 | +USD 1,701.76 |
| **Tổng** |  |  | **+USD 8,859.23** |

Các positive recovery row-months trong sáu kỳ thuộc asset keys có code 4 ở một kỳ trước; không có recovery âm và không có row-month nào vừa recovery dương vừa charge-off dương. Mẫu này hỗ trợ giả thuyết **timing/ever-charged-off** theo định nghĩa Nissan, nhưng không giải thích amount gap hay đủ để đo recovery rate/LGD. EX-103 định nghĩa `recoveredAmount` cho receivable từng được charge-off; field `repossessedProceedsAmount` chỉ nhận sale proceeds nếu xe được bán ngay trong kỳ repossession, còn bán ở kỳ sau thì tiền đi vào recovered amount. Giữ riêng hai field để tránh double count; định nghĩa đầy đủ có trong filing [Nissan ABS-EE và EX-103](https://www.sec.gov/Archives/edgar/data/1129068/000119312526231956/0001193125-26-231956-index.htm).

## Kiểm tra amendment gần nhất

Ngày 17/10/2026, truy vấn [SEC submissions API cho CIK 0002035264](https://data.sec.gov/submissions/CIK0002035264.json) trả 57 submission gần nhất, filing date mới nhất 25/09/2026. API có đúng cặp filing của report date 31/07/2025: ABS-EE accession `0000950131-25-003344` nộp 20/08/2025 và 10-D accession `0001193125-25-187356` nộp 25/08/2025; không thấy `ABS-EE/A` hoặc `10-D/A` có report date 31/07/2025 trong response hiện thời. SEC mô tả submissions endpoint là nguồn lịch filing được cập nhật khi filings được công bố; điều này chỉ cho biết **không có amendment filing trong census vừa kiểm tra**, không loại trừ adjustment trong certificate hoặc servicing records chưa nộp amendment. [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

## Phương pháp và cách sử dụng ledger

- Giữ source grain theo deal × report date. Mỗi dòng có collection-period start/end, ngày lịch, hai accession và SEC links.
- Giữ nguyên amount của ABS-EE và certificate theo nghĩa/dấu gốc. Số đếm, principal amount, recovery amount và DPD balances là các phép kiểm tra riêng; không gộp thành một default event mới.
- Tính exact bằng Decimal khi tạo CSV. `asset_minus_certificate_recovery_usd = ABS-EE recoveredAmount − certificate Recoveries of Defaulted Receivables`. DPD delta là asset aggregate trừ certificate theo từng bucket. Không nội suy/missing-to-zero, không forecast, không phát hành asset IDs.
- Excel Summary tính lại số kỳ, tie counts và residual trên sheet Period ledger. Các kết quả “shifted DPD” được ghi rõ diagnostic-only; người dùng không nên thay literal fields bằng candidate boundary.

**Kết luận risk:** hiện có bằng chứng tốt cho pool balance, contract count và nội bộ certificate KPI arithmetic. July charge-off event mapping, sáu recovery amount gaps và servicer DPD boundary vẫn chưa được giải thích đầy đủ. Không fit PD/event model trên các mismatch này; không gọi USD 8,859.23 hoặc các charge-off residual là LGD, net loss hay fraud.

## Tệp tái lập

- [CSV exception ledger 23 kỳ](data/nissan-2024b-exception-ledger-23-periods.csv)
- [Receipt, hashes và summary](data/nissan-2024b-exception-ledger-23-periods-receipt.json)
- [Workbook Excel](../apps/excel/templates/CreditAtlas-Nissan-Exception-Ledger.xlsx)
- [Builder ledger aggregate](../scripts/build_nissan_exception_ledger.py)
- [Nghiên cứu nguồn Nissan gốc](NISSAN_2024B_EXTERNAL_VALIDATION_VI.md)

Public release là monthly aggregate + accession links, không có asset/contract identifiers. N08 đã tái lập các điều kiện trong plan; root-cause/servicer confirmation còn mở và thuộc bước điều tra tiếp theo.
