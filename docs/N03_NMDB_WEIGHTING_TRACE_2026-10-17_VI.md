# N03 — FHFA NMDB New/Outstanding: trace trọng số và KPI

**Cập nhật:** 18/10/2026 · **Method card:** `nmdb-origination-stock-market-context` · **Source release:** 30/09/2026 · **Consumer:** P2 NMDB workbench và Excel exports.

## Kết luận audit

NMDB New và Outstanding cung cấp các giá trị aggregate do FHFA công bố. CreditAtlas **không tự ước lượng hay tái tính** các series này: API chọn `VALUE1` hoặc `VALUE2` đã có sẵn trong source; biểu đồ và Excel dùng nguyên selected value. App chỉ tính các thống kê trình bày như số observation, số suppressed/unavailable và chênh lệch giữa hai kỳ liền kề khi cả hai đều có giá trị. Không có forecast, zero-fill, smoothing, imputation hay khoản vay giả lập.

Trace đã rà từ ZIP/CSV receipt → mart Parquet → report service → API → UI → workbook. Audit này cũng phát hiện contract VALUE1-only cho ba series New còn thiếu trong code. Đã bổ sung ràng buộc theo Appendix B và test cả trường hợp source có ô VALUE2 numeric nhưng publisher quy định không được dùng weighting đó.

## Phạm vi nguồn và dữ liệu đã kiểm

FHFA mô tả NMDB là mẫu đại diện 5% các khoản vay nhà ở closed-end, first-lien được báo lên một trong ba credit bureau; đây không phải census. Investor loans và manufactured-home loans kém đại diện hơn. FHFA công bố release 30/09/2026 gồm New annual 1998–2025 và Outstanding quarterly 2013Q1–2026Q2. [NMDB Aggregate Statistics catalog](https://www.fhfa.gov/data/nmdb) · [FHFA Data Dictionary and Technical Notes, 26/06/2026](https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes)

| Source ID | Grain và kỳ | Local profile / integrity |
|---|---|---|
| `fhfa-nmdb-new-annual-2026-09-30` | Geography × market × series × year; annual flow theo account-opening date | 3,038,100 rows × 14 fields; 60 series; 1998–2025; 3,038,100 unique keys; 4,980 suppressed; VALUE1 missing 135,084; VALUE2 missing 337,292; không có suppressed row nào có numeric VALUE1/VALUE2. ZIP SHA prefix `ecc0c10dd6d4`, CSV member `74ec6d9f94f3`. |
| `fhfa-nmdb-outstanding-quarterly-2026-09-30` | Geography × market × series × quarter; active-mortgage stock tại cuối quý | 535,464 rows × 14 fields; 37 series; 2013Q1–2026Q2; 535,464 unique keys; không có suppressed rows; VALUE1 missing 0; VALUE2 missing 57,888. ZIP SHA prefix `97654803149d`, CSV member `172376993827`. |

Mart private có 3,573,564 dòng và gắn receipt/hash của hai ZIP, CSV members, source receipt và mart. Reconciliation vừa chạy lại cho thấy row totals khớp profile; số distinct key khớp row count ở cả hai product; không có suppressed rows chứa numeric value hoặc ô không parse được. Profile và raw observations không được đưa vào GitHub public.

## Định nghĩa weighting theo publisher

| Product | `VALUE1` | `VALUE2` | Cách hiểu đúng |
|---|---|---|---|
| New originations | Theo số khoản vay; mỗi sample mortgage đại diện 20 khoản thực | Theo origination loan amount | Annual flow; phân loại theo account opening date. VALUE2 không phải “loan-count average” và không thể so trực tiếp với VALUE1 như cùng một estimand. |
| Outstanding | Theo số khoản vay; mỗi sample mortgage đại diện 20 khoản thực | Theo UPB tại cuối quý | Quarter-end stock. Số khoản active và UPB có thể thay đổi do origination, payoff và các termination khác; không phải cohort flow hay dòng payment. |

**Không nhân VALUE1 thêm 20 trong app.** Đây là weight/định nghĩa thống kê của publisher; source đã phát hành series theo đó. **Không tính lại bình quân từ các geography hoặc market rows.** Categories có thể lồng nhau; “All Mortgages”, parent market, submarket, national và địa lý con không phải các thành phần cộng rời nhau.

Appendix B quy định New `VALUE1`-only cho `TOT_ORIG`, `TOT_LOANAMT`, `AVE_LOANAMT`, `AVE_PAYMENT`, `AVE_PROPVAL`. Appendix C quy định Outstanding `VALUE1`-only cho `TOT_LOANS`, `PCT_LOANS`, `TOT_UPB`, `PCT_UPB`, `TOT_LOANAMT`, `AVE_PAYMENT`. Các series khác chỉ được chọn VALUE2 nếu FHFA có công bố giá trị cho chính product/series đó. Một số cột raw VALUE2 vẫn có số ở series publisher đánh dấu VALUE1-only (ví dụ New `TOT_LOANAMT`, Outstanding `TOT_UPB`/`PCT_UPB`); raw được giữ để audit nhưng UI/API không được coi đó là estimand được phép chọn.

Định nghĩa units giữ theo Appendix B/C: ví dụ `TOT_ORIG` là nghìn khoản vay, New `TOT_LOANAMT` là triệu USD, `AVE_LOANAMT` là nghìn USD, Outstanding `TOT_LOANS` là nghìn khoản active, `TOT_UPB` là tỷ USD, phần trăm giữ theo thang percent, và `AVE_MTMLTV` là current mark-to-market LTV. Code không scale hoặc đổi currency/unit.

## Công thức truy từ code đến app

| Output | Quy tắc chính xác | Consumer / giới hạn |
|---|---|---|
| Selected value | `selected = VALUE1` khi filter `measure=VALUE1`; nếu `VALUE2`, lấy đúng cột VALUE2. Chỉ truy vấn product, geography, market, series, khoảng năm đã chọn; không có weighted mean mới. | `src/credit_atlas/nmdb_mortgage_statistics.py::report`; null được giữ null. |
| Observation count | `count(rows)` sau filter; một row là một kỳ trong một source grain đã chọn. | Không phải unique borrower hay loan count; không cộng qua geography/market hoặc hai product. |
| Suppressed count | `count(suppressed == true)` trong scope. FHFA suppresses estimates có ít hơn 3 loans. | Không thay bằng zero. Trong mart đã audit, New 4,980; Outstanding 0. |
| Selected unavailable count | `count(selected_value is null)` trong scope; có thể gồm suppression và các ô blank/dot không suppressed. Đây là count row, không phải missing-cell total ngoài filter. | Có overlap với suppressed count; không cộng hai KPI với nhau. Raw string, null và cờ suppression được giữ để phân biệt từng row. |
| Latest-period KPI | `selected_value` tại row cuối theo period order; nếu null thì UI báo unavailable. | Một value mô tả cuối kỳ/kỳ năm; không suy ra PD. |
| Adjacent-period change | Nếu hai row cuối theo thời gian đều có selected value: `latest − immediately_previous`; nếu unit `%`, label là percentage points; nếu không thì unavailable. | Không tính relative growth rate và không nhảy qua kỳ null/suppressed. Đây là delta mô tả. |
| Chart | Vẽ selected source value theo các period đã lọc; null ngắt line segment. | Không nội suy hoặc làm trơn. |
| Excel selected data | Ghi cả VALUE1 raw, VALUE2 raw, numeric nullable, selected value, unit, period, filter, suppression, release và mart digest. Chart lấy cột Selected value. | Export chỉ scope query; workbook reference National/USA/All Mortgages có 1,680 annual + 1,998 quarterly observations, không chứa toàn mart. |

Code paths: [`nmdb_mortgage_statistics.py`](../src/credit_atlas/nmdb_mortgage_statistics.py), [`build_fhfa_nmdb_market_mart.py`](../scripts/build_fhfa_nmdb_market_mart.py), [`server.py`](../src/credit_atlas/server.py), [`app.js`](../apps/web/app.js), [`nmdb_mortgage_statistics_excel.py`](../src/credit_atlas/nmdb_mortgage_statistics_excel.py). Source identities và consumer paths nằm trong [source-release register](data/creditatlas-source-release-register-2026-10-17.json); full values/receipts remain private on D:.

## Kiểm chứng và phát hiện đã sửa

- Actual mart query: New 3,038,100 rows / 60 series / 1998–2025; Outstanding 535,464 / 37 series / 2013–2026Q2; all keys unique; missing/suppression counts khớp receipt; suppressed-numeric và invalid-numeric đều bằng 0.
- Direct service call với New / National / USA / All Mortgages / `AVE_INTRATE` / VALUE1 / 2025 trả đúng source-selected 6.3%. `TOT_UPB` Outstanding với VALUE2 bị từ chối vì Appendix C là VALUE1-only.
- Actual raw source có các ô VALUE2 numeric ở một số series VALUE1-only; vì vậy rule không được chỉ dựa vào “cột hiện không có số”. Đã thêm `AVE_LOANAMT`, `AVE_PAYMENT`, `AVE_PROPVAL` vào `VALUE1_ONLY` của New và kiểm thử synthetic mart có VALUE2 numeric cho cả năm series bị cấm; 5 case bị chặn, VALUE2 ở `AVE_INTRATE` vẫn được chọn. Không sửa hay tính lại raw NMDB value.
- Đính chính lỗi gõ ở source register: Outstanding missing VALUE2 là **57,888**, không phải 58,888.
- Native Excel 16.0 read-only acceptance trên hai query export thật từ mart: New annual `AVE_INTRATE` / VALUE1, National / USA / All Mortgages, 1998–2025 (**28/28 × 18 ô**); Outstanding `PCT_MTMLTV_GT100` / VALUE1 cùng geography/market, 2013Q1–2026Q2 (**54/54 × 18 ô**). Cả hai workbook giữ Excel Table filter, không formula error/external link, bytes không đổi sau khi đóng. Chi tiết query và coverage đã khử path/hash tại [N05/N06 query-export Excel acceptance](data/nmdb-market-statistics-native-excel-qa-2026-10-17.json).
- Quan sát thực, không dự phóng: trong Outstanding All Mortgages / National / USA / VALUE1, share active loans có current mark-to-market LTV >100% là **11.3% ở 2013Q1**, **0.1% thấp nhất ở 2022Q2**, và **0.3% ở 2026Q2**. Hai đầu kỳ chênh **−11.0 percentage points**. FHFA định nghĩa `PCT_MTMLTV_GT100` là tỷ lệ khoản vay có current mark-to-market LTV lớn hơn 100%; đây là snapshot có mẫu số active loans thay đổi theo quý, không phải cùng một cohort, không phải LTV tại origination, PD hay dự báo. Release được FHFA đăng 30/09/2026, dữ liệu tới 2026Q2 ([FHFA NMDB catalog](https://www.fhfa.gov/data/nmdb), [Data Dictionary and Technical Notes](https://www.fhfa.gov/document/NMDB-Aggregate-Statistics-Data-Dictionary-Technical-Notes.pdf)).
- Workbook D02 reference được rebuild từ CSV nguồn: `NMDB states` có **79,968 hàng × 13 cột**, khớp đầy đủ từng hàng với CSV; 68 suppression flags và 14,535 ô rate trống vẫn được giữ đúng, trong đó 68/68 suppressed cells blank. Microsoft Excel 16.0 mở read-only/recalc workbook 24 sheet, Table filter hiện, không external link và file không đổi byte. Bằng chứng đã khử thông tin riêng tại [NMDB state-reference Excel acceptance](data/nmdb-state-reference-native-excel-qa-2026-10-17.json).
- Cùng lỗi duplicate worksheet/Table AutoFilter cũng được bỏ khỏi các builder NMDB New/Outstanding và Treasury HAMP summary; regression tests kiểm tra bộ lọc thuộc Table, không nhân đôi ở worksheet. Test suite xác nhận cấu trúc trước khi phát hành workbook.
- Sau các sửa chữa filter/workbook, **35 focused tests pass** cho NMDB mart/API/performance/acquisition/workbooks và Treasury HAMP summary builder.
- N05/N06 New/Outstanding query-grid acceptance: 235 API scopes pass, covering all 115 New and 68 Outstanding published series/weight pairs, all 31 market categories and all five geography levels per product. Fifty-six filtered workbooks match API across 1,758 rows × 18 columns (31,644 cells). The Alaska State × Jumbo Market query preserves seven publisher-suppressed rows as unavailable. Browser QA passes 8/8 checks with no page errors, including URL restoration, VALUE1-only rejection and 390px layout. Two representative exports pass Microsoft Excel 16.0 read-only/full rebuild; filters and charts remain, with zero formulas/errors/external links and unchanged bytes. Thirty focused tests pass. The 151 unavailable-cell occurrences are repeated across overlapping query scopes, not distinct raw cells; suppression remains a separate overlapping subset. Full Cartesian query combinations and native Excel on every export are not claimed. See [query-grid acceptance](data/nmdb-market-query-grid-acceptance-2026-10-18.json).

## Dùng cho mục đích nào, không dùng cho mục đích nào

New/Outstanding hữu ích cho market composition, mortgage characteristic distributions, origination-versus-active-stock context và biến động mô tả theo thời gian. Đây không phải HMDA application/decision rate, không phải applicant/loan-level performance panel, không có individual default target, không xác nhận calibration hay OOT validation cho Freddie, không tự tạo PD/LGD và không cho phép ghép từng geography row với một khoản vay. Nếu cần performance context aggregate, dùng method card riêng `nmdb-active-stock-rates` và giữ denominator/category/time coverage của publisher; không lấy composition series làm performance outcome.

## Việc tiếp theo trong plan

N03 trace cho PUDB, HMDA denominator và NMDB New/Outstanding hiện đã được ghi. N05/N06 đã có broad query-grid acceptance theo phạm vi receipt trên, nhưng vẫn còn các tổ hợp Cartesian và route khác ngoài lưới; không cần tải lại hai archive FHFA khi mart hiện tại đã bind receipt và đối soát. Việc tiếp theo theo Đợt A là hợp nhất N01–N03 status/method trace, rồi N04 public regression/runtime inventory; sau đó chỉ mở thêm NMDB export case khi nó kiểm tra được route hoặc edge khác. Tiếp tục trace formula/input/unit cho HMDA fixed-composition output và numeric outputs còn lại; mỗi KPI cần source ID/release, series definition, filter, unit, period, missing/imputation provenance, test evidence và consumer/API/Excel. Capability ledger vẫn 26/50 cho tới acceptance theo 50 requirements.
