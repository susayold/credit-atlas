# Treasury daily par-yield curve trực tiếp — nghiên cứu nguồn và nghiệm thu P5

Ngày rà soát nguồn: **18/10/2026**. Snapshot tải trực tiếp lúc **2026-10-17 21:37 UTC**, dữ liệu thị trường cuối ngày đến **2026-10-16**. Phạm vi là các tenor Treasury constant-maturity 2Y, 10Y và 30Y dùng làm bối cảnh lãi suất trong P5; đây không phải nghiên cứu hay xác nhận mô hình PD.

## Quyết định nguồn

P5 hiện dùng Treasury trực tiếp từ **1990-01-02** trở đi. Snapshot FRED DGS2/DGS10/DGS30 chỉ làm phần mở rộng lịch sử trước ngày đó và comparator; giá trị sau mốc 1990 của FRED không được lấy vào case mới. Việc tách mốc này bảo toàn lịch sử dài hơn của FRED nhưng ưu tiên publisher trực tiếp trên vùng mà Treasury archive có dữ liệu. Tất cả dòng đều giữ `source_id` và SHA-256 nguồn trong facts/API report.

Giá trị Treasury giữ nguyên ở ngày nguồn và đơn vị phần trăm. Không resample, không nội suy, không lấp ngày thiếu, không lấy 20Y để tạo 30Y, và không forecast. Case/view P5 riêng tư mới đã được dựng từ receipt Treasury này cùng public-suite comparator hiện có.

## Treasury đang đo điều gì?

Treasury gọi chuỗi này là **Daily Treasury Par Yield Curve Rates**. Đầu vào là báo giá bid-side mang tính indicative cho các Treasury mới đấu giá nhất trên thị trường OTC; báo giá do Federal Reserve Bank of New York thu thập khoảng 3:30 chiều mỗi ngày làm việc. Đây là par yield trên một đường cong lý thuyết, không phải giá giao dịch thực tế hay yield của một chứng khoán cụ thể. [Treasury Interest Rate Statistics](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics)

FAQ của Treasury nói constant-maturity (CMT) được đọc tại các điểm kỳ hạn cố định trên đường cong. CMT có thể khác yield của từng trái phiếu còn lưu hành; yield được báo theo bond-equivalent basis với coupon giả định trả nửa năm, không phải APY hay zero-coupon discount curve. Vì vậy P5 chỉ dùng nó làm bối cảnh và tính chênh lệch tenor cùng ngày; hiện không dùng làm quote để định giá một ABS cụ thể. [Treasury Interest Rates FAQ](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions)

Treasury đổi cách dựng đường cong từ quasi-cubic Hermite spline sang monotone-convex vào **06/12/2021**. Input hiện gồm báo giá bid cho các bill/note/bond mới đấu giá; Treasury không công bố computer formulation và bảo lưu quyền thay đổi input hoặc phương pháp. Snapshot hiện tại vì vậy là bản latest-revised, không cung cấp cho app lịch sử chính xác giá trị đã thấy tại ngày ra quyết định. [Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology)

## Nguồn tải và dữ liệu đã nhận

Trang Treasury Archives cung cấp CSV par-yield tổng hợp cho **1990–2023**. Trang Daily Treasury Rates cho phép tải CSV theo năm; lượt này dùng các phân vùng **2024, 2025 và 2026**. [Treasury Daily Rate Archives](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives), [Daily Treasury Rates 2026](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?field_tdr_date_value=2026&type=daily_treasury_yield_curve)

| Phân vùng nguồn | Dòng ngày-native | Ngày đầu | Ngày cuối | Blank cells ở 2Y/10Y/30Y |
|---|---:|---|---|---:|
| 1990–2023 | 8.507 | 1990-01-02 | 2023-12-29 | 997 |
| 2024 | 250 | 2024-01-02 | 2024-12-31 | 0 |
| 2025 | 249 | 2025-01-02 | 2025-12-31 | 0 |
| 2026 | 199 | 2026-01-02 | 2026-10-16 | 0 |
| **Tổng** | **9.205** | **1990-01-02** | **2026-10-16** | **997** |

Các blank gồm 994 ngày nguồn 30Y trong giai đoạn Treasury ngừng công bố và ngày 2010-10-11 bị trống ở cả ba tenor. Hai tenor 2Y/10Y mỗi tenor thiếu đúng ngày chung 2010-10-11; không thay bằng ngày lân cận.

## Đối chiếu với snapshot FRED

FRED comparator trong workspace hiện dừng ở **2026-10-06**; Treasury trực tiếp có thêm bảy ngày thị trường đến 2026-10-16. Kết quả được so sánh bằng Decimal trên cùng ngày có giá trị ở cả hai nguồn:

- 2Y: **9.197/9.197** giá trị trùng tuyệt đối; không có mismatch.
- 10Y: **9.197/9.197** giá trị trùng tuyệt đối; không có mismatch.
- 30Y: **8.203/8.203** giá trị quan sát được trùng tuyệt đối; không có mismatch. Ở **994** ngày trong discontinuation window, Treasury trực tiếp để trống trong khi FRED có giá trị; P5 mới không dùng các giá trị FRED đó. Một ngày còn lại, 2010-10-11, cả hai nguồn đều thiếu.

Đây là bằng chứng snapshot parity trên các kỳ có giá trị ở cả hai nguồn; không chứng minh lịch sử vintage, quyền giữ/redistribute dữ liệu FRED, hay feature qualification. Treasury official page nêu 30-year constant-maturity series bị dừng ngày **18/02/2002** và mở lại **09/02/2006**. Trong thời gian đó Treasury công bố hệ số để ước tính từ 20Y; P5 giữ 30Y là missing thay vì tự áp dụng hệ số. [Treasury Interest Rate Statistics](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics)

## Tích hợp P5 và cách đọc số

Receipt hiện hành: `local-private-id:treasury-par-yield-20261017T213708Z-ac15a82d`. P5 case/view mới nhất được ghi ngay bên dưới, đã kiểm tra hash/input lineage và lưu riêng tư.

Case mới nhất là `market-case-85942aa82d1a`; view `market-view-8af362feebc9` có trạng thái `VERIFIED_MARKET_CONTEXT`, receipt/hash/methods được bind và lưu riêng tư. Case có **45.517 native facts** trên năm series và **16.555** ngày ở bảng aligned. Ba tenor Treasury/FRED lịch sử có source switch được khai báo; ICE OAS và Freddie PMMS vẫn giữ nguồn/điều kiện sử dụng riêng. Treasury direct làm ngày mới nhất của 2Y/10Y/30Y thành 2026-10-16; OAS qua FRED vẫn đến 2026-10-07 và PMMS qua FRED đến 2026-10-08. Mốc ngày mới nhất của một chuỗi không được dùng để giả định các chuỗi khác cũng đã cập nhật.

| Chuỗi | Dòng | Giá trị dùng được | Missing | Ngày cuối có giá trị | Cuối kỳ (%) |
|---|---:|---:|---|---|---:|
| DGS2 / Treasury 2Y | 12.750 | 12.591 | 159 | 2026-10-16 | 4.74 |
| DGS10 / Treasury 10Y | 16.510 | 16.183 | 327 | 2026-10-16 | 5.09 |
| DGS30 / Treasury 30Y | 12.565 | 11.419 | 1.146 | 2026-10-16 | 5.43 |

Các hàng missing bao gồm ngày không có quote cùng những mốc native của phần lịch sử FRED; chúng không phải số được ước tính. P5 chỉ tính 10Y–2Y hoặc 30Y–10Y khi cả hai tenor cùng ngày đều usable. Trạng thái `historical_treasury_semantics_qualified` vẫn false; đây là context mô tả, không phải calibrated rate model, spread curve, security price, credit PD, LGD hay ECL.

## Quyền sử dụng và giới hạn phát hành

Các trang Treasury đã rà soát cung cấp dữ liệu/CSV công khai và methodology, nhưng không tìm thấy grant riêng cho phép dự án rehost toàn bộ raw dataset. Vì vậy bốn CSV gốc, normalized panel, receipts và output vẫn nằm trong D: private workspace; repo công khai chỉ chứa downloader, parser, source metadata và hash prefix. Không công bố raw Treasury, FRED, ICE hoặc Freddie Mac data từ tranche này. Quyền sử dụng công khai của BLS/FHFA không tự mở quyền cho các nguồn còn lại.

Dữ liệu là snapshot latest-revised, không có release-time vintage; không thích hợp để dựng lại thông tin sẵn có tại ngày cấp khoản vay. Không chạy model fit hoặc backtest trong tranche này. Muốn dùng làm feature phải bổ sung vintages/PIT, intended-use review, time-ordered validation, incremental predictive value, calibration, subgroup stability và stress/sensitivity.

## Code, kiểm tra và việc còn mở

`scripts/acquire_treasury_par_yields.py` tải CSV chính thức theo phân vùng, kiểm HTTPS host, kích thước, schema, khoảng ngày, trùng ngày, kiểu/range yield, missingness, hash và so sánh với FRED. `scripts/prepare_market.py --treasury-run ...` dựng source switch tại 1990-01-02; mỗi row trong Parquet và `/api/market-report` giữ `source_id`/`source_sha256`. UI báo vai trò source legs cùng khoảng ngày.

Bộ test parser/P5 **38/38 pass**; project-register API/runtime acceptance **13 checks pass** trên register 30 groups/129 source records. Full P5 Edge workflow acceptance **13/13 pass** trên view trực tiếp mới, gồm source parity/role, OAS Sunday observation, Treasury discontinuation gap, bond scenario/export, URL reload, mobile, navigation và no-run behavior. Direct Treasury-specific browser/export smoke **5/5 pass**, kiểm tra source label/role, date filter, JSON/API equality, row-level source id/hash/private flag, 390px overflow và browser errors. Private receipts: `market-browser-qa-fa1573a93a95` và `treasury-browser-qa-38a5e574809a`. Recurring refresh acceptance, rights đối với raw rehosting, ICE/PMMS rights, model calibration và meaning/qualification của 30Y còn mở; không phần nào được coi là capability đã hoàn tất chỉ vì source đã tải.
