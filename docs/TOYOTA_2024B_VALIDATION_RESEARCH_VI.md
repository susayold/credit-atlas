# Toyota Auto Receivables 2024-B: validation dataset và kết quả audit

Ngày chốt: 15/10/2026. Tất cả raw XML, Parquet và audit có asset key được giữ trong thư mục private trên D:. Nội dung dưới đây chỉ công bố số tổng hợp.

## 1. Câu hỏi và phạm vi kiểm định

Mục tiêu của checkpoint là kiểm tra pipeline đã dùng cho Toyota 2022-B có tái lập được trên một trust khác và trên một giai đoạn servicing mới hay không. Đây là kiểm định chuyển giao giữa hai deal trong cùng Toyota issuer/servicer family. Nó chưa thay thế external validation với sponsor/servicer khác, không chứng minh tính đại diện của pool và không đủ để gọi kết quả là origination PD.

Đã lấy 29 kỳ liên tiếp, 30/04/2024–31/08/2026: mỗi kỳ ghép filing SEC ABS-EE, EX-102 loan-level XML, EX-103 definitions và Form 10-D EX-99.1 Servicer’s Certificate theo report month. Nguồn gốc là SEC EDGAR, CIK 2012786; [ABS-EE filing 2024-04](https://www.sec.gov/Archives/edgar/data/2012786/000095013124002192/0000950131-24-002192-index.htm) và [Form 10-D filing 2024-04](https://www.sec.gov/Archives/edgar/data/2012786/000095013124002190/0000950131-24-002190-index.htm). Receipt private lưu URL, accession, HTTP metadata, byte count và SHA-256 cho từng nguồn.

Tháng 03/2024 không đưa vào vì filing ABS-EE tương ứng là kỳ inception/trùng kỳ và không có cặp 10-D được xác nhận trong acquisition manifest. Bắt đầu từ 04/2024 tạo được panel đồng kỳ 29/29 thay vì ghép các kỳ lệch ngày.

## 2. Đóng gói dữ liệu và kiểm tra cấu trúc

- EX-102 gốc: 5.621.411.994 byte không nén; lưu gzip lossless tổng 192.401.854 byte.
- Panel Parquet: 1.518.106 asset row-months, 70.254 asset keys quan sát, 62 trường và 29 partition tháng.
- 28 cặp tháng liền nhau đã được kiểm tra; mỗi partition hash/size khớp manifest, asset key duy nhất trong tháng, reporting date XML khớp ngày kỳ và mỗi bản ghi được parse theo Auto Loan XSD.
- Giá trị XML gốc và dấu tiền được giữ; `currentDelinquencyStatus` có cột raw và cột số ngày DPD theo XSD. Panel không tự sinh nhãn default, prepayment, recovery hoặc LGD.

Mỗi tháng có số asset rows giảm từ 70.254 (04/2024) xuống 37.163 (08/2026). Đây là coverage của các snapshots trong filing, không phải số khoản giải ngân mới hoặc cohort origination. Asset key vẫn là mã nguồn của trust và không được coi là borrower identity đã resolve.

## 3. Kết quả tie-out với Servicer’s Certificate

| Kiểm tra | Kết quả |
|---|---:|
| Ending pool balance = ABS-EE positive ending balance sum | 29/29 exact |
| Contract count = positive-ending-balance asset count | 29/29 exact |
| Liquidated receivable count = số asset có charge-off dương | 29/29 exact |
| Gross principal of liquidations = tổng charge-off principal | 29/29 exact |
| 4 delinquency buckets × count và balance | 232/232 exact |
| `recoveredAmount` = Aggregate Net Liquidation Proceeds | 1/29 exact |

Trong 28 tháng không khớp, tổng ABS-EE `recoveredAmount` cao hơn certificate net proceeds **$1.764.558,08**; delta dương ở cả 28 tháng. Ví dụ 04/2025: asset sum $834.540,77, certificate $682.834,17, delta +$151.706,60. Không suy diễn nguyên nhân từ dấu/dạng chênh lệch và không tính recovery rate/LGD từ hai chuỗi chưa đối soát.

EX-103 có cùng SHA-256 trong cả 29 kỳ. Definition của Item 3(i)(2) nói Amounts Recovered phát sinh từ receivable đã default trong kỳ và **bao gồm** các khoản ở Item 3(k)(1) Repossession Proceeds. Certificate lại có các dòng Net Liquidation Proceeds Received During the Collection Period, Recoveries on Previously Liquidated Contracts và Aggregate Net Liquidation Proceeds. Vì vậy các nhãn đều có liên quan đến proceeds nhưng không thể mặc định chúng cùng kỳ đo lường, population hoặc net/gross basis. Bước tiếp theo là trích và tái dựng các dòng certificate theo từng collection bucket, sau đó đối chiếu sign, timing và repossession/expense classification ở cấp khoản nếu nguồn cho phép.

## 4. Sự kiện charge-off, mã zero-balance và KPI

- 761 unique asset keys có `chargedoffPrincipalAmount > 0`; mỗi key có đúng một tháng charge-off dương.
- Cả 761 tháng charge-off đều là tháng đầu tiên `zeroBalanceCode=4` xuất hiện cho key đó; tổng charge-off dương theo XML là $19.788.967,40 và khớp certificate từng kỳ.
- Code 4 xuất hiện 11.562 row-months do được lặp lại trong snapshot sau event; không đếm từng row-month thành event mới.
- Có 34.978 asset keys từng được quan sát với ending balance bằng zero. Code 1 xuất hiện 34.182 row-months; code 3 xuất hiện 38 row-months. Chỉ dùng code theo mô tả XSD/EX-103, không gán mọi disappearance là default.
- Certificate-validated pool, contract count, gross liquidation và DPD buckets tạo cơ sở đáng tin hơn cho surveillance KPI tháng. 31+/61+ là tỷ lệ ending-balance từ asset rows và cần ghi rõ mẫu số/định nghĩa; charge-off principal là flow của kỳ, không phải lifetime loss rate.

Recovery field có 1.615 positive và 868 negative row-months. Positive recovery chỉ xuất hiện trên code-4 row-months trong audit; âm có 867 code-4 row-months và một row-month code khác. Đây là mô tả về dữ liệu báo cáo, chưa xác định correction/reversal hoặc economics.

## 5. So với Toyota 2022-B

| Hạng mục | Toyota 2022-B | Toyota 2024-B |
|---|---:|---:|
| Kỳ ABS-EE + certificate ghép đồng kỳ | 51 | 29 |
| Asset row-months | 2.508.991 | 1.518.106 |
| Asset keys | 77.626 | 70.254 |
| Charge-off event assets | 1.122 | 761 |
| Pool/count, liquidation count/principal, 4 DPD bucket checks | 51/51 và 408/408 | 29/29 và 232/232 |
| Recovery exact match | 2/51 | 1/29 |
| Tổng signed delta asset recovery − certificate proceeds | +$2.058.647,06 | +$1.764.558,08 |

Tái lặp cùng cấu trúc recovery discrepancy trên hai deal gợi ý đây là vấn đề mapping/timing/classification đáng ưu tiên điều tra, nhưng hai trust cùng Toyota không tạo hai quan sát issuer độc lập. Không tăng model readiness hay completion percentage chỉ vì thêm deal này.

## 6. Nơi lưu và cách tái tạo

- Acquisition receipt và dữ liệu gốc: `data/private/structured/toyota-2024b-validation-panel-5286fb3cae94/`
- Panel Parquet/manifest: `data/private/derived/toyota-2024b-validation-panel-35e5183b1c22/`
- Longitudinal audit: `artifacts/private/toyota-2024b-absee-panel-audit-148e4a9f9a76/audit.json`
- Certificate tie-out: `artifacts/private/toyota-2024b-certificate-tieout-6223784d25dd/audit.json`
- Browser QA: `artifacts/private/toyota-2024b-validation-ui-qa-a7665b477047/receipt.json`
- Dựng panel: `scripts/build_toyota_2024b_validation_panel.py`
- Audit panel và certificate: `scripts/audit_toyota_2024b_absee_panel.py`, `scripts/audit_toyota_2024b_certificate_tieout.py`
- App card: `apps/web/app.js`; API qualification/pinned audit: `src/credit_atlas/absee_profile.py`

Chạy lại trong PowerShell từ project root:

```powershell
$env:PYTHONPATH='src'
python scripts/build_toyota_2024b_validation_panel.py
python scripts/audit_toyota_2024b_absee_panel.py
python scripts/audit_toyota_2024b_certificate_tieout.py
python -m credit_atlas.cli --root D:\data\Codex\credit-atlas serve --port 8780
```

## 7. Kết luận và việc kế tiếp

Deal 2024-B xác nhận panel builder, event anchoring và KPI surveillance cốt lõi có thể tái lập trên một trust khác của cùng issuer; tie-out từng kỳ cho pool, contract count, charge-off và delinquency đều đạt. Nó chưa xác nhận recovery/LGD, borrower-level independence, representativeness, origination outcomes, calibration hay tác động của legal trigger. Trước model fitting, tiếp tục (1) tái dựng certificate recovery components và EX-103 mappings để giải thích delta, (2) mua/thu thập 10-D + ABS-EE history từ issuer/servicer khác để external validation, (3) kiểm tra feature availability và split/embargo theo filing date cho deal mới, rồi (4) chỉ sau đó đánh giá outcome definition và calibration. Sổ 50 yêu cầu giữ 26/50 = 52%; evidence mới là partial.
