# Managed retail pool — dữ liệu, phân tích và bằng chứng

Checkpoint 11/10/2026. P5 có tab **Managed pool**, API `/api/managed-pool` và JSON riêng tư `/api/managed-pool-report`.

## Nguồn và phạm vi

Nguồn issuer: https://www.worldomni.com/abs/ManagedPool-Retail.xlsx, được discover từ index chính thức trong acquisition `pool-history-source-757ce3631134`. Workbook giữ nguyên; acquisition receipt và từng file được xác minh SHA256/size trước khi đọc. Không lấy thêm borrower records từ workbook aggregate này.

7 cột nguồn: 30/06/2026, 30/06/2025 và cuối năm 2025/2024/2023/2022/2021. Có 30 chỉ tiêu mỗi cột, tổng 210 giá trị nguồn. Snapshot và dòng tiền giữ riêng; không cộng các snapshot thành tổng danh mục.

## Phân tích trong app

- Dư nợ cuối kỳ và số hợp đồng; quá hạn 31–60, 61–90, 91–120, 121+ ngày; tổng quá hạn theo count và balance; tỷ lệ nguồn công bố cho từng bucket/tổng.
- Average portfolio/contracts, repossessions, gross charge-offs, signed recoveries, net charge-off losses và reported loss/repossession rates.
- Tỷ lệ tính lại net loss/average portfolio và repossessions/average contracts; giữ nguyên input cells, không annualize.
- 15 đối soát mỗi kỳ: hai duplicate stock disclosures, hai bucket sums, net-loss bridge và mười tỷ lệ quá hạn tính lại. Tolerance: count/duplicate = 0; monetary bridge = 0.000001 nghìn USD; rounded fractions = 0.000050000000001.
- Bảng snapshot/dòng tiền, chi tiết nguồn exact/cell/unit/type, kết quả đối soát, caveats và JSON export. Lỗi nguồn xóa dữ liệu/export cũ; retry/reload phục hồi.

## Quy tắc quan trọng

1. A2 ghi **Dollar Amount in Thousands**: giữ đơn vị nghìn USD, không ngầm đổi thành USD.
2. Recoveries nguồn âm: **net losses = gross charge-offs + signed recoveries**. Không trừ recovery âm lần nữa.
3. C/D chỉ ghi **At June 30**. Không đủ nguồn để xác nhận flow start/duration hay annualization convention. E–I ghi **For the 12 months ended**; thời lượng 12 tháng được giữ theo header này.
4. Reported net-loss/repossession rates giữ riêng với raw period fractions. Sự khác biệt giữa chúng không tự chứng minh công thức annualization.
5. Missing giữ null/UNAVAILABLE; zero thực giữ zero. Không ép source rounding residual về zero.
6. Đối soát thành công không biến aggregate net charge-off loss thành LGD, PD, forecast hay loan-level model dataset. Không có native Excel recalculation hoặc historical-vintage qualification.

## Kiểm tra đã lưu

- `private evidence omitted from public release`: 21 tests PASS (managed + static pool), gồm missing/sign/date/ratio/scope và inconsistent-total handling.
- `private evidence omitted from public release`: openpyxl đọc workbook độc lập với projection XML; 210 giá trị, 105 reconciliation và 14 derived ratios PASS.
- `private evidence omitted from public release`: 4 nhóm browser PASS, API/JSON parity, exact source/unit/sign, mobile/reload, source outage/recovery và frozen holdout ledger unchanged. Desktop/mobile screenshots đã xem.
- Lần QA trước `managed-pool-qa-3cad4448bae9` bị dừng vì route mô phỏng outage sai pattern (API không có query string); không dùng làm evidence nghiệm thu. Source audit ban đầu sửa xử lý openpyxl EmptyCell trước khi có receipt PASS.

## Liên hệ plan

Đây là phần bổ sung cho P5.02/P5.10. Hai capability vẫn **Một phần**. Còn thiếu collateral loan-level, forecasts, historical availability, full legal/valuation qualification. Sáu sheet static-pool deal cũ vẫn chưa normalized. Số mục toàn plan giữ 21 Đã có / 9 Có điều kiện / 12 Một phần / 8 Cần dữ liệu; không tăng phần trăm chỉ vì thêm một tab.
