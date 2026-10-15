# Sovereign default — checkpoint dữ liệu 11/10/2026

Checkpoint mới nhất: app hiện phục vụ4edition2023–2026/42519rows. Xem [SOVEREIGN_ARCHIVE_EDITIONS_VI.md](SOVEREIGN_ARCHIVE_EDITIONS_VI.md) cho profile pinned mới, schema aliases/markers, source conflicts và evidence. Các số2edition/21877rows bên dưới là checkpoint ban đầu2025/2026, được giữ làm lịch sử; không phải scope hiện phục vụ.

## Phạm vi đã hoàn thành

Đã tải bằng HTTP trực tiếp từ Bank of Canada sáu file: hai trang công bố, hai workbook BoC–BoE Database 2025/2026, paper 2026 và methodology. Receipt/hash kiểm tra trước mỗi lần đọc; không mở Excel, không theo external links và không tính lại công thức nguồn.

- Source: `private evidence omitted from public release`.
- Receipt SHA-256: `1f5821cfeaeda3bfbc696fbdfeb1098cf15934b6ef2866f22759e5f10c3956a9`.
- Profile: `private evidence omitted from public release`.
- Profile SHA-256: `f7de62e13544b731e129cb6a6e443dde41694dfbea4f63cbb0d1ff4e419f0453`.

| Edition | Reference years | Entity-year rows | Entities |
|---|---|---:|---:|
| 2025 | 1960–2024 | 10.855 | 167 |
| 2026 | 1960–2025 | 11.022 | 167 |

Mỗi edition có World và 166 entity quốc gia theo nguồn. Đây không phải toàn bộ denominator 215 sovereigns. Mã canonical lấy từ `k` (2025) và `k3` (2026), không lấy `k2` mới để suy diễn ISO codes.

Đã chuẩn hóa 16 chỉ tiêu: tổng debt in default, 11 nhóm creditor, domestic fiscal arrears, hai global counts và tỷ lệ sovereign participation của nguồn. Các trường khác vẫn được giữ trong workbook gốc, chưa chuẩn hóa toàn bộ.

Năm cuối có nhãn `2024p`/`2025p`; workbook định nghĩa `p -- Provisional`. Profile và report giữ nguyên nhãn/cell/provisional status.

## Phân tích đã có ở tầng API

App Country có hai tab World Bank macro và Sovereign defaults. Tab sovereign có bộ lọc edition/entity/year/metric/timeline, bốn summary cards, summary-vs-flat source checks, chart và bảng raw timeline, creditor composition/arrears, peers có search/paging, nguồn/hash/limitations. Global export dùng đúng report của tab đang mở; cả hai bộ lọc được giữ trong URL.

`/api/sovereign-defaults` trả report; `/api/sovereign-defaults-report` xuất JSON private. Sáu filters: `edition`, `entity`, `year`, `metric`, `from`, `to`. Không chấp nhận năm ngoài edition hoặc tham số khác.

Report gồm actual/source cell, timeline giữ null, peers cùng năm, 11 components/residual, arrears riêng, country-panel coverage, World/country-sum residual và hai phép so sánh khác nhau:

1. Thay đổi giữa hai năm trong cùng edition.
2. Revision của cùng năm giữa edition 2025 và 2026.

Ví dụ World năm 2024 là 507.347,14 triệu USD trong edition 2026, tăng 82.335,31 triệu USD so với giá trị cùng năm của edition 2025. Đây là revision nguồn, không phải tăng trưởng default trong một năm.

Production parser giữ numeric text chính xác trong XML. Vì source XLSX có binary serialization, giá trị World 2025 lưu là `437196.79999999999`, không âm thầm thay bằng decimal được làm tròn. Presentation có thể format nhưng export phải giữ raw value và units.

## Vấn đề nguồn cần hiển thị rõ

Edition 2026 có 66 conflicts của chỉ tiêu số sovereigns in default: sheet summary ghi 0, flat Debt sheet có giá trị khác 0. Năm 2025 flat sheet ghi 80, năm 2024 ghi 91. Profile giữ cả hai và cờ mismatch; không sửa workbook gốc hoặc giả định số 0 summary là kết quả thật.

131 đối chiếu World amounts giữa summary và flat sheet đạt precision của flat values. Edition 2025 có 0 conflicts trong 130 amount/count comparisons; edition 2026 có 66 count conflicts trong 132 comparisons.

Năm 2025 country panel có 153/166 entities có TOTAL, 78 giá trị dương; nguồn World ghi 80 sovereigns in default. Tổng các country values khác World khoảng 6 triệu USD. Không ép reconcile bằng cách điền null thành 0 hoặc phân bổ residual cho quốc gia.

Domestic arrears giữ riêng, không cộng vào debt in default. Nominal annual stocks không phải số vỡ nợ mới trong năm, PD, LGD, tổn thất hay institution exposure.

## Kiểm chứng

- Independent openpyxl audit: `private evidence omitted from public release`, PASS.
- Kiểm tra toàn bộ 350.032 metric values, bao gồm 235.520 null và 72.356 zeros; metadata/entity/source rows/year headers và hash sáu nguồn cũng được đối chiếu.
- Openpyxl chuyển số XML thành float; audit chỉ cho phép sai số chuyển đổi binary rất nhỏ. Production giữ raw XML text riêng.
- 13 tests normalization/scope/source mutation/profile mutation/revision/null/zero/provisional/conflict PASS: `private evidence omitted from public release`.
- HTTP tests kiểm tra report, attachment, HEAD, invalid/duplicate filters và loopback origin; cùng normalization và WDI country regression: 56 PASS trong 40,57 giây, `private evidence omitted from public release`.
- UI/API/export/mobile/outage/initial retry/late response: 9 groups PASS, `private evidence omitted from public release`. Export World2024 và participation bằng scoped API; null PLW/zero NAM/positive VNM giữ riêng; cancelled WDI catalog không ghi đè sovereign context. Frozen retail ledger không đổi.
- Existing World Bank regression: 10 groups PASS, `private evidence omitted from public release`, gồm countries/aggregates, missing year, export, URL reload, mobile và điều hướng các domain khác.
- Mobile overflow do metric label dài đã sửa bằng scoped form CSS. Screenshot mobile được xem trực tiếp; không dùng overflow test để chứng nhận mọi màn hoặc mọi workbook.

## Chưa hoàn thành

Giao diện country/sovereign và browser QA/export đã có; sovereign analyst review capture riêng chưa tích hợp. Hai edition không tạo đủ historical publication vintages để làm OOT. Các source count conflicts chưa được publisher giải quyết. Macro stress linkage, PD/LGD calibration và điều kiện sử dụng decision-grade vẫn chưa đạt.

Nguồn này bổ sung evidence cho P4.09; không nâng trạng thái 50 capability, không thay scope D01 R0–R4 và không chứng nhận CreditAtlas hoàn thành 100%.

## Chạy lại

Từ `local machine path omitted`:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/prepare_sovereign_defaults.py
python scripts/audit_sovereign_defaults.py
```

Prepare tạo artifact mới; profile đang phục vụ vẫn được pin theo path/hash đã ghi, không tự đổi sang artifact mới nhất.
