# Toyota recovery-component exception ledger — 2022-B và 2024-B

Cập nhật: **17/10/2026**. Đây là nghiên cứu đối soát component tiền thu hồi, không phải kết luận về nguyên nhân sai lệch hay ước lượng LGD.

## Kết quả chính

Tôi ghép tổng `recoveredAmount` theo tháng trong ABS-EE EX-102 với `Aggregate Net Liquidation Proceeds` trên Servicer’s Certificate SEC EX-99.1 cho Toyota 2022-B (51 kỳ) và 2024-B (29 kỳ). Kết quả có 80 kỳ. Ba kỳ khớp chính xác; 77 kỳ còn chênh lệch chưa được tài liệu đã kiểm tra giải thích. Tổng `ABS-EE − certificate` là **+USD 3,823,205.14**.

| Deal | Kỳ | Khớp | Chưa giải thích | ABS-EE recoveredAmount | Certificate aggregate proceeds | Residual |
|---|---:|---:|---:|---:|---:|---:|
| Toyota 2022-B | 51 | 2 | 49 | USD 16,414,508.06 | USD 14,355,861.00 | +USD 2,058,647.06 |
| Toyota 2024-B | 29 | 1 | 28 | USD 13,517,164.16 | USD 11,752,606.08 | +USD 1,764,558.08 |
| **Tổng** | **80** | **3** | **77** | **USD 29,931,672.22** | **USD 26,108,467.08** | **+USD 3,823,205.14** |

Mỗi kỳ có hai phép kiểm tra riêng trên certificate. Công thức component `Aggregate Net Liquidation Proceeds = −(Net Liquidation Proceeds Received During the Collection Period + Recoveries on Previously Liquidated Contracts)` khớp **80/80**. Công thức `Net Credit Losses = Gross Principal of Liquidated Receivables + signed Principal of Repurchased Contracts, previously charged-off + hai dòng proceeds có dấu` cũng khớp **80/80**. Hai phép kiểm tra này chỉ xác nhận phép cộng các dòng certificate; chúng không giải thích chênh lệch giữa hai nguồn.

Ví dụ tháng 04/2025 của 2024-B: ABS-EE `recoveredAmount` là USD 834,540.77; certificate aggregate proceeds là USD 682,834.17; residual là +USD 151,706.60. Certificate tạo aggregate từ hai dòng signed −USD 150,252.40 và −USD 532,581.77. [SEC filing 2022-B](https://www.sec.gov/Archives/edgar/data/1914281/000095013122002459/d346874dex991.htm) minh họa cấu trúc gốc: collection period, hai dòng liquidation/recovery có dấu và aggregate proceeds. Tài liệu này ghi collection period đầu là **1/3/2022–30/4/2022, 61 ngày lịch**. Kỳ đầu 2024-B cũng là 1/3/2024–30/4/2024, 61 ngày theo certificate đã thu thập. Vì vậy, chỉ dùng nhãn report month sẽ làm mất thông tin về độ dài cửa sổ thu thập. [SEC filing 2024-B tháng 04/2025](https://www.sec.gov/Archives/edgar/data/2012786/000095013125002267/d923232dex991.htm) là ví dụ kỳ có residual lớn nêu trên.

## Phương pháp và ý nghĩa của các biến

1. **ABS-EE side:** cộng giá trị `recoveredAmount` trong từng ABS-EE EX-102 của kỳ, từ panel đã được audit và gắn receipt/hash. EX-103 mô tả `recoveredAmount` là số thu hồi trong kỳ trên receivable đã default và bao gồm proceeds từ repossession. Đây là tổng theo asset-level submission; không giả định nó tự động trùng một dòng đơn lẻ trong certificate.
2. **Certificate side:** giữ nguyên dấu của hai dòng tiền. `Net Liquidation Proceeds Received During the Collection Period` và `Recoveries on Previously Liquidated Contracts` thường được trình bày âm trong bảng liquidation. Certificate đưa aggregate proceeds dương vào bảng collections. Kiểm tra quan hệ dấu trên từng kỳ thay vì đổi dấu từng hàng tùy kết quả mong muốn.
3. **Residual:** `ABS-EE recoveredAmount sum − certificate aggregate proceeds`. Residual bằng 0 được ghi `TIED`; residual khác 0 được giữ nguyên theo kỳ và ghi `UNRESOLVED`.
4. **Độ chính xác:** dùng Decimal từ dữ liệu nguồn để so sánh exact đến cent; không nội suy, không dùng số dự phóng, không thay missing bằng zero để tạo kết quả.

## Những gì chưa chứng minh được

77 residual có cùng dấu dương trong bảng này, nhưng dấu giống nhau không chứng minh nguyên nhân chung. Đối chiếu hiện tại chưa xác định được nguyên nhân là định nghĩa field, timing/cutoff, population, correction, reclassification hay phạm vi certificate. Một phần khác biệt có thể cần truy nguyên qua lịch collection, servicing data dictionary, amendment, báo cáo supplement và ánh xạ từng ABS-EE asset sang contract/certificate. Không gán chênh lệch cho repossession lần nữa: EX-103 cho biết proceeds repossession đã nằm trong `recoveredAmount`, nên cộng thêm một field cùng bản chất có rủi ro double count.

Kết quả này **không** phải recovery rate, LGD, PD, net credit loss, forecast, hay estimate về fraud/data error. Không đưa residual vào tổn thất, không bù chỉnh để đạt zero và không kết luận nguyên nhân khi chưa có evidence. Hai trust cùng issuer/servicer family nên không đại diện cho hai issuer độc lập.

## Tiếp tục điều tra

- Khóa mapping EX-102/EX-103 theo từng phiên bản filing: accession, reporting start/end, event date, `recoveredAmount`, repossession proceeds và các field tiền thu khác; kiểm tra amendment/revisions trước khi cộng.
- Tái tạo cùng bridge trên một trust khác chỉ sau khi có đầy đủ data dictionary và certificate field definitions; dùng như kiểm tra khả năng lặp lại parser/source logic, không xem là external model validation.
- Nếu không thể truy đến contract-level mapping bằng nguồn công khai, giữ 77 kỳ ở trạng thái unresolved, ghi rõ missing evidence cần chủ dữ liệu/servicer cung cấp; chỉ sau khi khớp định nghĩa mới xem xét LGD/cashflow analysis.

## Tệp tái lập

- [CSV ledger](data/toyota-recovery-components-80-periods.csv): 80 kỳ, aggregate-only.
- [Receipt và summary](data/toyota-recovery-components-80-periods-receipt.json): method, totals, audit/acquisition SHA-256.
- [Excel workbook](../apps/excel/templates/CreditAtlas-Toyota-Recovery-Exception-Ledger.xlsx): sheet tổng quan, filterable period ledger và definitions/source references.
- [Builder kiểm tra và tái tạo ledger](../scripts/build_toyota_recovery_components_ledger.py).
- [Nghiên cứu nguồn Toyota 2024-B](TOYOTA_2024B_VALIDATION_RESEARCH_VI.md).

Public output chỉ gồm aggregate theo kỳ và filing references; không phát hành asset/contract identifiers hoặc loan-level rows. Tài liệu công khai từ Toyota 2024-B cũng có thể đối chiếu trên [SEC filing tháng 12/2025](https://www.sec.gov/Archives/edgar/data/2012786/000119312526026626/d34067dex991.htm) và [SEC filing năm 2026](https://www.sec.gov/Archives/edgar/data/2012786/000119312526240854/d68275dex991.htm).
