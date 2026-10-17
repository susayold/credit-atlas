# CreditAtlas — nhật ký triển khai theo plan mới

Ngày cập nhật: **17/10/2026**. Plan tổng và thứ tự N01–N24: [PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md](PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md).

## Đợt đang thực hiện: N01–N03 và N05–N06

### N01 — tiến độ dùng chung

- Thêm API `GET /api/project-register`; tổng 50 yêu cầu và tỷ lệ hoàn thành được tính từ `COMPLETION_REQUIREMENTS_50.json`, không gõ riêng số tổng vào UI.
- UI có tổng P1–P5 và D01 R0–R4 ở hai khối riêng. Phần trăm hiển thị chỉ là tỷ trọng capability acceptance của toàn CreditAtlas.
- Completion flags của ledger không đổi. API giữ scope note để giải thích điều kiện còn lại của từng capability.

### N02 — danh mục nguồn dữ liệu

- Tạo catalog ban đầu gồm **24 nhóm dữ liệu trọng tâm**, có domain, grain, kỳ, trạng thái acquisition/audit, quyền truy cập, mục đích, giới hạn, bước tiếp và đường dẫn evidence/nhà phát hành.
- Phân biệt Freddie annual samples đang chờ authenticated access, Ginnie production chưa tải, dữ liệu exposure private và nguồn public đã audit.
- Đây chưa phải census mọi raw source trong workspace và chưa map đủ mọi KPI trong app. Việc nối từng receipt/source version và kiểm tra rights theo từng release tiếp tục trong N02.

### N02 — source-to-KPI code trace — 17/10/2026

- Đọc trực tiếp register hiện tại (**27 dataset/domain records**), `public_sources.catalog()` (**20 source IDs cụ thể**), server routing, service/view classes và các màn hình chính trong `apps/web`.
- Tạo [crosswalk N02 từ source tới KPI/API/workspace](N02_SOURCE_TO_KPI_TRACEABILITY_2026-10-17_VI.md): ghi module, API, UI consumer, output, scope và loại bằng chứng cho từng 27 record. Đây là static trace; không coi sự tồn tại của route là runtime acceptance.
- Xác minh local public-suite acquisition receipt: **20/20 source objects DOWNLOADED_AND_PROFILED**, batch hoàn tất 2026-10-08, không có failure. Receipt private nên bản public chỉ ghi count/status, không phát hành raw rows hay hash. ALFRED, CFPB, HUD FHA, FHFA HPI và Federal Reserve bank context có receipt/review riêng; chi tiết date/grain và semantic gaps được ghi trong crosswalk.
- Tạo [crosswalk N02 dạng JSON](data/n02-source-to-kpi-map-2026-10-17.json) để tiện tra theo registry ID, source ID, module/API và source family. 13/20 `public_sources` IDs map được tới parent record cấp nhóm; bảy FRED series chưa có record source-specific.
- Phát hiện nhiều source family đang có API/UI nhưng chưa có source-level record hoặc chưa bind release/hash đầy đủ: bảy FRED series, FRED/ALFRED vintages, FHFA quarterly HPI, CFPB mortgage delinquency, HUD FHA IIF và performance, Federal Reserve bank asset quality, Fannie format samples và Treasury/ICE market context.
- Một vài record hiện là nhóm bao nhiều source objects: SBA có sáu cohort CSV và dictionary; FDIC có financials snapshot và failure events; HMDA có nhiều release families. Cần crosswalk từng object/receipt, không suy rằng record nhóm đã chứng minh mọi release.
- N02 vẫn **In progress**. Chưa đối chiếu mọi receipt private với register và chưa gắn từng source release/hash vào từng KPI output. Không thay publication date bằng retrieval timestamp; không thay đổi ledger 26/50.

### N03 — provenance và phương pháp

- Ghi nhận bảy loại giá trị: reported, derived, publisher-imputed, model-preprocessing-imputed, model prediction, declared scenario và forecast.
- Registry hiện có mười lăm method cards gắn dataset, target, cách tính/protocol, validation đã lưu, giới hạn và model/data evidence. Các card bao gồm D01 transitions, UCI350, UCI365, NMDB, HMDA action-denominator và fixed-mix, P4 scenario/ECL, Toyota/Nissan/structured ABS và Bondora 12-MOB support.
- Các giả định P4 hiển thị đúng scope illustrative: lịch bullet 36 tháng, monthly EIR 0,004, weights 0,7/0,3; source expected loss vẫn unavailable. Không tạo biến dự phóng mới.
- N03 vẫn đang làm: mọi KPI/output số trên toàn app chưa được liên kết tới method ID và input lineage ngay trong view.
- Trace công thức PUDB, HMDA denominator và NMDB New/Outstanding đã được ghi riêng. Khi rà Appendix B/C cho NMDB, thêm các series New `AVE_LOANAMT`, `AVE_PAYMENT`, `AVE_PROPVAL` vào contract VALUE1-only; kiểm thử synthetic mart bảo đảm VALUE2 numeric thô không mở sai weighting.

### N03 — FHFA NMDB performance KPI trace — 17/10/2026

- Đối chiếu FHFA Data Dictionary/Technical Notes với national extract, state extract, receipt/hash, parser/API, app selectors/tables/charts, workbook builders và hai Excel outputs. Ghi chi tiết tại [N03 NMDB performance trace](N03_NMDB_PERFORMANCE_TRACE_2026-10-17_VI.md).
- Chuẩn hóa `P3089DL` trên API/UI/Excel thành **30–89 DPD**; FHFA gộp bucket 30–59 và 60–89 ngày. Đã sửa cả national NMDB performance workbook lẫn D02 data-reference workbook. Giữ mẫu số active loans cuối quý, native percentage points và 4 market source series riêng.
- Audit actual CSV state: 79.968 rows; 68 cờ suppression, 17 mỗi series, đều ở Vermont × Government / Non-Conventional trong 2004Q1–2008Q3. `PFORB` có 14.484 blank trước 2019Q4; 17 cùng mang suppression flag và 14.467 không mang cờ. Code, app và Excel giữ blank/flag riêng; không điền zero.
- Sửa trend SVG để flush segment tại từng null, thay vì nối đường qua suppression/pre-series gap. Mở rộng Edge QA: P3089 label, Vermont suppressed row, đoạn chart bị ngắt, Excel download, selectors và mobile; **6 checks pass, không page error**.
- Focused tests: `test_nmdb_performance.py`, `test_nmdb_state_performance.py`, `test_nmdb_performance_workbook.py`, `test_d02_data_reference_workbook.py` — **6 passed**. Workbook D02 có 23 sheet và 79.968 state rows; artifact-tool render QA xác nhận định nghĩa; native Excel desktop chưa mở/recalculate.
- Đây là trace/presentation fix, không thêm row hay forecast. N03 còn KPI khác; N05/N06 tổng vẫn mở; capability acceptance giữ **26/50 = 52%**.

### N05 — canonical FHFA NMDB aggregate mart

- Dựng `data/derived/fhfa-nmdb-market-statistics/market-statistics.parquet` trong private workspace từ hai ZIP có receipt PASS; dữ liệu public raw không được chép vào public checkout.
- Mart chứa 3.573.564 hàng aggregate, khóa có product để giữ riêng annual origination flow và quarterly outstanding stock. Raw strings, nullable numeric values, geography, units, suppression, release và source hashes được giữ.
- Đối soát source profile: 3.038.100 New + 535.464 Outstanding; 4.980 dòng New suppressed; missing VALUE1/VALUE2 lần lượt 135.084/337.292 ở New và 0/57.888 ở Outstanding; zero invalid numeric rows.
- Phân biệt series theo FHFA Appendix B/C. Các series được publisher ghi VALUE1-only không cho chọn VALUE2 dù file raw có thể chứa ô ở cột VALUE2.
- Dataset profile cho thấy 37 Outstanding series IDs, không phải 38 như dòng trong research checkpoint cũ; đã sửa tài liệu nguồn.

### N06 — app và Excel

- Thêm P2 view `nmdb` với product, geography level/id, market, series, trọng số và year filters; có time-series chart, latest-period KPI, liền-kề delta, missing/suppression, provenance và use limits.
- Thêm API catalog/report và query-scoped `.xlsx` endpoint. Workbook reference National / USA / All Mortgages có 1.680 New annual + 1.998 Outstanding quarterly rows, 97 codebook definitions, latest KPIs và quality/lineage.
- Export giữ VALUE1/VALUE2 raw, giá trị đã parse, suppression, selected measure, filter context, source release và mart SHA-256. Excel không nhồi toàn bộ 3,57 triệu aggregate rows vào một sheet.
- N05/N06 chưa đóng acceptance tổng: runtime/API/export đã có; browser QA hiện pass cho NMDB performance và representative New/Outstanding filters/query-scoped exports. Native Excel desktop và các route khác vẫn còn mở. Không tăng completion 26/50 chỉ vì thêm implementation.

### Runtime review N05/N06 — 17/10/2026

- Catalog runtime trả đúng 3.038.100 New annual / 60 series / 27 markets và 535.464 Outstanding quarterly / 37 series / 4 markets.
- New National / USA / All Mortgages, `AVE_INTRATE`, VALUE1 trả 28 năm 1998–2025; giá trị cuối 2025 là 6,3% theo source scale. Outstanding `AVE_MTMLTV`, VALUE2 trả 54 quý đến 2026Q2; giá trị cuối là 54,2%.
- VALUE2 cho Outstanding `TOT_UPB` bị từ chối HTTP 400 theo quy tắc VALUE1-only của FHFA.
- Query-scoped Excel export cho New annual và Outstanding quarterly đều trả HTTP 200. Đã đọc cấu trúc XLSX: bốn sheet; biểu đồ bind cột `Selected value` và nhãn kỳ dạng text, không che bảng dữ liệu. Workbook tham chiếu tải qua route HTTP 200, 389.862 bytes.
- Đây là runtime/API/export check; chưa thay thế browser visual acceptance hay Excel desktop open/recalculate review.

### Edge browser acceptance N05/N06 New/Outstanding — 17/10/2026

- Thêm `scripts/browser_nmdb_market_statistics_qa.py`; chạy Edge headless qua test server, public UI checkout và private receipt-bound mart `89fae54538e3…` (3.573.564 aggregate rows). QA receipt, hai workbook tải và output đầy đủ được giữ ngoài public repo trong thư mục scratch riêng.
- **8 checks pass, 0 page/console errors:** New annual 1998–2025, AVE_INTRATE VALUE1 = 6,3% năm 2025; Outstanding quarterly AVE_MTMLTV VALUE2 = 54,2% năm 2026Q2, đủ 54 quý; URL filters survive reload; selected `TOT_UPB` chỉ mở VALUE1 và API trả HTTP 400 khi ép VALUE2; mobile 390px không overflow.
- State Alaska × Jumbo Market × AVE_INTRATE có 27 annual observations; 7 suppressed cells giữ unavailable và chart tách thành 4 observed segments. Hai query-scoped workbooks được kiểm bằng openpyxl: filters/weighting, 27/54 observation rows, missing/suppression flags, latest values, bốn sheet và chart đều khớp API report.
- Kiểm tra workbook này là đọc package/XLSX theo cấu trúc và data values; **không** khẳng định Microsoft Excel desktop mở/recalculate thành công. Không xuất raw loan-level records. N05/N06 tổng vẫn mở cho Excel desktop, PUDB/HMDA/route parity còn lại và các KPI chưa trace; capability ledger giữ **26/50 = 52%**.

## N07 — Toyota recovery-component exception ledger

- Tạo bridge aggregate công khai cho Toyota 2022-B (51 kỳ) và 2024-B (29 kỳ), gắn từng kỳ với collection-period start/end, calendar days, filing date, ABS-EE/10-D accession, certificate URL và certificate hash. Không phát hành contract/asset IDs.
- Kiểm tra bằng Decimal: certificate aggregate-proceeds identity **80/80** và net-credit-loss identity **80/80**. So sánh ABS-EE `recoveredAmount` với certificate aggregate proceeds: **3/80 tied**, **77/80 unresolved**; residual tổng **+USD 3,823,205.14** (2022-B +USD 2,058,647.06; 2024-B +USD 1,764,558.08).
- Ghi rõ hai trust đều có kỳ đầu 01/03–30/04 dài 61 ngày; không suy collection window từ report-month. Chưa có evidence xác định timing, population, amendment, correction hay field mapping là nguyên nhân. Không tính recovery rate/LGD/PD/forecast và không ép residual về 0.
- Thêm [nghiên cứu chi tiết](TOYOTA_RECOVERY_COMPONENT_EXCEPTION_LEDGER_VI.md), [CSV aggregate ledger](data/toyota-recovery-components-80-periods.csv), [receipt/hash summary](data/toyota-recovery-components-80-periods-receipt.json) và workbook Excel lọc được tại `apps/excel/templates/CreditAtlas-Toyota-Recovery-Exception-Ledger.xlsx`. Công thức summary trong workbook đối chiếu lại 80/3/77 và tổng residual; ba sheet đã render để kiểm tra bố cục.
- Theo tiêu chí N07, ledger/bridge và bằng chứng unresolved đạt. Việc xác định root cause và qualification cho LGD/cashflow vẫn mở. Excel desktop chưa mở/recalculate; kiểm tra vừa làm chỉ dùng artifact-tool/render.
- N07 là một action trong kế hoạch, không phải một trong 50 capability acceptance; ledger toàn CreditAtlas vẫn **26/50 = 52%**.

## N08 — Nissan event, DPD và recovery exceptions

- Tái lập panel Nissan 2024-B gồm **23 kỳ**, **1.154.259 asset-month rows** và **63.688 asset keys**; public deliverable chỉ có số tổng theo kỳ, accession, URL và hash lineage.
- So sánh độc lập các candidate: pool balance và positive-balance count **23/23**; positive charge-off count **20/23**, amount **21/23**; first-code-4 count **21/23**, amount **20/23**; DPD literal **178/184**; recovery **17/23**. Không chọn event rule chỉ để khớp một tháng.
- Tháng 07/2025: 36 positive charge-off rows / **+$655.185,56** ở ABS-EE; certificate có 1 defaulted receivable và principal signed **−$59.000,49**. Không có transaction-level mapping chứng minh đây là cùng một đại lượng. SEC submission census ngày 17/10/2026 không có 10-D/A hay ABS-EE/A cho report date này trong 57 submission gần nhất; điều đó không loại trừ adjustment trong servicing records.
- Tháng 06/2025 DPD literal khớp **2/8** bucket fields; candidate dời ranh giới sớm một ngày khớp **8/8** riêng tháng đó nhưng chỉ **86/184** trên toàn panel so với **178/184** literal. Candidate được giữ ở dạng diagnostic, không áp thành rule.
- Sáu recovery deltas (12/2024–05/2025) tổng **+$8.859,23**. Workbook ba sheet có summary công thức, period ledger lọc được đủ 66 trường và method/source notes; công thức được artifact-tool tính lại, các checkpoint ra đúng **23/23/23/20/21/17/6; $8.859,23; 178/184; 86/184**. Đã render và xem bố cục; chưa mở/recalculate bằng Microsoft Excel desktop.
- Thêm [Nissan exception research](NISSAN_2024B_EXCEPTION_LEDGER_VI.md), [23-period CSV](data/nissan-2024b-exception-ledger-23-periods.csv), [receipt/hash summary](data/nissan-2024b-exception-ledger-23-periods-receipt.json) và workbook [CreditAtlas-Nissan-Exception-Ledger.xlsx](../apps/excel/templates/CreditAtlas-Nissan-Exception-Ledger.xlsx). Registry ghi riêng panel và public aggregate derivative.
- Theo acceptance của N08, tái lập exceptions và bác bỏ rule chỉ khớp một kỳ đã đạt. Root cause/source-field mapping còn mở; N08 không phải capability trong 50-item ledger nên CreditAtlas vẫn **26/50 = 52%**.

## N09 — contract-aware ABS surveillance

- Tạo hợp đồng dữ liệu riêng cho Toyota 2022-B, Toyota 2024-B và Nissan 2024-B. Comparator Toyota là aggregate net liquidation proceeds từ hai signed certificate components; Nissan là current-period Recoveries of Defaulted Receivables. Collection window, source signs, DPD definitions, missingness và source accession giữ theo từng trust.
- Build 103 aggregate deal-period rows, kiểm SHA-256 của input ledgers/receipts, contract JSON và output CSV. Runtime API kiểm integrity, khóa contract × report date duy nhất, period counts và summary trước khi trả dữ liệu.
- Kết quả: 86/103 kỳ có ít nhất một exception; 83 recovery residual khác 0. Toyota 2022-B: 2/51 recovery ties, 49 exceptions, residual +USD 2,058,647.06 trong deal. Toyota 2024-B: 1/29, 28, +USD 1,764,558.08. Nissan 2024-B: 17/23, 6, +USD 8,859.23; thêm ba kỳ exception không thuộc recovery; literal DPD 178/184. Không tính recovery-dollar total hay tie-rate chung qua deal.
- Thêm `ABS-SURV-F001` với root cause open, use limits, required follow-up evidence và link filing tại từng kỳ. Finding không phải LGD/loss/fraud/ECL hay validation kết quả model.
- Thêm API `/api/absee-surveillance`, report JSON và workbook route; UI hiển thị summary, contract comparator, nguồn SEC liên kết và exception drilldown. Excel có Summary, Period ledger, Data contracts, Analyst finding; công thức đối chiếu 103/3/86/83 và số theo từng deal.
- Thêm finding note, release contract, CSV/receipt, method card, dataset record và README Excel. Public release chỉ chứa aggregate period rows, không phát hành loan/asset-level records.
- Acceptance N09 đủ: hợp nhất các deal với explicit contract, source-backed KPI, exception drilldown, SEC links, Excel và analyst finding đã có. Root cause vẫn mở; 83 recovery deltas chưa giải thích. N09 không đổi 26/50 capability acceptance.

## N14 — Bondora 12-MOB label and maturity qualification

- Kiểm tra lại file tải hiện hành bằng HTTP HEAD ngày 17/10: 162,618,206 bytes, Last-Modified 10/08/2026 và ETag trùng source đã pin; SHA-256 `a75db03e…e1a07bf`. Không có file mới để thay thế snapshot.
- Thêm full-workbook aggregate audit, không xuất loan ID/dòng khoản vay. Reconcile 789,144 rows / 31 fields / hai sheets; tri-state labels là 86,618 true, 520,246 false và 182,280 NULL. Country × origination-year có 58 cell, bốn cell <50 được suppress trong workbook.
- Kiểm tra maturity bằng proxy minh bạch: issue date +12 calendar months ≤ ngày Last-Modified 10/08/2026. 617,724 khoản proxy-mature; trong đó 10,860 label vẫn NULL. Cả 10,860 không có action date tại/sau anniversary: 7,996 không có action date và 2,864 action trước anniversary. Phần còn lại 171,420 đều NULL và chưa mature theo proxy. Không biến NULL thành false.
- Phân tầng 10,860 proxy-mature NULLs: 7,178 Active; 2,864 Repaid; 818 Defaulted. `months_on_book`: dưới 12 là 9,150, 12+ là 1,657, missing 53. Đây là mô tả trạng thái; không giải thích nguyên nhân label hoặc thay đổi nhãn.
- Nghiên cứu [2026 publisher transparency report](https://goandgrow.eu/en/blog/bondora-loan-portfolio-statistics-2026-a-transparency-report/): publisher dùng PD12 cho cohort đủ 12 tháng và mô tả default là >90 DPD kèm chấm dứt hợp đồng do arrears. Chưa có bằng chứng định nghĩa này khớp mọi lịch sử trong export. Không có feature set/model fit; post-booking fields bị loại khỏi underwriting use.
- Thêm [N14 audit note](BONDORA_N14_LABEL_MATURITY_AUDIT_VI.md), script `scripts/audit_bondora_n14_readiness.py`, hai boundary/tri-state tests và Excel [Bondora label support](../apps/excel/templates/CreditAtlas-Bondora-N14-Label-Support.xlsx). Detailed report chỉ nằm trong private artifacts; workbook chứa aggregate counts và suppress small cells.
- N14 còn partial: cần publisher xác nhận observation cutoff/label build và giải thích 10,860 NULLs. Không đủ để gọi PD/model-ready hay kết luận lỗi nguồn.

## Giao diện

Trang **Tiến độ & registry** trong điều hướng chung hiển thị capability acceptance, D01 releases, dataset filters, quyền truy cập, method cards và giới hạn. Register JSON có thể tải xuống. Không đưa raw borrower rows hoặc private exposure values vào catalog.

Workbook plan ở `docs/reviews/` đã cập nhật trạng thái N01–N03 thành **Đang làm** và ghi cụ thể phần còn lại; không đổi tỷ lệ acceptance 26/50.

## Trạng thái kiểm tra

N09 verification: `tests/test_absee_surveillance.py` và `tests/test_http_boundary.py` chạy với basetemp trên D: cho **20 passed, 5 skipped**; các test mới về hash/summary/filters/API/report/XLSX đều pass. Năm skip thuộc fixtures cần machine-local/private inputs. Workbook N09 recalculates 103/3/86/83 và từng deal; Summary và Analyst finding được render để QA. N14: hai test label/calendar boundary pass; full source audit khớp SHA, rows/columns/labels và tạo private aggregate report; workbook formulas reconcile 789,144 / 86,618 / 520,246 / 182,280; Summary, country support và method notes được render. `node --check`, Python compile, JSON parse và `git diff --check` được kiểm tra trước publish. N06 New/Outstanding representative Edge acceptance hiện pass 8 checks; Excel desktop open/recalculate và các route/source khác vẫn mở. N01–N03 cũng chưa được nghiệm thu cuối. Lượt trước có public regression 1.670 passed/196 skipped trước các thay đổi này; kết quả đó không thay cho test mới.

## Bước kế tiếp

1. Mở/recalculate các workbook N06 trong Excel desktop; tiếp tục browser/query parity cho PUDB, HMDA và các route NMDB còn lại.
2. Hoàn thiện N02 theo crosswalk mới: tách source families đang thiếu record, bind mọi release/hash receipt và kiểm tra source rights/date-grain cho từng KPI.
3. Nối KPI outputs vào method cards, gồm numerator/denominator, data release/as-of, formula và missingness; giữ các score/final holdout đã freeze nguyên trạng.
4. Chuyển sang N10: chuẩn bị pilot Freddie annual sample và kiểm tra quyền truy cập, receipt/hash, release/layout, parser counts và resource budget khi Clarity session hợp lệ có sẵn. Không giả lập sample chưa tải.
