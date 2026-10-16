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

### N03 — provenance và phương pháp

- Ghi nhận bảy loại giá trị: reported, derived, publisher-imputed, model-preprocessing-imputed, model prediction, declared scenario và forecast.
- Registry hiện có mười một method cards gắn dataset, target, cách tính/protocol, validation đã lưu, giới hạn và model/data evidence. Các card bao gồm D01 transitions, UCI350, UCI365, NMDB, HMDA fixed-mix, P4 scenario/ECL và Toyota/Nissan/structured ABS reconciliation.
- Các giả định P4 hiển thị đúng scope illustrative: lịch bullet 36 tháng, monthly EIR 0,004, weights 0,7/0,3; source expected loss vẫn unavailable. Không tạo biến dự phóng mới.
- N03 vẫn đang làm: mọi KPI/output số trên toàn app chưa được liên kết tới method ID và input lineage ngay trong view.

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
- N05/N06 chưa đóng acceptance tổng: API và download đã có smoke check runtime ngày 17/10; browser acceptance và mở workbook trong Excel desktop vẫn còn mở. Không tăng completion 26/50 chỉ vì thêm implementation.

### Runtime review N05/N06 — 17/10/2026

- Catalog runtime trả đúng 3.038.100 New annual / 60 series / 27 markets và 535.464 Outstanding quarterly / 37 series / 4 markets.
- New National / USA / All Mortgages, `AVE_INTRATE`, VALUE1 trả 28 năm 1998–2025; giá trị cuối 2025 là 6,3% theo source scale. Outstanding `AVE_MTMLTV`, VALUE2 trả 54 quý đến 2026Q2; giá trị cuối là 54,2%.
- VALUE2 cho Outstanding `TOT_UPB` bị từ chối HTTP 400 theo quy tắc VALUE1-only của FHFA.
- Query-scoped Excel export cho New annual và Outstanding quarterly đều trả HTTP 200. Đã đọc cấu trúc XLSX: bốn sheet; biểu đồ bind cột `Selected value` và nhãn kỳ dạng text, không che bảng dữ liệu. Workbook tham chiếu tải qua route HTTP 200, 389.862 bytes.
- Đây là runtime/API/export check; chưa thay thế browser visual acceptance hay Excel desktop open/recalculate review.

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

## Giao diện

Trang **Tiến độ & registry** trong điều hướng chung hiển thị capability acceptance, D01 releases, dataset filters, quyền truy cập, method cards và giới hạn. Register JSON có thể tải xuống. Không đưa raw borrower rows hoặc private exposure values vào catalog.

Workbook plan ở `docs/reviews/` đã cập nhật trạng thái N01–N03 thành **Đang làm** và ghi cụ thể phần còn lại; không đổi tỷ lệ acceptance 26/50.

## Trạng thái kiểm tra

N09 verification: `tests/test_absee_surveillance.py` và `tests/test_http_boundary.py` chạy với basetemp trên D: cho **20 passed, 5 skipped**; các test mới về hash/summary/filters/API/report/XLSX đều pass. Năm skip thuộc fixtures cần machine-local/private inputs. Workbook builder recalculates và kiểm tra 103/3/86/83 cùng từng deal; Summary và Analyst finding đã render để QA. Node/Python/JSON syntax và `git diff --check` được kiểm tra trước publish. Đây chưa phải mở/recalculate bằng Microsoft Excel desktop. Browser/native Excel acceptance riêng của N06 vẫn mở. N01–N03 cũng chưa được nghiệm thu cuối. Lượt trước có public regression 1.670 passed/196 skipped trước thay đổi này; kết quả đó không thay cho test mới.

## Bước kế tiếp

1. Browser review N06 và Excel desktop open/recalculate; xác nhận bộ lọc, chart, bảng, missingness và lineage hiển thị đúng.
2. Mở rộng N02 từ 24 nhóm trọng tâm tới nguồn thực sự cấp dữ liệu cho mỗi KPI, bind release/hash receipt khi có.
3. Nối KPI outputs vào method cards, gồm numerator/denominator, data release/as-of, formula và missingness; giữ các score/final holdout đã freeze nguyên trạng.
4. Chuyển sang N10: chuẩn bị pilot Freddie annual sample và kiểm tra quyền truy cập, receipt/hash, release/layout, parser counts và resource budget khi Clarity session hợp lệ có sẵn. Không giả lập sample chưa tải.
