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

### N03 — HMDA fixed-2023-mix source audit — 17/10/2026

- Chạy `scripts/audit_hmda_cohorts.py` trên cohort private để đọc độc lập source CSV bằng DuckDB, so sánh toàn bộ joint mart, rồi tính lại ordered attrition, action counts/amounts, denominator, full-reference/common-support rates, missing strata và weight coverage cho từng preset/năm.
- **70/70 checks pass**, gồm kiểm tra hash source/cohort không đổi trong audit. Detailed receipt và cell-level cohort values vẫn ở private workspace, chưa được duyệt phát hành công khai.
- Kết quả xác nhận phép tính và lineage local cho cohort này; không chứng minh source publisher completeness, không phải PD/causal/fairness result và không thay thế browser/Excel acceptance. N03 vẫn mở cho các release/query HMDA khác và KPI còn lại.
- Không thêm forecast, không đổi data, không nâng capability ledger: **26/50**.

### N03 — FHFA NMDB performance KPI trace — 17/10/2026

- Đối chiếu FHFA Data Dictionary/Technical Notes với national extract, state extract, receipt/hash, parser/API, app selectors/tables/charts, workbook builders và hai Excel outputs. Ghi chi tiết tại [N03 NMDB performance trace](N03_NMDB_PERFORMANCE_TRACE_2026-10-17_VI.md).
- Chuẩn hóa `P3089DL` trên API/UI/Excel thành **30–89 DPD**; FHFA gộp bucket 30–59 và 60–89 ngày. Đã sửa cả national NMDB performance workbook lẫn D02 data-reference workbook. Giữ mẫu số active loans cuối quý, native percentage points và 4 market source series riêng.
- Audit actual CSV state: 79.968 rows; 68 cờ suppression, 17 mỗi series, đều ở Vermont × Government / Non-Conventional trong 2004Q1–2008Q3. `PFORB` có 14.484 blank trước 2019Q4; 17 cùng mang suppression flag và 14.467 không mang cờ. Code, app và Excel giữ blank/flag riêng; không điền zero.
- Sửa trend SVG để flush segment tại từng null, thay vì nối đường qua suppression/pre-series gap. Mở rộng Edge QA: P3089 label, Vermont suppressed row, đoạn chart bị ngắt, Excel download, selectors và mobile; **6 checks pass, không page error**.
- Focused tests ở checkpoint ban đầu: `test_nmdb_performance.py`, `test_nmdb_state_performance.py`, `test_nmdb_performance_workbook.py`, `test_d02_data_reference_workbook.py` — **6 passed**. D02 khi đó có 23 sheet và 79.968 state rows; native Excel được nghiệm thu ở follow-up phía dưới.
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
- N05/N06 chưa đóng acceptance tổng: runtime/API/export và browser QA đại diện đã có; hai actual New/Outstanding query exports cùng D02 state reference được native Excel nghiệm thu ở follow-up phía dưới. Các route/filter còn lại vẫn mở. Không tăng completion 26/50 chỉ vì thêm implementation.

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

### Native Excel và parity follow-up N03/N05/N06 — 17/10/2026

- Rà lại mọi workbook builder có `add_table()` và phát hiện filter bị khai báo đồng thời ở worksheet và Excel Table trong NMDB query exports cùng D02 `NMDB states`. Đã gỡ sheet-level filter lặp ở hai builder; Table filter vẫn hiện trong Excel. Cùng cấu trúc lặp được gỡ khỏi Treasury HAMP summary builder và có regression test round-trip.
- Tạo hai export từ mart FHFA receipt-bound: New annual `AVE_INTRATE` / VALUE1, National / USA / All Mortgages, 1998–2025 (**28/28 hàng × 18 cột**) và Outstanding `PCT_MTMLTV_GT100` / VALUE1, cùng geography/market, 2013Q1–2026Q2 (**54/54 × 18**). Excel 16.0 read-only mở cả hai, rebuild, xác nhận table filters hiện, 0 formula error/external link và bytes không đổi. Release 2026-09-30; không dùng forecast/imputation.
- Quan sát mô tả từ series source: share active mortgages có current MTM LTV >100% theo VALUE1 là 11.3% ở 2013Q1, mức thấp nhất 0.1% ở 2022Q2 và 0.3% ở 2026Q2; endpoint change −11.0 pp. Đây là snapshot qua các mẫu số active-stock khác nhau, không phải cùng một cohort hay PD. [FHFA định nghĩa series](https://www.fhfa.gov/document/NMDB-Aggregate-Statistics-Data-Dictionary-Technical-Notes.pdf).
- Rebuild D02 data-reference workbook: 24 sheets; `NMDB states` có 79,968 hàng × 13 cột, exact row parity với CSV. 68 suppressed values vẫn blank trong tổng 14,535 blank rate cells. Excel 16.0 read-only mở/rebuild, Table filter hiển thị, 0 external links, file không đổi.
- Một query NMDB Performance có suppression (98×12), workbook plan (18 formulas, 0 errors, ledger 26/50) cũng đã qua native Excel ở follow-up trước. Tổng hiện có **35 focused tests pass** cho các test NMDB và Treasury workbook liên quan. Bằng chứng sanitized: [New/Outstanding exports](data/nmdb-market-statistics-native-excel-qa-2026-10-17.json), [state reference](data/nmdb-state-reference-native-excel-qa-2026-10-17.json), [performance query](data/nmdb-query-excel-native-qa-2026-10-17.json).
- N05/N06 vẫn **partial**: query/export samples đã mở bằng native Excel, nhưng chưa cover đủ mọi geography × market × series × measure × period; PUD/HMDA/HUD exports và HAMP native Excel còn mở. Capability ledger giữ **26/50 = 52%**.

### Browser acceptance FHFA PUDB acquisition profile — 17/10/2026

- Thêm `scripts/browser_pudb_profile_qa.py`; chạy Edge headless trên mortgage source workspace bằng profile receipt-bound và workbook private. QA receipt, JSON export và workbook tải ở `artifacts/private/pudb-browser-qa-20261017`, không đưa dữ liệu private lên repo.
- **5 checks pass, 0 page/console errors:** UI khớp source release 2026-09-24, 2.093.767 rows, 66 fields, 2.093.767 unique keys và archive SHA; category tables khớp profile; API và JSON download khớp service output; 390px không overflow.
- Workbook tải từ route có năm sheet, đối soát **126 category rows** và **66/66** field missingness/dictionary; 5 category cells dưới 30 được giữ suppressed, formulas cho category share còn hiện diện. Profile xác nhận `public_release_approved=false`.
- Native Excel desktop open/recalculate vẫn chưa xác nhận. Đây là annual Enterprise acquisitions, không có payment/default target và không trở thành D01 performance panel.

### Browser acceptance HMDA national releases — 17/10/2026

- Chạy lại `scripts/browser_hmda_national_qa.py` trên code hiện tại sau khi xác nhận receipt cũ có `app.js` hash khác. Private receipt và workbook/JSON tải từ trình duyệt được giữ trên D: và không đưa vào repo.
- **21 checks pass, không ghi nhận page/console errors:** 2025 National Snapshot và Dynamic weekly snapshot; One-Year 2020–2024; state/action-3 denial-reason JSON so khớp API; workbook Excel mỗi release tải từ route trùng byte với source workbook; national summary hiển thị tại viewport 390px.
- National Snapshot 2025: **13.543.606 records / 4.782 reporters / 9.360.942 quyết định / 22,5948%** descriptive denied share. Dynamic as-of 2026-10-11: **13.558.306 / 4.794 / 9.373.448 / 22,5718%**. Giữ snapshot/version riêng; không gộp thành cùng một sample.
- One-Year 2020–2024 đã hiển thị riêng theo release. Counts lần lượt **25.666.745 / 26.227.364 / 16.099.307 / 11.564.178 / 12.259.199**; descriptive denied shares **15,8829% / 15,6948% / 22,0795% / 25,2792% / 24,2844%** trên action 1–3 decision denominator. Đây là tỷ lệ mô tả theo từng release, không phải trend chuẩn hóa hoặc PD; thay đổi window/definition cần được đánh giá trước so sánh thời gian.
- HMDA vẫn là application/decision data, không chứa repayment/default outcomes. Tại checkpoint này còn mở browser route One-Year 2019 và native Excel; các follow-up bên dưới đã đóng hai acceptance đó. Quyền tái sử dụng phần mềm và harmonization/comparability giữa release vẫn cần đánh giá riêng. Giữ privacy/release gates và không đổi ledger **26/50 = 52%**.

### Browser acceptance HMDA 2018 Three-Year — 17/10/2026

- **4 checks pass, không có page/console errors:** nguồn khớp **15.138.510 records**, quarantined **1.961** hồ sơ action `-1`, decision denominator **10.623.751**, tám action categories và 57 state categories. Bộ lọc LTV đổi breakdown theo nguồn.
- Route tải workbook riêng tư đúng tên `CreditAtlas-HMDA-2018-Three-Year-Analysis.xlsx`; mobile 390px không overflow. Receipt và workbook ở D:, `public_release_approved=false`.
- Ở checkpoint này, HMDA có **25 browser checks** trên 2025 Snapshot/Dynamic, One-Year 2020–2024 và Three-Year 2018. Các lượt bổ sung sau đó đưa tổng acceptance lên 46 checks; native Excel được nghiệm thu cho đủ chín workbook release-bound. Comparability giữa loại release vẫn cần nghiên cứu riêng; đây không phải performance/PD sample.

### HMDA release selector và tải theo module — 17/10/2026

- Browser diagnostic phát hiện `hmdaWorkspace` trước đây tải nối tiếp National, Three-Year 2018, One-Year 2019–2024 và legacy cohort/reference khi mở một trang. Trên private source, các response của National bắt đầu ở 73,5s, One-Year 2024 ở 110,8s và One-Year 2019 ở 180,4s; lượt diagnostic không tới legacy summary trong 183s. `networkidle` acceptance cũ timeout 60s dù các API đã phản hồi HTTP 200 và không thấy JS/page errors.
- Thêm menu **HMDA release / analysis** với lựa chọn URL-persistent: 2025 Snapshot/Dynamic, 2018 Three-Year, từng One-Year 2019–2024, và legacy lender/geography/cohort analysis. Trang mặc định chỉ gọi module National; các module còn lại chỉ gọi khi người dùng chọn. Giữ query deep link legacy qua `hmda_view_id`.
- Cập nhật `scripts/browser_hmda_qa.py` để nhận data `--root` và UI `--web-root` riêng; QA giờ chạy code public checkout trên private D: data, không phụ thuộc app copy ở data root.
- Chạy lại suite trên code hiện tại: national **21/21 checks pass**, 2018 Three-Year **4/4**, legacy cohort/reference **17/17**; không browser errors. Coverage gồm release summaries, source denominator, state/LTV/denial-reason breakdowns, API/JSON parity, byte-identical XLSX downloads, responsive 390px và điều hướng các workspace. Receipt và downloaded outputs lưu private trên D:.
- Đây là chia tải theo module, không xóa nguồn hay gộp sample. Follow-up đã đóng browser acceptance One-Year 2019 và native Excel cho cả chín workbook HMDA release-bound; release comparability/rights và KPI/outcome nằm ngoài application LAR vẫn mở. Ledger vẫn **26/50 = 52%**.

### Browser acceptance HMDA One-Year 2019 — 17/10/2026

- Chạy `scripts/browser_hmda_one_year_2019_qa.py` trên frozen One-Year source riêng; module nhận `hmda_panel=one_year_2019` và chỉ tải view 2019.
- **4 checks pass, không page/console errors:** 17.563.200 LAR records, 5.565 reporters, action 1–3 denominator **12.280.699**, action-3 numerator **2.535.710**, denied share mô tả **20,6479%**. Giữ nguyên publisher caveat: release có hơn 12 tháng updates và không phải cutoff chuẩn 12 tháng.
- Action-3 denial-reason JSON khớp chính xác private aggregate; Excel KPI/codebook/source-audit tải từ route byte-identical với workbook private đã receipt-bind; viewport 390px không overflow.
- 2019 là application/decision data, không có repayment/default target. Không forecast, impute, hoặc ghép thành performance panel. Receipt, downloaded artifacts và screenshot chỉ nằm trên D:, `public_release_approved=false`.
- HMDA browser acceptance hiện ghi nhận **21 national + 4 Three-Year 2018 + 4 One-Year 2019 + 17 legacy = 46 checks**. Native Excel cho toàn bộ chín workbook HMDA được ghi ở mục follow-up bên dưới. Release comparability/rights review vẫn mở; capability ledger giữ **26/50 = 52%**.

### HMDA browser acceptance trên current checkout — 17/10/2026

- Rerun trên `app.js` hiện tại: national **21/21**, Three-Year 2018 **4/4**, One-Year 2019 **4/4**, legacy cohort/reference **17/17**; tổng **46 checks**, 0 page/console errors. Bốn receipt đều hash-match `app.js` hiện tại; 2018 và legacy receipts còn bind stylesheet, legacy receipt bind cả server/module paths.
- Sửa legacy QA harness để ưu tiên `src/` của checkout thay vì bản package cũ trong private virtualenv; receipt giờ hash đúng `web_root` và code trong repo. 2018 harness bổ sung hash app/CSS/QA script. Đã rerun sau sửa.
- HMDA source/view/API/cohort tests: **146 passed** với pytest basetemp trên D:. Không đổi action denominator, không forecast và không nâng capability ledger.
- Browser QA xác nhận behavior của module/filters/exports đã test; HMDA vẫn là application/decision data, chưa có repayment/default target. Release comparability và rights review còn mở. Evidence summary: [current HMDA browser QA](data/hmda-current-browser-qa-2026-10-17.json).

### Native Excel acceptance HMDA — 17/10/2026

- Microsoft Excel desktop **16.0** đã mở read-only và chạy `CalculateFullRebuild()` cho cả chín workbook tải qua app: 2025 National Snapshot, 2025 Dynamic, 2018 Three-Year và One-Year 2019–2024.
- **9/9 PASS; 177 công thức; 0 formula errors; 0 external links.** Mỗi bản tải khớp byte với workbook nguồn receipt-bound; macros bị tắt, external link updates bị tắt, đóng mà không lưu và hash file sau khi đóng không đổi.
- Số sheet/công thức theo release: Snapshot 7/69; Dynamic 5/26; 2018 Three-Year 5/10; 2019 8/12; 2020 8/12; 2021 8/12; 2022 8/12; 2023 8/12; 2024 7/12.
- Bằng chứng sanitized: [HMDA native Excel QA](data/hmda-native-excel-qa-2026-10-17.json). Receipt/hash đầy đủ ở private workspace; không phát hành workbook hoặc loan-level rows.
- Đây là nghiệm thu file export của chín release hiện có, không chứng minh mọi filter/query, reuse rights, cross-release comparability hay credit-performance labels. Không forecast; capability ledger vẫn **26/50 = 52%**.

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

N09 verification: `tests/test_absee_surveillance.py` và `tests/test_http_boundary.py` chạy với basetemp trên D: cho **20 passed, 5 skipped**; các test mới về hash/summary/filters/API/report/XLSX đều pass. Năm skip thuộc fixtures cần machine-local/private inputs. Workbook N09 recalculates 103/3/86/83 và từng deal; Summary và Analyst finding được render để QA. N14: hai test label/calendar boundary pass; full source audit khớp SHA, rows/columns/labels và tạo private aggregate report; workbook formulas reconcile 789,144 / 86,618 / 520,246 / 182,280. `node --check`, Python compile, JSON parse và `git diff --check` được kiểm tra trước publish. N06 New/Outstanding Edge acceptance pass 8 checks, PUDB 5 checks, HMDA current-code browser QA pass 46 checks and native Excel pass for all nine HMDA release-bound workbooks; native Excel and route/source acceptance for PUDB, NMDB query combinations, HUD and HAMP remain open. N01–N03 cũng chưa được nghiệm thu cuối. Lượt trước có public regression 1.670 passed/196 skipped trước các thay đổi này; kết quả đó không thay cho test mới.

## Bước kế tiếp

1. Hoàn tất native Excel cho query-scoped N06, PUDB, HUD và HAMP exports; tiếp tục trace KPI N03 còn thiếu, cùng release comparability/rights cho HMDA và browser/query parity cho các route NMDB khác.
2. Hoàn thiện N02 theo crosswalk mới: tách source families đang thiếu record, bind mọi release/hash receipt và kiểm tra source rights/date-grain cho từng KPI.
3. Nối KPI outputs vào method cards, gồm numerator/denominator, data release/as-of, formula và missingness; giữ các score/final holdout đã freeze nguyên trạng.
4. Chuyển sang N10: chuẩn bị pilot Freddie annual sample và kiểm tra quyền truy cập, receipt/hash, release/layout, parser counts và resource budget khi Clarity session hợp lệ có sẵn. Không giả lập sample chưa tải.
