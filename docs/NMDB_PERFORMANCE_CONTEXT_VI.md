# FHFA NMDB quarterly performance — nguồn benchmark bổ sung

Cập nhật 2026-10-16. Nguồn này bổ sung bối cảnh thị trường cho D02; nó là một
benchmark độc lập, không phải phần mở rộng của NSMO Public Use File.

## Nguồn và phạm vi đã tải

- Trang FHFA NMDB Aggregate Statistics: <https://www.fhfa.gov/data/nmdb>.
- File chính thức: `nmdb-mortgage-performance-statistics-national-census-areas-quarterly.zip`,
  phát hành 2026-09-30, dữ liệu từ 2002Q1 đến 2026Q2.
- Data dictionary và technical notes: bản ngày 2026-06-26, Appendix D và phần
  Technical Notes về mortgage performance.
- ZIP đã tải qua HTTPS, không cần tài khoản: 128,638 bytes;
  SHA-256 `2083c4e1b5273fd2f471d2e58057b17b82b86ef3ac7ed13c58925b4453ec4e89`.
- Thành viên CSV trong ZIP:
  `nmdb-mortgage-performance-statistics-national-census-areas-quarterly.csv`;
  SHA-256 `f50bcea47221135d4fc0ef75b3c5f4265ab0c97fb46a5d65b9a8cbc2bfa605bd`.
- Bản dữ liệu đã tuyển chọn:
  `docs/data/nmdb-performance-national-quarterly-2026q2.csv`; 1,568 dòng,
  chỉ giữ National / USA; 4 market × 4 series × 98 quý, không có ô bị suppress.
- Receipt và hash của bản tuyển chọn nằm tại
  `docs/data/nmdb-performance-national-quarterly-2026q2-receipt.json`.
  ZIP gốc được giữ ngoài public repo tại `D:\data\Codex\credit-atlas\data\public\mortgage\nmdb-2026q2`.

## Những chỉ số được công bố

| SERIESID | Ý nghĩa của FHFA | Mẫu số |
|---|---|---|
| `P3089DL` | Mortgage trễ ít nhất 30 hoặc 60 ngày | Active loans cuối quý |
| `P90DL` | Mortgage trễ ít nhất 90, 120, 150 hoặc 180 ngày | Active loans cuối quý |
| `PFORECL` | Đang foreclosure, bankruptcy hoặc deed-in-lieu | Active loans cuối quý |
| `PFORB` | Đang được ghi nhận trong forbearance | Active loans cuối quý; chuỗi bắt đầu 2019Q4 |

Các rate trong CSV và Excel được giữ theo đơn vị phần trăm do FHFA xuất bản;
ví dụ `1.7` nghĩa là 1.7%, không phải 0.017. Blank của PFORB trước 2019Q4 là
không có chuỗi, không được đổi thành 0.

Bốn market giữ theo phân loại của FHFA: All Mortgages; Enterprise Acquisitions;
Government / Non-Conventional; Other Conventional Market. Đây là các chuỗi
riêng do publisher định nghĩa. Không cộng All Mortgages với các thành phần.

## Kết quả tích hợp

- `/api/nmdb-performance` đọc aggregate CSV đã tuyển chọn, đối chiếu SHA-256 với
  receipt, kiểm tra national scope, coverage, trùng khóa, suppression flag và
  miền giá trị phần trăm trước khi trả dữ liệu.
- `/nsmo` có panel riêng cho NMDB, cho chọn performance series và market, đọc
  latest quarter theo bốn market, xem chart chuỗi 2002Q1–2026Q2 và bảng quý.
- `/downloads/nmdb-performance.xlsx` cung cấp workbook bốn sheet: hướng dẫn,
  Latest KPIs, full Quarterly data và Definitions. Sheet dữ liệu có Excel Table,
  filter và header freeze; tỷ lệ được định dạng để không nhầm phần trăm với fraction.

Quý mới nhất trong snapshot (2026Q2) báo `All Mortgages`: P3089DL 1.7%,
P90DL 1.0%, PFORECL 0.2%, PFORB 0.5%. Ở Government / Non-Conventional, các giá
trị tương ứng là 4.2%, 2.8%, 0.4%, 1.4%. Đây là portfolio snapshot rates theo
mẫu số active cuối quý, không phải default rate của cohort cho vay mới.

## Cách diễn giải và giới hạn

1. NMDB là mẫu 5% mortgage của credit bureau được tổng hợp; file công khai ở đây
   không chứa từng khoản vay. Vì vậy không thể tạo thêm NSMO event, theo dõi một
   loan qua thời gian hoặc train model.
2. Rate chia cho active mortgages tại cuối quý, không phải cumulative incidence
   trong horizon cố định hay performance theo origination vintage.
3. FHFA dùng status do credit bureau ghi nhận và stale-account rule: 3 tháng từ
   2012, 6 tháng trước 2012; áp dụng lookback 24 tháng cho các khoản 180+ ngày
   trễ và foreclosure/bankruptcy/deed-in-lieu. Vì định nghĩa và nguồn báo cáo
   khác nhau, không so trực tiếp như thể cùng một estimator với HUD FHA hoặc
   NSMO PUF.
4. FHFA nói hai quý gần nhất có thể được sửa khi reporting lag đóng; 2026Q1 và
   2026Q2 phải được coi là sơ bộ.
5. Credit-history purge có thể làm thiếu serious-delinquency trong 2006–2012.
   Không quy toàn bộ thay đổi trong giai đoạn này cho chất lượng người vay.
6. FHFA nêu NMDB đại diện tốt hơn cho mortgage nhà xây tại chỗ và owner-occupied
   so với investor mortgages và manufactured homes.
7. Bản dashboard lọc geography National để so xu hướng toàn quốc; nó không đưa
   Census Region/Division vào app và không tạo kết quả suy luận địa phương.

## Tái tạo acquisition

Trong project có `scripts/acquire_nmdb_performance.py`. Mặc định script tải ZIP
chính thức, ghi raw archive vào vùng `data/public/mortgage/nmdb-2026q2/`, rồi
tạo CSV tuyển chọn cùng provenance receipt. Nếu đã có ZIP local:

```powershell
python scripts/acquire_nmdb_performance.py `
  --source-zip D:\data\Codex\credit-atlas\data\public\mortgage\nmdb-2026q2\fhfa-nmdb-performance-national-census-areas-quarterly.zip
```

Tạo lại workbook bằng runtime Excel của workspace:

```powershell
node D:\data\Codex\credit-atlas\apps\excel\build_nmdb_performance_workbook.mjs `
  D:\data\Codex\credit-atlas-public `
  D:\data\Codex\credit-atlas-public\apps\excel\templates\CreditAtlas-NMDB-Performance.xlsx
```

Nguồn định nghĩa chính: [FHFA NMDB Aggregate Statistics](https://www.fhfa.gov/data/nmdb)
và [NMDB Data Dictionary and Technical Notes](https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes-2026q1.pdf).
