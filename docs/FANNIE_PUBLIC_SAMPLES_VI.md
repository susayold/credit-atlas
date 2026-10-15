# Fannie Mae — public samples, coverage và giới hạn model

Checkpoint 12/10/2026. Acquisition bằng HTTP/curl, không đăng nhập và không computer use. Tải **7 files / 1.217.459 bytes**: hai trang index chính thức, ba sample và hai glossary PDF. Dữ liệu đầy đủ của Data Dynamics vẫn cần đăng ký/terms; sample được nhà phát hành cung cấp để thiết lập database.

## Nguồn đã tải và kết quả kiểm tra

| Nguồn | Records | Fields | Source loan IDs riêng | Kỳ quan sát |
|---|---:|---:|---:|---|
|Single-Family sample|757|108|8|Reporting 07/2009–06/2020; candidate origination 07–09/2009|
|Multifamily main sample|241|62|4|Reporting 11/2004–12/2018; acquisition 17/11/2004–31/01/2018|
|Multifamily annual DSCR sample|17|3|4|Fiscal years 2007–2020, coverage không liên tục cho mọi loan/year|

Source positions: **96.749**; field quality profiles: **173**. Loan-month records không là số khách hàng độc lập. Không cộng unique IDs từ hai family để tuyên bố đã có borrower population thống nhất.

Single-Family dùng pipe-delimited, không header. Profile giữ raw positional field names. Candidate field 2/3/14/40/44 đối chiếu với glossary hiện tại cho loan identifier, reporting period, origination date, delinquency và zero balance; **chưa qualified toàn schema/phiên bản sample**. Có 4 raw `XX` delinquency rows; không chuyển unknown thành Current. Zero-balance candidates: blank 752, code01 3, code06 1, code09 1. Không tạo nhãn default hay PD12 từ số lượng này.

Multifamily có CSV headers. Có 231 Current, 1 dòng 30–59 days, 1 dòng 60–89 days và 8 dòng 90+ days; đây là counts trên loan-month, không phải independent default counts. Source header ` Affordable Housing Type` có leading space được giữ nguyên trong raw quality table.

Annual DSCR có 17 giá trị reported, min **1,13x**, max **2,68x**, không dòng nào dưới 1x trong sample. Thiếu NCF/debt-service amounts nên **không recompute ratio**. Bốn source IDs overlap giữa main/annual file, không có orphan ID tại sample. Không join annual ratio sang mọi monthly row: khác grain, periods/cutoffs và credit-facility ratios có thể ở cấp deal. Không so với covenant threshold để tuyên bố compliant.

## Glossary và schema drift

Hai PDF đều 11 pages, đã extract riêng 22 pages mà không sửa nguồn. Selected visual review: Single-Family page2, Multifamily page11. PDF Single-Family ghi 10/09/2026; page2 nêu borrower credit-score field24 ngừng populate từ activity March2026, tham chiếu field111. Sample chỉ có108 positions và reporting kết thúc2020; không áp schema hiện tại vào sample một cách tự động.

Multifamily glossary March2023, pages10–11 định nghĩa annual DSCR theo NCF/debt service và caveat credit facilities ở deal-level. Ngày glossary và kỳ dữ liệu khác nhau; file downloaded hôm nay không chứng minh historical publication availability.

Nguồn chính thức:

- [Single-Family data và public sample](https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data).
- [Single-Family glossary](https://capitalmarkets.fanniemae.com/resources/file/credit-risk/pdf/crt-file-layout-and-glossary.pdf), pages1–4 cho candidate positions và page2 cho credit-score change.
- [Multifamily data và public samples](https://capitalmarkets.fanniemae.com/credit-risk-transfer/multifamily-loan-performance-data).
- [Multifamily glossary](https://capitalmarkets.fanniemae.com/resources/file/credit-risk/pdf/mflpd-glossary-file-layout.pdf), pages10–11 cho annual DSCR.

## App và export

Vào **Mortgage → Chất lượng**, dưới quality monitoring của Freddie là card **Fannie Mae public format samples**. Chọn all / Single-Family / Multifamily + annual DSCR; xem file-grain counts, reporting window, source status counts, field blanks/literal tokens và qualification gates. Family filter chỉ lọc nguồn Fannie, không thay Freddie run/segment. Family choice hiện chưa persist URL.

GET `/api/fannie-samples?family=all|single-family|multifamily`; GET `/api/fannie-samples-report` cùng filter xuất private JSON. Request verify profile, acquisition receipt và cả bảy file hashes. Export không chứa source loan IDs/record-level panel. Outage xóa result/export cũ ở source card; frozen Freddie quality vẫn giữ scope riêng.

## Evidence

- Source `data/private/mortgage/fannie-public-samples-4d84128d3cb6/acquisition-complete.json`, SHA `860dcf9ea0bc879977dc854f23d424c869e2783fd30dc9f36695939533429124`.
- Profile `artifacts/private/fannie-public-profile-fafc20762187/profile.json`, SHA `e2575f225eeffc6d99beee07f5165c1b3a7c1a34e85d3c09f1f5d2c2ebed128e`.
- Independent DuckDB `fannie-public-audit-b518c8fa1c6a/receipt.json`: **1.015 rows / 96.749 positions / 173 field missingness checks PASS**, categories, duplicate key support và DSCR summaries khớp. Frozen retail ledger không đổi.
- `fannie-samples-http-tests-20261012-final.xml`: **27 PASS** gồm Fannie source/API và HTTP regression. Lần đầu LendingClub hash IO vượt socket5seconds; test helper cho riêng full-source route budget30seconds vì hash~650MB, ordinary routes giữ5seconds. Không thay source/hash verification hoặc kỳ vọng response.
- Browser `fannie-samples-qa-a19e7e45fbf4/receipt.json`: **4 nhóm PASS**, source/export parity; family/status/DSCR/quality scopes; mobile; outage/retry. Ledger không đổi, không page errors.
- Layout extraction/render `fannie-layout-review-4b869d32d31e/receipt.json`: hai PDF/22 pages, selected rendered pages nêu trên. Không là full schema qualification.

Lần profile đầu từ chối trailing blank CSV record trong annual DSCR; parser đã tách blank physical record count (=1) khỏi17 financial rows. Không xóa source file, không biến blank thành zero; profile mới có receipt/hash riêng.

## Tác động tới plan và phần còn thiếu

Nguồn bổ sung giúp adapter/source quality và case Multifamily; **không giải quyết R2/R3 của Freddie Mortgage PD12**. Added Freddie annual vintages =0. Không fit/refit, không mở final-test predictors và không nhập các Fannie IDs vào frozen D01.

P2.01/P2.02 có thêm partial evidence, P2.08 vẫn cần qualified annual samples. Còn full dataset access, source-version/schema compatibility, representative multi-vintage support, horizon maturity, entity-safe temporal split, model/calibration/OOT. P3/C4 không được đánh dấu hoàn thành từ reported DSCR sample vì thiếu numerator/denominator và actual effective covenant terms. Tất cả50capability states giữ nguyên.
