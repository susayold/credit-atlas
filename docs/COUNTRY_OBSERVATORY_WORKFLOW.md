# P4 — Country Credit Context Observatory

Ngày 09/10/2026. Mở `http://127.0.0.1:8770/?view=country` hoặc chọn
**P4 · Country observatory**. Đây là country/economy annual context;
chưa phải sovereign PD, rating, exposure book hoặc mô hình stress đã hiệu chỉnh.

## 1. Nguồn và phạm vi

Đã tải qua HTTP API World Bank V2, không cần account/API key:
[API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392),
[pagination/date-range/footnotes](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures).
Nguồn `2` (WDI), phạm vi 1960–2025, giữ tất cả returned rows và source NULL.
Một query có thể trả cả quốc gia/economy và các nhóm tổng hợp chồng lấn.

| Chỉ báo | Code | Đơn vị/ý nghĩa |
|---|---|---|
| NPL / gross loans | FB.AST.NPER.ZS | %, stock ratio hệ thống deposit takers |
| Bank capital / assets | FB.BNK.CAPA.ZS | %, đọc capital definition của nguồn; không dùng FDIC equity ratio thay thế |
| Private credit | FS.AST.PRVT.GD.ZS | % GDP, financial corporations |
| Private credit by banks | FD.AST.PRVT.GD.ZS | % GDP, phạm vi banks riêng |
| External debt stock | DT.DOD.DECT.GN.ZS | % GNI; gồm public/private debt, không phải chỉ government debt |
| Real GDP growth | NY.GDP.MKTP.KD.ZG | annual % change |
| CPI inflation | FP.CPI.TOTL.ZG | annual % change; giá trị âm giữ nguyên |

Định nghĩa và footnotes giữ nguyên trong metadata/records. Current API/glossary
capital definition dùng Tier 1 / total assets; methodology/consolidation có thể
khác theo quốc gia và thời kỳ. Không tự biến thành CET1/RWA compliance.
[Capital glossary](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/FB.BNK.CAPA.ZS),
[NPL glossary](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/FB.AST.NPER.ZS),
[external debt glossary](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/DT.DOD.DECT.GN.ZS).

## 2. Artifacts đã chạy trên dữ liệu thật

- Source: `country-source-f58e3805c53f`, 22 files (country catalog + 7 lần
  observations/indicator metadata/glossary), **30.437.643 bytes**. Immutable URL, bytes, SHA-256,
  retrieved time, exact pages/totals lưu trong receipt.
- Canonical: `country-case-a651e2bdc3d1`, **122.892 rows** = 7 × 66 × 266.
  **100.254 economy rows**, **22.638 aggregate rows**; 217 economies và
  49 aggregates được trả cho các chỉ báo. Catalog hiện có 296 entries,
  gồm 217 economies/79 aggregates; 30 catalog aggregates không có trong query.
- Independent audit: `country-audit-ca473df34ec4`, **PASS**,
  bidirectional SQL EXCEPT ALL: **0 differing rows**; duplicate/orphan keys: **0**.
  Native JSON → exact identity join → SQL projection độc lập so với adapter.
- App view: `country-view-b6e001ce51a3`, immutable source-backed snapshot.
  Source/canonical/view bytes và methods kiểm tra mỗi lần đọc; sửa summary rồi
  cập nhật digest vẫn bị phát hiện khi projection không khớp nguồn.

Private files nằm dưới `private evidence omitted from public release` và `private evidence omitted from public release`
trên D:. Batch đầu `country-source-44479f1d7ba5` đã tải nhưng bị adapter ban đầu
chặn do blank ISO3/name whitespace; không có case ready từ batch đó. Sau sửa
exact-join contract, batch mới ở trên đã tải và được kiểm chứng. Không sửa
receipt cũ hoặc ghi đè raw data.

## 3. Data quality và phạm vi dùng được

| Finding | Evidence | Tác động và xử lý |
|---|---|---|
| Missing source values | 64.452 / 122.892 rows | Không đủ coverage đồng đều; giữ NULL, không zero/impute/carry-forward |
| Blank source ISO3 | 2.310 rows | Medium identity risk; nối duy nhất bằng exact catalog ISO2 + tên trim-equivalent, giữ source ISO3 blank và join_basis |
| Name whitespace differences | 924 rows | Low; raw name và catalog name đều giữ, không fuzzy matching |
| Blank API unit | 122.892 rows | Unit ambiguity; source_unit blank giữ nguyên, declared_unit riêng dựa definition/glossary; không coi là probability |
| Footnotes | 20 rows | Giữ nguyên trên timeline/report; không silently drop annotations |
| Coverage/vintage | API lastupdated 2026-10-08 | Latest revised snapshot, reference year không phải publication year; chưa PIT backtest |
| Classification | Current region/income metadata | Không dùng current group để khẳng định membership lịch sử |
| Aggregate semantics | 49 overlapping returned aggregates | Tách universe; không cộng ratios/countries + regions thành tổng |

Tất cả findings trên được kiểm chứng từ source snapshot đã lưu, confidence cao
cho số lượng/identity; chưa chứng minh country methodology comparability.
NPL và capital aggregate rows đều NULL trong snapshot này. NPL countries có
2.357 known rows/154 economies (từ 2000), capital có 2.301/152; API reference
range bắt đầu 1960 không có nghĩa hai series thực sự có dữ liệu từ 1960.

SQL và annual coverage lưu trong audit directory. Notebook
`source-quality.ipynb` chứa các SQL đã dùng và code rerun; là companion để xem/chạy
lại, chưa chạy bằng một notebook kernel riêng. Receipt audit là evidence đã thực thi.

## 4. Luồng app và export

1. Chọn verified snapshot, **Countries/economies** hoặc **Source aggregates**.
2. Chọn entity, indicator, comparison year và timeline range.
3. Timeline giữ NULL/footnote/status, chart ngắt tại missing/absent years.
4. Cross-section chỉ lấy **đúng comparison year và universe**; tất cả returned
   entities gồm missing để mẫu số rõ ràng. Không thay bằng latest known value.
5. Latest-known profile có **reference year riêng cho từng indicator**, chỉ
   tìm ở/before comparison year. Nó không được dùng điền vào selected-year metrics.
6. Export giữ full selected timeline và same-year cross-section, source/native
   identifiers, units, annotations, declared join basis và limitations.

Ví dụ VNM: NPL 2024 có dữ liệu; NPL 2025 NULL. GDP growth/CPI 2025 có dữ liệu.
Hai nhóm này không được tự căn cùng latest year rồi gọi là comparable snapshot.
Source values được display làm tròn; JSON giữ numeric values của snapshot.

API: `/api/country-views`, `/api/country-view?view_id=...`,
`/api/country-report?view_id=...&country=VNM&indicator=FB.AST.NPER.ZS&year=2024&from=2010&to=2025&universe=economies`.
Host/origin loopback, duplicate/unknown/out-of-range/mixed-universe filters bị
chặn; no-store, CSP, private aggregate export, không raw-file serving.
Source glossary licenses/attribution được giữ; chưa cho phép public release của app.

## 5. Commands và phần tiếp theo

Acceptance: **704 software tests PASS** (375 engine + 329 application),
145,25 giây. Actual browser **10 checks PASS**,
`country-browser-qa-2bfc8b3b2089`: source counts, VNM/null behavior,
same-year/universe isolation, private export parity, ISO2 resolution, URL reload,
390px mobile, no-mortgage-run operation, cross-workspace navigation và
zero JavaScript/console errors. Annual chart giữ gap; table cross-section scroll
trong card để kiểm tra đầy đủ mà không kéo dài toàn trang.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/acquire_country_observatory.py
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_country_observatory.py --source country-source-f58e3805c53f
.\.venv\Scripts\python.exe -X utf8 scripts/audit_country_observatory.py --case country-case-a651e2bdc3d1
.\.venv\Scripts\python.exe -X utf8 scripts/build_country_view.py --case country-case-a651e2bdc3d1
.\.venv\Scripts\python.exe -X utf8 scripts/browser_country_qa.py
.\scripts\test.ps1
.\scripts\run.ps1
```

Country context không hoàn thành sovereign-default/debt model. Default/event
sources, release vintages, country methodology notes và economic stress
response vẫn là dependencies riêng. P4 còn typed exposures, EL/ECL/staging,
dependence/tail scenarios và finance/review package; full suite tiếp tục theo
[PLAN_FIVE_WORKSPACES.md](PLAN_FIVE_WORKSPACES.md).
