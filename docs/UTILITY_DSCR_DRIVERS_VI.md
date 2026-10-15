# EBMUD — phân tích biến động DSCR

## Mục đích và scope

Phân rã thay đổi DSCR giữa hai năm lịch liền nhau trong cùng system/edition, với scope parity hoặc total debt service. Số liệu từ Continuing Disclosure 2024/2025 đã source-audit; không dùng ACFR rounded millions để tính các tác động USD. Không ghép previous edition làm baseline; revision comparison là tác vụ riêng.

## Công thức chính xác

Ký hiệu: N = net revenues; R = revenues after stabilization; M = O&M; E = N − R + M là residual nguồn; D = debt service theo scope. Chỉ tính khi D0 và D1 dương.

- Revenue effect = (R1 − R0) / D0.
- Maintenance effect = −(M1 − M0) / D0.
- Source residual effect = (E1 − E0) / D0.
- Debt-service effect = N1 / D1 − N1 / D0.
- Tổng bằng N1 / D1 − N0 / D0, đối soát bằng Fraction, residual chính xác 0/1.

Thứ tự là numerator trước, denominator sau. Counterfactual N1/D0 được hiển thị. Đây là phân rã kế toán có phụ thuộc thứ tự, không phải causal attribution hoặc chứng minh hiệu quả một quyết định. Chi phí tăng có effect âm; phần source residual không bị bỏ qua dù chỉ 1 USD.

Exact rational numerator/denominator và Decimal50 có trong API/JSON/details. UI làm tròn 6dp; tổng số hiển thị có thể lệch ở mức làm tròn. `year_change_decimal50` dùng exact rational delta để không trừ hai tỷ số đã làm tròn ở bước trung gian. Đơn vị tác động là DSCR times, không phải percentage points.

## Kết quả FY2025 vs FY2024

| System/basis | Revenue effect | O&M effect | Debt-service effect | DSCR change |
|---|---:|---:|---:|---:|
| Water/total |+0.471985|−0.131754|−0.057841|+0.282390|
| Water/parity |+0.496271|−0.138534|−0.075431|+0.282305|
| Wastewater/total |+0.462169|−0.250424|−0.084150|+0.127596|
| Wastewater/parity |+0.462169|−0.250424|−0.084150|+0.127596|

Water source residual tăng 1 USD, tạo một effect dương nhỏ khoảng 4.88e−9x với scope total; row vẫn có input 1 USD và exact fraction dù 6dp display là 0.000000. Wastewater net-revenue residual change bằng 0; maintenance bridge của nguồn có thể có residual riêng và không tự bị sửa.

Không suy từ phân rã trên rằng rate increase, demand, accounting revisions hoặc financing transactions là nguyên nhân đã xác minh. Muốn giải thích kinh tế cần thêm volumes/rates, source notes và transaction evidence phù hợp.

## Coverage, kiểm tra và giao diện

40 year/system/edition/basis scopes: 32 supported adjacent-year bridges và 8 first-year scopes không có prior calendar year. Cases thiếu baseline hiển thị unavailable, không có effect rows. Guard từ chối cross-edition/system/nonadjacent baseline hoặc denominator không dương.

API/private JSON thêm `dscr_driver`, với baseline/current USD inputs, source file/page, exact effects, counterfactual, sum và residual. P3 → Utility DSCR có driver bridge và biểu đồ five-year reported parity/total DSCR; bảng nguồn giữ riêng ratios reported và recomputed.

Independent audit dùng closed-form integer/Fraction identities khác dạng denominator effect của production. Script `scripts/audit_utility_drivers.py` kiểm tra toàn bộ 40 scopes và unchanged holdout ledger. Tests bao gồm source residual, baseline missing, denominator/cross-edition guards, source/profile tampering và HTTP boundary. Đây là numerical verification; không nâng legal headroom/compliance hoặc PD/LGD qualification.

Receipt cuối: `private evidence omitted from public release` PASS32supported/8missing-prior; `utility-driver-http-tests-20261011-final.xml` PASS46; browser `utility-debt-qa-23618d05faf4/receipt.json` PASS5groups,0browser errors,ledger unchanged. Driver effects/chart,exact API/export parity,baseline unavailable,filters/year bounds/URL reload,mobile vàoutage recovery được kiểm tra. Desktop/mobile driver screenshots của lượt trước đã xem trực tiếp; sửa delta sau đó chỉ thống nhất exact backend precision,6dp display giữ nguyên.

Lượt test đầu phát hiện decoding Fraction từ hai strings thay vì integers; đã sửa conversion, giữ failed XML và chạy lại. Partial evidence ghi tại P3.03/P3.08, không nâng trạng thái 50 capability.
