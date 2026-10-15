# D01/R2 — rà soát nguồn mortgage performance và khoảng trống vintage

**Đối chiếu:** 16/10/2026.  
**Mục tiêu:** xác định data nào thực sự giúp D01 (Freddie residential mortgage
lifecycle), data nào chỉ hỗ trợ case khác hoặc bối cảnh aggregate, và bước thu
thập tiếp theo theo M01-005/006. Tài liệu không thay thế điều khoản của nguồn.

## Kết luận cho quyết định dữ liệu

Hiện chưa có thêm Freddie annual loan-performance sample nào được tải. Nguồn
chính thức xác nhận Freddie có khoảng 56 triệu mortgages, origination từ 1999
đến 31/03/2026 và monthly performance đến 31/03/2026; tuy nhiên full dataset,
annual-by-year files và sample files đều tải qua Clarity sau khi đăng ký/đăng
nhập. Đây vẫn là đường duy nhất khớp trực tiếp population, frequency, schema
và target contract của D01.

Không tìm thấy public replacement cùng contract. Các dữ liệu đã thu thập như
NSMO, NMDB aggregate, HUD performance, FHFA HPI/PUDB và HMDA đều có giá trị
cho case hoặc context riêng, nhưng không tạo thành Freddie annual vintage.
Ginnie và Fannie có loan-level performance phù hợp cho case song song/external
validation, song đều có access/terms gate và không được pool vào Freddie.

## Source fit và tình trạng tại checkpoint

| Nguồn | Grain / coverage hiện được công bố | Dùng cho module nào | Tình trạng / tác động lên D01 |
|---|---|---|---|
| Freddie Mac SFLLD | Loan-level origination + monthly servicing/performance; mortgages mua/bảo lãnh từ 1999, performance đến 31/03/2026; Standard và Non-Standard | **D01/R2 chính** | Clarity yêu cầu đăng ký/đăng nhập. Code downloader, manifest và local import đã có; chưa nhận authenticated URL/cookie nên số vintage bổ sung tải được là 0. Release 47 public examples/layout dùng để kiểm tra parser, không phải annual sample. |
| Fannie Mae Single-Family Performance | Primary fixed-rate subset và HARP; bản cập nhật 31/07/2026 có acquisition/performance Q1 2026 | Case parallel hoặc external validation sau harmonization | Data Dynamics yêu cầu account, email verification và chấp nhận Terms; external redistribution/commercial use cần thỏa thuận. Chưa có full panel; public samples chỉ là setup/parser material. Đã tạo hai workbook private D: — sample Excel (757 SF, 241 MF, 17 annual DSCR records; giá trị khớp CSV) và schema Excel (114 SF, 62 MF, 3 annual DSCR fields, 45 raw enum blocks). Không thêm Freddie vintage. |
| FHFA/CFPB NSMO PUF v7.0 | 62.359 sample mortgages, origination 2013–2024; 51 quý performance đến 2025Q3; survey/response process riêng | **D02 riêng**, descriptive/target-feasibility; có thể xem xét delayed-entry study sau protocol | Đã tải và audit riêng sau khi user chấp thuận Notice/Terms. Feasibility trên PUF cho thấy origination-aligned 90+ support quá mỏng để biện minh model đa biến; không pool hay đổi tên thành Freddie. |
| Ginnie Mae Loan Performance | Loan-per-quarter/loan-per-year cho MBS; catalog ghi quarterly `LoanPerf_202606.zip` 782.688.297 bytes và annual `LoanPerfAnn_202512.zip` 2.302.624.988 bytes | Ginnie MBS case riêng; lifecycle và exposure của active pools | User đã xác nhận chấp thuận Terms; sample/layout auditors, authenticated downloader và Excel reference cho LoanPerf, liquidation, payment history (59+7, 15+6, 5+26 field records), code values và ba sample-QA tab đã sẵn sàng trong private D:. Workbook không chứa loan-level rows/keys. Production endpoint cần phiên user hợp lệ (`gm_up_token` và profile validation); HTTP 401 không xác nhận file đã tải. Chờ đường dẫn Netscape cookie trên D:. Không thay M01-005 Freddie. |
| FHFA NMDB Aggregate Statistics | Quarterly geographic/market aggregate; release 30/09/2026 có performance đến 2026Q2; bối cảnh đại diện từ NMDB 5% sample | Market/macro context cho D01/D02 | Đã tải national/state; series theo geography/market, không có loan IDs hoặc monthly event paths. Không dùng làm D01 row/target/annual vintage. |
| CFPB Mortgage Performance Trends | Monthly delinquency series từ 2008-01 đến 2025-12 theo national/state/county/metro | External market context | Đã tải bốn CSV và tích hợp panel. Nguồn dùng NMDB; có missing/imputation/revision và emergency-reporting semantics. Aggregate benchmark, không phải independent borrower panel. |
| FHFA Enterprise PUDB | Annual single-family acquisition/origination loan-level records; 2025 Census Tract pilot 2.093.767 records | Credit-access/acquisition mix, không phải D01 servicing | Đã tải và đối chiếu record counts. Không có monthly repayment performance hoặc denial/applicant denominator hoàn chỉnh; không train D01. |
| HMDA LAR | Application/origination decision records theo năm; public fields đã sửa đổi để bảo vệ privacy | D08/origination-market analysis | Có thể phân tích approve/deny/product/channel; không có monthly post-booking payment history. Không join identity với Freddie khi không có khóa/link được cấp phép. |
| HUD FHA Single-Family Performance Trends | Portfolio-level monthly report tables; index liệt kê đến 08/2026, gồm delinquency, foreclosure, claims và REO recovery/loss | FHA aggregate benchmark / D02 context | Tables 1–6 đã được transcribe từ official report text và tích hợp riêng. Raw PDF trả 403; đây không phải loan-level panel và không được ghi nhận như binary acquisition. |
| HUD FHA Insurance-in-Force / Portfolio Snapshot | Tract-level active FHA exposure hoặc loan origination attributes, tùy release | Exposure/concentration hoặc acquisition context | Tract aggregate đã tải riêng; snapshot XLSX bị 403. Không có chuỗi monthly performance borrower-level. |
| FHFA NMDB underlying loan file | FHFA mô tả NMDB là de-identified 5% sample với servicing history; trang public tải là **aggregate statistics**, còn NSMO là PUF riêng | Có thể là source mới nếu FHFA xác nhận một quy trình cấp data/terms phù hợp | Chưa thấy direct public loan-level download/permission path trong official data index. Không giả định aggregate page cấp quyền truy cập toàn bộ NMDB; chỉ hỏi FHFA qua contact công bố nếu cần theo đuổi riêng. |
| Fannie Mae Multifamily | Multifamily loan performance/annual DSCR files; cadence và population thương mại đa gia đình | D09 / P2 CRE riêng | Data Dynamics và Terms áp dụng; không tương thích residential D01. |

## Vì sao các nguồn đã thu thập không đóng được M01-006

- **M01-006 yêu cầu nhiều Freddie annual samples** để đối chiếu khóa, fanout,
  row grain, layout, enum/sentinel và availability theo vintage. Chỉ 2012
  Freddie là corpus đã chạy pipeline trong D01.
- NSMO có performance theo quý và sample/response/weight/censoring riêng.
  Kết quả của nó có thể phục vụ D02, nhưng trộn với Freddie sẽ tạo một
  population/observation contract khác.
- Ginnie có active-pool selection, monthly history/status codes và removal
  semantics riêng; nếu tải được, phải đưa vào case riêng trước khi so sánh.
- Fannie có acquisition/performance và phù hợp external validation về mặt
  nội dung, nhưng sampling, field definitions, terms và access cần audit riêng.
- HPI, NMDB aggregate, HUD tables, PUDB và HMDA không có định danh/chuỗi
  borrower-performance cần thiết để tạo observed outcome ở grain loan-month.

## Thu thập tiếp theo theo plan

1. **Freddie D01:** dùng Clarity sau khi user cung cấp đường dẫn phiên/manifest
   gồm URL tải official cho annual files. Pilot một vintage khác trước khi
   batch; năm pilot nên chốt theo coverage/maturity và ý đồ split trong protocol,
   không chọn theo kết quả tốt. Downloader hiện giới hạn URL official HTTPS,
   Release 47, ZIP/member names, kích thước và headroom D:. Sau archive check,
   tiếp tục parse/schema/population qualification; chưa tự động đăng ký vintage
   vào model panel.
2. **Ginnie case song song:** sau khi có cookie path, tải một quarterly pilot
   2026Q2 trước (nhỏ hơn annual 2025), kiểm tra profile endpoint, receipt/hash,
   HH/LP/TT counts, disclosure key uniqueness, frequency/status histories và
   footprint. Chỉ sau pilot mới cân nhắc annual file hoặc LL payment-history
   product; không join các files chỉ vì identifier có vẻ giống nhau.
3. **Fannie:** chỉ bắt đầu full panel sau khi user tạo account/được chấp thuận,
   đọc Terms và chấp nhận giới hạn dùng. Bắt đầu bằng sample/layout audit, rồi
   tách mapping/crosswalk và acquisition schema khỏi Freddie.
4. **NMDB underlying:** chưa tải hay xin data thay user. Giữ aggregate trong
   context; nếu cần loan-level NMDB ngoài NSMO, gửi inquiry tới contact chính
   thức của FHFA và chờ access/terms rõ ràng trước khi dự tính pipeline.

Không tải thêm aggregate chỉ để tăng số file: các context chính đã có và không
giải quyết gate loan-level. Không fit D01 model trong lúc M01-005/006,
M01-015 và protocol chưa đạt.

## Nguồn chính thức đã đối chiếu

- [Freddie Mac SFLLD: phạm vi 1999–2026, coverage đến 31/03/2026, Clarity access và terms](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
- [Fannie Mae Single-Family Loan Performance: release Q1 2026, subset và registration/terms](https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data)
- [Fannie Mae legal disclosure: internal use, redistribution và external commercial use](https://www.fanniemae.com/about-us/legal-disclosure)
- [FHFA NSMO PUF: v7.0, 62.359 loans, 2013–2024 origination, 2025Q3 performance, Notice/Terms](https://www.fhfa.gov/data/nsmo)
- [FHFA NMDB Aggregate Statistics: 2026Q2 performance, release 30/09/2026](https://www.fhfa.gov/data/nmdb)
- [FHFA NMDB program: purpose, underlying 5% mortgage sample and servicing scope](https://www.fhfa.gov/programs/nmdb)
- [CFPB Mortgage Performance Trends: NMDB lineage, monthly geography CSVs, imputations/revisions](https://www.consumerfinance.gov/data-research/mortgage-performance-trends/about-the-data/)
- [FHFA Enterprise PUDB](https://www.fhfa.gov/data/pudb)
- [CFPB HMDA](https://www.consumerfinance.gov/data-research/hmda/)
- [Ginnie Mae official bulk disclosure catalog](https://bulk.ginniemae.gov/)
- [HUD FHA Single-Family Loan Performance Trends](https://www.hud.gov/hud-partners/single-family-loan-performance)
