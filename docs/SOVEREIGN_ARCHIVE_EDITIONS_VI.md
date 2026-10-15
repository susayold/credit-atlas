# Sovereign default — mở rộng edition 2023–2026

Ngày checkpoint: 11/10/2026. P4.09 thêm nguồn và phương pháp đối chiếu revisions; không nâng completion status của 50 capability.

## Nguồn mới

Đã tải sáu file qua HTTP trực tiếp từ Bank of Canada: hai trang công bố, hai XLSX và hai paper PDF cho edition 2023/2024. Mỗi XLSX/PDF phải có link trong trang edition trước khi receipt acquisition được chốt. HTTPS origin, size bounds, CRC, PDF header và source hashes đã được kiểm tra. Không theo external links hoặc tính lại workbook.

- Folder: `private evidence omitted from public release`.
- Receipt SHA-256: `21ba37b2a39d743dff6b835042044bff572f5d0eb14794254ab9eaabc87166e6`.
- Trang 2023: https://www.bankofcanada.ca/2023/07/staff-analytical-note-2023-10/
- Trang 2024: https://www.bankofcanada.ca/2024/07/staff-analytical-note-2024-19/

Raw XLSX giữ tên gốc, gồm `BoC-BoE-Database-2023-08-29.xlsx`. HTTP Last-Modified/ETag/Content-Type và retrieval timestamp được lưu. Những headers này không chứng minh các bytes hiện tải đã tồn tại tại ngày xuất bản đầu tiên.

## Dataset hiện phục vụ

| Edition | Reference years | Entity-year rows | Country entities (không World) | Update text của workbook |
|---|---|---:|---:|---|
| 2023 | 1960–2022 | 9.954 | 157 | Last Update: 29 August 2023 |
| 2024 | 1960–2023 | 10.688 | 166 | Last Update: 17 MAY 2024 |
| 2025 | 1960–2024 | 10.855 | 166 | Last Update: July 2025 |
| 2026 | 1960–2025 | 11.022 | 166 | Last Update: August 6, 2026 |

Tổng 42.519 rows ×16 selected metrics =680.304 value positions. Đây là 16 chỉ tiêu đã chọn, không phải toàn bộ trường raw workbook.

Profile mới: `private evidence omitted from public release`.
SHA-256: `578e9aaad6b34e157829ca3f4007fc1210b9b2e627c677c2bec9f30d253e7d83`.

Source acquisition ban đầu 2025/2026 và profile cũ được giữ nguyên. Report xác minh cả hai receipts và cả12 source files, rồi đọc profile pinned. Không tự chọn profile mới nhất.

## Schema drift và source markers

1. Edition 2023 dùng header row63; các edition khác row65. Canonical key là `k`, trừ edition2026 dùng `k3`.
2. Edition 2023 không có cột IADB trong flat sheet. Cả9.954 metric positions này giữ schema absence/null, không lấy summary World IADB để điền country observations. Vì thiếu component, composition residual unavailable.
3. Edition 2024 có flat TOTAL header `DEBT_TOTAL_2023` mặc dù các fields khác mang suffix2024. Adapter dùng explicit alias riêng cho nguồn/hash này. Toàn bộ64World reference years đối chiếu với summary2024 amounts đạt declared flat precision. Report/UI/export hiển thị original header và cảnh báo; không đổi workbook gốc.
4. Edition 2024 có1.341nonnumeric cells trong selected metrics: dấu sao ba/bốn/năm ký tự và17whitespace cells. Dòng chú thích nguồn định nghĩa `**** -- values for debt in default unavailable`. Bốn dấu sao mang status `source_unavailable`; ba/năm dấu sao và whitespace mang status `uninterpreted_source_marker`. Tất cả giữ numeric null và raw text/cell. Không giả định ý nghĩa của các biến thể chưa có chú thích.
5. Không ép blank trong legacy source thành zero; không dùng data mới để lấp khoảng trống của edition cũ.

Country universes khác nhau giữa editions. UI dùng entity options riêng cho edition, không giữ mã không tồn tại trong source mới chọn. Nếu đổi edition làm entity cũ không còn trong options, select hiển thị World trước khi người dùng áp dụng. API URL trực tiếp với entity không có vẫn bị từ chối. Không join mã đổi tên bằng fuzzy matching.

## Phân tích revision

Revision chỉ so cùng entity/reference year/metric với edition liền trước có trong archive. Nếu năm hoặc entity không có ở edition trước, report trả unavailable. Không so năm gần nhất hoặc edition không liền trước.

Ví dụ World reference2022:

- Edition2023 raw: `554236.54933913087` triệu USD.
- Edition2024 raw: `530095.93000000005` triệu USD.
- Revision2024−2023: `-24140.61933913082` triệu USD.

Đây là thay đổi số liệu nguồn cho cùng năm2022, không phải dòng default mới hoặc thay đổi2022→2023. Year change trong cùng edition được hiển thị ở card khác.

Edition2023 latest header là2022 không có suffixp; UI nói `Source annual value`, không tự gọi là số liệu final. Edition2024/2025/2026 latest headers cóp; giữ provisional status của source.

## Source conflicts

| Edition | World amount/count comparisons | Conflicts |
|---|---:|---:|
| 2023 | 126 | 2 |
| 2024 | 128 | 0 |
| 2025 | 130 | 0 |
| 2026 | 132 | 66 |

Tổng516comparisons/68conflicts. Tất cả258World amount comparisons đạt flat precision;68conflicts thuộc count. Edition2023 reference2021 summary count97 nhưng flat sheet99; cả hai được giữ. Không sửa nguồn hoặc tuyên bố publisher đã giải quyết.

World sovereign counts và positive country-stock counts khác phạm vi. Country sums/World residual được báo riêng; không phân bổ residual vào quốc gia hoặc coi số positive country records là default probability.

## Kiểm chứng

- Independent openpyxl audit: `private evidence omitted from public release`, PASS.
- Kiểm tra680.304positions, gồm515.678missing,72.509zeros,1.341source markers và9.954schema-absent positions. Kiểm tra entity metadata, source rows, reference headers và12source hashes. Production parser giữ raw XML text; audit cho phép riêng sai số chuyển đổi sang float của openpyxl.
- Backend/HTTP/WDI regression:59PASS, `private evidence omitted from public release`.
- Archive browser:5groupsPASS, `private evidence omitted from public release`. Test alias/revision/export, starred null, schema absence/date, entity options, count conflict, URL reload và mobile. Desktop source-check/mobile controls screenshots đã xem trực tiếp.
- Current2025/2026/WDI-tab regression:9groupsPASS, `private evidence omitted from public release`, gồm scoped export, null/zero, peer paging, mobile, outage/retry và delayed WDI catalog response.
- Retail frozen holdout ledger không đổi.

Lần test trước có một assertion sai rằng PLW không có ở2023. Source inventory chứng minh PLW có; test được sửa dùng CHN, mã thực sự không có ởedition2023. Source/parser không bị sửa để làm test này pass. Kết quả thất bại cũ được giữ trong `sovereign-archive-country-tests-20261011.xml`.

## Điều kiện còn mở

Có thêm historical editions, chưa có complete publication-vintage panel. Update text khác publication date; URL chứa năm không chứng minh release-day bytes. `historical_publication_vintages_complete`, `pd_lgd_calibrated` và `macro_stress_linkage_qualified` vẫn false.

Nguồn đo nominal annual stocks in default, không đủ để tự tạo default-onset event labels, PD, LGD hoặc causal macro response. Cần thêm publication evidence, definition/coverage protocol, appropriate dated macro inputs và validation trước qualified stress linkage. Sovereign analyst review capture cũng còn mở.

## Chạy lại

```powershell
# Từ local machine path omitted
.venv\Scripts\python.exe -X utf8 scripts/prepare_sovereign_defaults.py
python scripts/audit_sovereign_defaults.py
.venv\Scripts\python.exe -X utf8 scripts/browser_sovereign_archive_qa.py
```

Prepare tạo profile mới; serving path/hash không tự đổi. Browser QA cần local server8770.
