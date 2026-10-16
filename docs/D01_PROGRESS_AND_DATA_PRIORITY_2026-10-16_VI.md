# D01 — tiến độ so với plan và ưu tiên dữ liệu

**Checkpoint:** 16/10/2026. Đây là trạng thái theo bằng chứng có thể kiểm tra,
không phải ước lượng thời gian đã bỏ ra.

**Bổ sung dữ liệu HMDA 2024 trong ngày:** đã tải và đối soát file national
One-Year 12.259.199 dòng/99 trường, 4.926 LEI; chi tiết và hash tại
[`HMDA_NATIONAL_ONE_YEAR_2024_REVIEW_VI.md`](HMDA_NATIONAL_ONE_YEAR_2024_REVIEW_VI.md).
Đây là hồ sơ application/decision riêng cho D08, không phải payment/performance
panel và không làm tăng % D01 bên dưới.

Đã tích hợp aggregate view riêng vào app và tạo workbook Excel riêng 7 sheet
(không nhét 12,26 triệu dòng vượt giới hạn Excel). Browser acceptance cho cả
Snapshot 2025 và One-Year 2024 **PASS, 8 checks, zero errors**, gồm breakdown,
JSON/Excel download và mobile width; bằng chứng private tại
`D:\data\Codex\credit-atlas\artifacts\private\hmda-national-browser-qa-6f761518ddc3\receipt.json`.
Bước data kế tiếp là lấy One-Year 2023 để tạo so sánh cùng release family. Tỷ lệ
D01 vẫn 26/50 vì HMDA không đáp ứng gate performance R2/R3.

## Tiến độ tổng thể

CreditAtlas hiện hoàn thành **26/50 yêu cầu = 52%** theo completion ledger;
**42/50 = 84%** có ít nhất implementation hoặc conditional coverage. Hai tỷ lệ
này đếm yêu cầu, không đo effort, độ sẵn sàng production hay phần trăm mô hình.
Yêu cầu Partial không được tính là Complete. Chi tiết trạng thái từng yêu cầu ở
[`BACKLOG_STATUS.md`](BACKLOG_STATUS.md).

Trong phạm vi **D01 — Residential Mortgage Lifecycle & Loss Lab**, trạng thái
theo từng release như sau:

| Release | Kết quả so với Definition of Done | Phần đã có | Phần còn thiếu / gate |
|---|---|---|---|
| R0 — foundation | Partial | Engine pin; rebuild 2012 50.000 loans / 4.510.559 loan-months; semantic audit trên corpus; reproduction, tests và runtime evidence | Dependency/resource sign-off cuối; license/distribution terms cho engine và package audit cuối |
| R1 — descriptive | **Đạt cho frozen Freddie 2012 sample** | Source/DQ, portfolio/profile, timeline, transitions, episodes, competing outcomes, observed-loss bridge, denominators/support, findings save/reopen, scoped descriptive export, reproduction và real-data browser QA | Không bao gồm multi-vintage so sánh; không bao gồm PD/model, LGD/ECL hay dự báo; R2/R3 vẫn mở |
| R2 — multi-vintage | **Chưa đạt; access-blocked** | Downloader/manifest/registration safeguards và schema-version research đã có | Đã có 1 Freddie vintage (2012), cần thêm authorized annual samples để test semantics/support/time split; số vintage bổ sung trong checkpoint này = **0** |
| R3 — model study | **Chưa đạt; chưa fit (đúng gate)** | Pipeline/model engineering và synthetic integration coverage; latest real-data prepare-study ghi 43.327 train rows (100 positive), 0 calibration/validation/test, no model fit | Actual same-cohort fit, calibration, validation, OOT, uncertainty, selection freeze, model card; tất cả chờ R2 và protocol |
| R4 — final handoff | Partial | Descriptive case study, reproduction, privacy/export/browser evidence | Research/model release đầy đủ chờ R0 sign-off cuối và R2/R3 |

R1 được đánh dấu đạt theo scope mô tả một vintage vì Definition of Done tại
plan §47.22 yêu cầu views dùng cùng frozen dataset, reconciliation, denominator
và support, unavailable khác zero, finding review, export có lineage/filter và
browser QA. Đạt R1 không đồng nghĩa D01 hoàn chỉnh. Browser receipt mới nhất
cho case `d01-202610150931` ghi **PASS, 107 checks, zero browser errors**; receipt,
ảnh và dữ liệu giữ trong private D:.

## Data đã bổ sung / data còn thiếu

- **Đã bổ sung vào D01:** Release Notes và Disclosure Changes chính thức của
  Freddie Release 47, có hash riêng. Chúng giúp xác định thay đổi code/sentinel,
  missing value, loss sign, cumulative modification cost, score field và layout.
  Đây là tài liệu schema, **không phải loan-performance rows**; thêm 0 vintage.
- **HMDA mới cho D08, không tính vào D01:** One-Year National 2024 đã được tải,
  hash/reconcile, tích hợp view và workbook; browser acceptance đã đạt. One-Year
  2023 là bước tiếp theo cho so sánh application mix, vẫn không thay thế Freddie
  performance vintages.
- **Data chính Freddie:** chỉ 2012 đã qua pipeline hiện có. Trang chính thức
  công bố monthly performance đến 31/03/2026, nhưng download annual files chạy
  qua Clarity có sign-in. Không lấy macro, HMDA hay survey thay cho vintage.
- **Ginnie:** user đã chấp thuận Terms. Official catalog có production quarterly
  `LoanPerf_202606.zip`, nhưng endpoint yêu cầu phiên hợp lệ; thư mục nhận cookie
  `D:\data\Codex\credit-atlas\data\private\access` hiện chưa có file cookie.
  Ginnie là case riêng và sẽ không tăng Freddie
  vintage count.
- **Fannie Mae:** primary dataset hiện công bố acquisition/performance Q1 2026,
  nhưng yêu cầu Data Dynamics account, xác minh email và chấp nhận terms; sample
  công khai/layout có ích cho parser, không tương đương full panel. Chỉ dùng sau
  khi quyền truy cập và mục đích sử dụng được kiểm chứng, làm case/cross-validation
  riêng trước khi harmonize.
- **Treasury HAMP (nguồn bổ trợ, không phải Freddie vintage):** đã tải và audit
  archive public update; khớp metadata **9.872.074 rows**, 0 duplicate key groups
  và 0 domain ngoài danh mục. Tuy nhiên payment activity quan sát được chỉ có
  14 tháng **2022-01–2023-02**; 2018–2021 vẫn chưa có coverage được chứng minh.
  Bản Treasury 2009–2017 đang timeout ở host chính thức. Nguồn này được giữ như
  một case servicing/loss-mitigation riêng; không làm tăng 26/50 hay số vintage
  Freddie. Xem [Treasury HAMP review](TREASURY_HAMP_DATA_REVIEW_VI.md).
- **Aggregate/context:** FHFA NMDB, CFPB Mortgage Trends, Fed/FRED, HMDA, FHFA
  PUDB, HUD và NSMO có ích cho domain riêng hoặc benchmark, nhưng khác grain,
  population/cadence/observation process; không ghép để tạo Freddie panel.

Các nguồn và access conditions được đối chiếu tại
[`D01_R2_DATA_SOURCE_RECHECK_2026-10-16_VI.md`](D01_R2_DATA_SOURCE_RECHECK_2026-10-16_VI.md),
[`D01_GINNIE_ACQUISITION_PREFLIGHT_2026-10-16_VI.md`](D01_GINNIE_ACQUISITION_PREFLIGHT_2026-10-16_VI.md)
và [`FREDDIE_RELEASE47_CROSS_VINTAGE_IMPLICATIONS_VI.md`](FREDDIE_RELEASE47_CROSS_VINTAGE_IMPLICATIONS_VI.md).

## Ưu tiên làm tiếp

1. **Mở Freddie Clarity access trước.** Sau khi có phiên hợp lệ, lấy đúng annual
   sample theo manifest chính thức; tải một vintage pilot (plan hiện nêu 2008 là
   ứng viên train), ghi bytes/hash/release,
   kiểm ZIP/member/schema/domain/IDs/row grain và disk headroom. Chỉ sau khi audit
   mới đăng ký vintage vào canonical panel. Không chạy batch trước pilot.
2. **Mở Ginnie pilot song song, nhưng giữ case riêng.** Dùng session cookie do
   user lưu trên D:, profile-check session trước, tải quarterly 2026Q2, hash và
   audit HH/LP/TT, disclosure key-period uniqueness, statuses/codes/frequency.
   Chỉ sau khi pilot qua mới cân nhắc annual hoặc loan-level payment history.
3. **Fannie Mae chỉ sau khi access/terms được kiểm chứng.** Bắt đầu với sample
   và file layout để audit mapping; sau đó lấy panel được phép dùng. Giữ Freddie,
   Fannie, HARP mapping và population riêng cho tới khi crosswalk/protocol được
   nghiên cứu và duyệt.
4. **Không tải thêm context chỉ để tăng số lượng file.** Các aggregate đã tích hợp
   hỗ trợ macro/market/context; nguồn mới chỉ ưu tiên nếu đóng được gap cụ thể như
   independent validation, delinquency benchmark hoặc target observation.

## Quy tắc về biến dự phóng

Hiện checkpoint này **không có biến nào được CreditAtlas dự phóng, nội suy hoặc
điền thiếu**. Số liệu lịch sử quan sát vẫn phải ghi rõ nguồn, vintage/revision,
population, grain, denominator, as-of date và missingness. Nếu sau này cần dự
phóng biến nào, trước khi tính phải có hồ sơ riêng ghi:

1. Định nghĩa biến, đơn vị, kỳ quan sát, nguồn và ngày thông tin thực sự sẵn có.
2. Research phương pháp phù hợp với chính biến đó; giải thích lựa chọn so với
   benchmark đơn giản, trích dẫn tài liệu/phương pháp nguồn và điều kiện áp dụng.
3. Công thức/thuật toán, feature/input, transformations, training window,
   forecast horizon, assumptions, treatment của revisions/missingness và data
   lineage.
4. Time-ordered backtest không shuffle; baseline naïve; rolling/expanding-origin
   evaluation phù hợp; metric theo use (ví dụ MAE/RMSE cho mức liên tục, Brier/
   calibration cho xác suất); uncertainty intervals và subgroup/error analysis.
5. Stress/sensitivity, failure cases, leakage checks, reproducible code/receipt,
   và nhãn UI/export phân biệt `observed`, `estimated/imputed` và `forecast`.

Nếu không đủ lịch sử/định nghĩa để validation, trạng thái phải là **unavailable**
hoặc **exploratory scenario**, không tạo một con số “dự phóng” rồi trình bày như
quan sát. Chi tiết phương pháp và kết quả nghiên cứu phải được ghi trước khi biến
được đưa vào ứng dụng.

## Bằng chứng chính

- [`PLAN_MODULE_01.md` §47.22](PLAN_MODULE_01.md) — Definition of Done.
- [`D01_CHART_SUPPORT_AUDIT_VI.md`](D01_CHART_SUPPORT_AUDIT_VI.md) — reconciliation
  sáu nhóm chart/support.
- [`D01_EXPORT_CONTRACT_AUDIT_VI.md`](D01_EXPORT_CONTRACT_AUDIT_VI.md) — 5 scopes,
  lineage, determinism, unsupported metrics và privacy scan.
- [`D01_CASE_STUDY_VI.md`](D01_CASE_STUDY_VI.md) — population, target, KPI,
  denominators, kết quả và limitations.
- [`D01_R2_CURRENT_SUPPORT_AUDIT_2026-10-16_VI.md`](D01_R2_CURRENT_SUPPORT_AUDIT_2026-10-16_VI.md)
  — current real-case split and train-feature availability; DTI mask is confirmed
  by Freddie's official FAQ to be structural for Relief Refinance; aggregate-only
  train audit is implemented/tested and its verified aggregates now appear in
  Model Readiness; no model fit. Latest UI acceptance: **107 checks**.
- Latest private browser receipt:
  `D:\data\Codex\credit-atlas\artifacts\private\browser-qa-7137a6a6545b\receipt.json`.
  Source code used: current public working tree; real-data case:
  `d01-202610150931`.
