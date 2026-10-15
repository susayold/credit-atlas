# CreditAtlas — cách dùng theo công việc của analyst

## Dữ liệu và phân tích KPI

**Excel principal maturity:** trong Debt maturities bấm **Xuất maturity Excel**.
Maturities/Facts giữ exact selected filing/family, subtotal/total/share formulas
và source evidence. [Hướng dẫn](SEC_MATURITY_EXCEL_VI.md).

**Đáo hạn gốc nợ:** mở P3 Issuer financials → Debt maturities, chọn issuer,
filing/cutoff và debt-only hoặc debt/capital-lease scope. Đọc6 buckets,
supported subtotal, complete total và first-three-years share; thiếu inputs
giữ unavailable. [Cách đọc và dữ liệu còn thiếu](SEC_DEBT_MATURITIES_VI.md).

**Excel doanh nghiệp:** tại Annual trends hoặc Interest coverage, bấm
**Xuất SEC Excel**. Hai sheets Analysis/Facts giữ formulas, period comparisons,
driver bridges, explicit coverage và source evidence theo bộ lọc hiện tại.
[Hướng dẫn](SEC_ANALYSIS_EXCEL_VI.md).

Mở **Risk monitor → Phân tích KPI chi tiết**, chọn P1–P5. Mỗi domain có actuals,
formulas/mẫu số, comparisons, source/quality controls, individual KPI dossier
và investigation playbook; export JSON/Excel theo filters hiện tại.
[Bản phân tích 88 KPI](KPI_ANALYSIS_GUIDE_VI.md) và
[workflow app/Excel](KPI_APP_AND_EXCEL_VI.md).

Để đọc doanh nghiệp cụ thể, mở **P3 Issuer financials → Annual trends** hoặc
**Interest coverage**. Chọn3/5/10 report periods, issuer và cutoff; đọc exact
inputs, candidate evidence và support trước diễn giải. Coverage có explicit
expense selector và latest-period reading; phần thiếu dữ liệu không thành zero.
[Hướng dẫn coverage](SEC_INTEREST_COVERAGE_VI.md).

## Lưu financial memo của issuer

P3 Issuer financials → **Corporate memo** → **Tạo corporate memo**. Nhập các
phần narrative, lưu cùng exact selected filing và annual history do server
capture. Sửa memo tạo revision; đọc lịch sử và export private JSON. Nguồn/kỳ
mới cần memo mới. [Hướng dẫn đầy đủ](CORPORATE_FINANCIAL_MEMO_VI.md).

## Financial analysis qua nhiều năm

P3 Issuer financials có **Annual trends**: chọn3/5/10 report periods, đọc
ratios và deltas cùng baseline/source support; export private JSON. Original
10-K và amendments giữ riêng; missing/gap/ambiguous/concept changes có gate.
Xem [hướng dẫn SEC trend](SEC_ANNUAL_TRENDS_VI.md). DSCR/covenant vẫn cần inputs.

## Đọc dữ liệu và KPI trên Risk monitor

Phần **Dữ liệu & phân tích KPI** nằm đầu monitor. Chọn domain rồi chọn **Đọc
chi tiết một KPI** để xem actual, baseline actual, delta, công thức/support,
diễn giải và evidence IDs. Mỗi domain có bốn bước đọc số liệu/kiểm tra giả thuyết,
bảng source support mở sẵn và KPI thiếu inputs. **Xuất KPI Excel** xuất đúng
scope bộ lọc lúc bấm, gồm actuals, delta formulas, data tables và immutable
review history. Xem [hướng dẫn app và Excel](KPI_APP_AND_EXCEL_VI.md).

Mục **Analyst review gắn với KPI** tạo review từ snapshot hiện tại, giữ actuals/
baseline/filters/sources cùng owner, nhận định, giả thuyết và bước kiểm chứng.
Review đã lưu có revision/history và export JSON; sửa judgement không thay
evidence đã capture. Xem [hướng dẫn review đầy đủ](KPI_ANALYST_REVIEW_WORKFLOW_VI.md).

**Baseline cho KPI readout** có trong P2/P4/P5. Auto chỉ chọn đúng tháng lịch
trước; manual dùng exact prior period; tắt baseline chính giữ actuals và bỏ delta
phụ thuộc baseline đó. Missing/current/future/ambiguous periods không fallback.
URL và JSON giữ requested/resolved period + status. P2 cùng tháng năm trước là
comparison riêng; overview chart vẫn có Δ so kỳ trước; lifetime/quality/replay
không bị đổi scope. P4 chỉ có hai pinned imports cùng USD/region/source contract.

Mỗi domain có thêm **Chất lượng dữ liệu & phạm vi kiểm tra**: 22 controls trên
cả năm domain. Xem sample/grain, missingness, source-record duplicates, integrity,
partition và ledger checks cùng công thức/mẫu số. P3 có parse completeness theo
file/field; blank outcome date có thể là event chưa xảy ra. P1 raw-feature missing
profile và P4 missing-amount profile chưa có trong monitor, nên giữ Unavailable.
Không có composite quality score; qualification declarations được ghi riêng.

Trong **P5 Structured**, đọc tám dòng `Replay`/ledger residual cùng bảng
**Selected cash ledger** và **Cash and reserve bridge**. Ledger giữ due/paid/
shortfall, cash, reserve và external-distribution flag theo priority. Reserve
replenishment là internal transfer; không cộng overlapping shortfalls thành loss.
Kỳ này là latest reported period, historical conditional replay, không forecast.

Trong **P3 Business**, phần SBA và SEC được ghi scope riêng. Các dòng SEC
cho AAPL/MSFT/F/GM có report date/filing date; hai bảng financial fields và
concept evidence giữ exact USD, periods, candidate count và conflicts.
Nút **Filing evidence** mở đúng issuer, accession và cutoff trong SEC workspace.
Không dùng latest filing khác report date để xếp hạng cùng kỳ hoặc gán issuer PD.

Trong **P1 Retail**, các KPI policy dùng validation 4.499 clients, tách khỏi
3.001 final-test clients ở phần model. Mở các bảng **Policy assumptions**,
**Declared cases và constant-action benchmarks**, **Action support** để đọc
cost matrix, thresholds, capacity và support. Case mặc định là mục đầu plan,
không phải phương án tối ưu. Các số `cost units` là giả định, không tiền lỗ thực.
Để thay assumptions và tính preview, mở workspace Retail → **Policy**.

Trong **P4 Portfolio**, mở **Phân rã biến động theo vùng — exact-cent bridge**
để xem prior/current/delta, contribution và records của mỗi vùng. Contributions
dùng tổng kỳ trước, cộng ra relative total change. Không diễn giải delta thành
loss hoặc cure; mở movement workflow nếu cần entries/exits/shared observations.
Xem [plan phân tích tiếp theo](PLAN_KPI_ANALYTICS_NEXT_VI.md) để biết thứ tự triển khai.

Mở **Risk monitor → Phân tích KPI chi tiết**, chọn P1–P5. Có 88 dòng KPI với
actual, comparison, công thức/support và diễn giải. Mở các bảng nguồn phía dưới
để xem split/calibration, lịch sử mortgage, SBA status, geographic buckets hoặc
ABS periods/tranches. Bộ lọc count/UPB thay đổi mẫu số D3; cửa sổ lịch sử chọn
12/36/all. Nút xuất report riêng tư lưu cả KPI và provenance. Reload giữ lựa chọn.

Mục **Các KPI cần dữ liệu / workflow bổ sung** chỉ rõ những chỉ số chưa tính được
và các workflow đã có riêng. EL thiếu risk inputs giữ Unavailable; không coi
approval amount là exposure hoặc stock D3 là PD. Đọc
[tài liệu đầy đủ về dữ liệu, 88 KPI và phân tích](KPI_ANALYSIS_GUIDE_VI.md)
để tra actual, baseline, phép tính và phạm vi nguồn của bản kiểm tra 10/10/2026.

> Cập nhật 10/10/2026: [Plan chi tiết 50 chức năng và hướng dẫn trong app](PLAN_WORKBENCH_DETAIL.md). Mỗi chức năng có mục tiêu, inputs, phương pháp, outputs, nghiệm thu và bước tiếp theo; đây là roadmap, không chứng nhận đã triển khai đủ.

Bản ngày 10/10/2026. Mở ứng dụng tại `http://127.0.0.1:8770`.
Trang chủ có năm workspace và bốn lối mở nhanh: Excel, review danh mục,
hồ sơ Retail và ABS cashflow. Dùng nút **Tìm chức năng** hoặc Ctrl/CmdK để
tìm một tác vụ; có thể nhập tiếng Việt không dấu. Menu bên trái nhóm theo domain.

## 1. P4 Portfolio: từ file Excel đến review

1. Mở **Nhập / xuất Excel** từ trang chủ. Chọn đúng import trong phần
   **Chọn danh mục & phạm vi**. Snapshot source mặc định có 9.698 observations,
   141 số dư bằng 0 và reported balance USD 915.208.989,12.
2. Nếu nhập dữ liệu riêng, tải mẫu. Thay ba dòng EXAMPLE trong InputPositions;
   cập nhật InputControl. Giữ tên sheet, header và nhập giá trị rõ ràng.
   Chọn file `.xlsx` rồi **Nhập Excel**; app tạo import riêng có lineage.
3. Mở **Tổng quan**. Chọn currency, dimension và **Áp dụng phạm vi**. Đọc
   amount share, số records, zero balances và tình trạng có/thiếu risk inputs.
   Tìm/sắp xếp bucket rồi bấm bucket để đọc detail.
4. Bấm **Review bucket** để mở draft chứa đúng count/amount/scope của bucket.
   Điền owner, rationale, expiry; lưu draft, sau đó lưu revision nếu đổi trạng thái.
   Export review giữ evidence cùng lịch sử. Nhận định được lưu riêng với kết quả tính.
5. Chọn **Biến động** để xem bridge giữa hai source snapshots. Chọn
   **Scenarios**, **ECL**, **Tail risk** khi cần đọc các study đã lưu và assumptions.
   Các task này dùng chung import/currency; version selector chọn study cụ thể.
6. Quay lại **Excel**, chọn một native currency rồi xuất workbook. Sáu sheet:
   Summary, ScenarioModel, ResearchResults, Inventory, Review, Audit.
   Formula ở ScenarioModel hỗ trợ what-if; kết quả ECL/Monte Carlo đã lưu
   trong ResearchResults không được chạy lại khi sửa ô Excel.

Ở snapshot Freddie này, source EL là Unavailable vì chưa có declared risk
inputs. Số EL trong scenario study là một phép tính theo assumptions riêng.
Missing không thành zero và reported balance không tự trở thành EAD.
USD/VND/TWD giữ riêng. Chi tiết định dạng: [Excel workflow](EXCEL_WORKFLOW.md).

## 2. P1 Retail: model → policy → đọc từng hồ sơ

**Tổng quan** đọc saved final-test AUC/AP/Brier và calibration. Có 3.001 clients
trong final test; chart chỉ vẽ bins có support. Mở disclosure để đọc full
metrics và giới hạn đánh giá. **Validation** so sánh candidates, variants và
paired uncertainty; đây là kết quả đã lưu, không refit khi mở màn hình.

**Policy & subgroup** cho phép đọc version, thử thresholds/action costs/review
capacity, rồi lưu version sau preview. Đọc số accept/review/decline, capacity
overflow và subgroup support cùng assumptions. Thay policy không thay frozen model.

**Hồ sơ & giải thích** có toàn bộ 4.499 validation clients, paging và token
search. Chọn hồ sơ để đọc xác suất và signed contributions theo nhóm yếu tố;
xuất JSON riêng của hồ sơ. Token thuộc study, không phải source client ID.
**Model & evidence** giữ selection, feature/target và lineage context.
Benchmark Taiwan này có target tháng kế tiếp; màn hình không suy diễn nó
thành mô hình mortgage PD 12 tháng.

## 3. P2 Mortgage: đọc loan book và diễn biến thực

Chọn run, segment và metric basis ở context bar. Thanh tác vụ mở chín màn
trong cùng run: Tổng quan, Danh mục, Cohorts & exits, Transitions, Hồ sơ & cure,
Loss & recovery, Chất lượng, Review & evidence, Model readiness.

**Danh mục** xem monthly patterns và khoảng tháng. **Cohorts & exits** chọn
horizon/segment, đọc incidence cùng support. **Transitions** chọn reporting
year/count hoặc balance; bấm một matrix cell để đọc origin denominator,
distinct loans và phạm vi. Năm không có adjacent pairs giữ empty state.

**Hồ sơ & cure** lọc outcome hoặc tìm prefix của private loan key. Chọn một
loan để đọc reporting path, confirmed D3/cure events và observed UPB.
Danh sách cuộn trong card trên mobile; timeline ở ngay dưới card chọn loan.
Cure confirmation giữ ngày được xác nhận, không lùi về tháng đầu của episode.

**Chất lượng**, **Loss & recovery** và **Review & evidence** giúp đối chiếu
source findings/loss components, lưu finding cùng history và export theo scope.
**Model readiness** hiển thị gate/feature audit thật. Hiện chỉ có Freddie 2012;
chưa có đủ vintages để đóng training gate của kế hoạch D01.

## 4. P3 Business: chọn nguồn theo câu hỏi

SBA, SEC và bankruptcy benchmark là những populations khác nhau trong cùng
workspace. Mỗi nguồn có contract riêng; app không tự ghép chúng thành hồ sơ
của cùng một doanh nghiệp.

**Business credit / SBA:** Tổng quan có 2.190.504 source records, programs
7(a)/504 và snapshot date. Bấm một program/status để mở đúng population trong
**Cohorts & outcomes**. Chọn program, dimension, bucket và đọc records cùng
source amounts. **Chất lượng**, **Dictionary**, **Nguồn & giới hạn** giúp kiểm
tra grain/field definitions. Export giữ confirmed scope và decimal strings.
Record share trong status chart không phải fixed-horizon default probability.

**Issuer financials / SEC:** chọn issuer, annual filing và filing-date cutoff.
**Issuer overview** đọc kỳ và ratios; **Financial statements** đọc source
fields/units; **Concept evidence** mở từng field để xem candidates và conflicts;
**Source quality** đọc coverage. Ford có field missing và GM có revenue
ambiguous trong snapshot hiện tại; ratio phụ thuộc field đó giữ Unavailable.
Export chứa cùng accession/cutoff và facts, không lựa chọn lại alias đẹp hơn.

Từ SBA có lối mở **Bankruptcy ratios** hoặc **Saved bankruptcy model** để đọc
benchmark riêng. Chúng không chấm điểm tự động các doanh nghiệp SBA/SEC.

## 5. P5 Structured: từ kỳ báo cáo đến stage/tranche

Mở **ABS waterfall**, chọn collection period và kiểm tra payment date.
**Tổng quan** đọc pool/note context và lịch sử. **Waterfall** bấm từng priority
để đọc due, paid, unfunded, cash/reserve trước–sau và tranche allocations.
Full ledger nằm trong disclosure. **Tranches** chọn tranche để đọc balances,
interest/principal payments. **Đối chiếu** kiểm tra source comparisons;
**Terms & giới hạn** đọc qualification và assumptions. Xuất report theo kỳ.

Snapshot World Omni 2025-A có 20 kỳ reported history. Replay đang có điều kiện;
các stage shortfalls không được cộng thành credit loss. Full contractual
agreement/amendment verification vẫn là gap của dự án.

Mở **Market & bond** khi cần context: **Market context** chọn series/date,
đọc native observations và source gaps. **Bond scenarios** nhập face/coupon/
yield/years/frequency, tính scenario và xuất cashflows/duration. Đây là giá
theo assumptions trên form. **Nguồn & limits** giữ source rights và use limits.

## 6. Cách lưu và tìm lại một kết quả

URL giữ selected workspace/task cùng scope phù hợp của từng module. Sau khi
áp dụng filters, copy URL và lưu kèm report. Report/Excel/review là artifact
để đối chiếu; ghi source version, assumptions và mục đích sử dụng trong memo.
Workbook notes không tự ghi ngược vào review của app.

[Research và nghiệm thu UX](PRODUCT_UX_RESEARCH_AND_REBUILD.md) giải thích
những gì học từ sản phẩm thương mại, những gì đã kiểm tra và các capability
chưa có. [Trạng thái toàn dự án](FIVE_WORKSPACES_STATUS.md) giữ riêng gap về
data/model/qualification; hoàn tất đợt UX không đóng toàn bộ kế hoạch suite.

## Đọc nội dung chi tiết trong app

- Mở **Kế hoạch chi tiết 10 chức năng** ở đầu workspace. Chọn một mục để đọc mục tiêu, inputs, phương pháp, outputs, điều kiện nghiệm thu và bước tiếp theo. Trạng thái là checkpoint nghiên cứu, không phải live health.
- **Mở workflow liên quan** mở đúng màn/tab đã có. Những chức năng cần data chưa có nút chạy hoặc kết quả giả.
- **Tải kế hoạch (.md)** lưu 10 mục của domain đang xem. Bản đầy đủ 50 mục nằm trong [PLAN_WORKBENCH_DETAIL.md](PLAN_WORKBENCH_DETAIL.md).
- Mỗi task có **Hướng dẫn tác vụ**; HMDA, FDIC, World Bank và UCI bankruptcy có hướng dẫn riêng theo source. Hướng dẫn xuất hiện trước khi API nặng hoàn tất; kết quả vẫn chỉ hiện khi đọc được evidence.
- Retail → **Model & evidence**: đọc bảy bước từ population/target đến freeze và policy, rồi cách diễn giải AUC, AP, Brier, log loss, reliability và uncertainty. Cohort/split/holdout counts được lấy từ saved snapshot; mở màn không đánh giá lại model.

## Risk monitor — màn mở mặc định

Mở app tại `/` hoặc `?view=monitor`. Monitor tập hợp năm domain; đây là historical research monitor, không phải live customer alert feed.

1. **Monitor domain:** chọn domain để giữ KPI/panels/queue/export cùng scope. Đừng cộng số records/clients hoặc balances khác sources.
2. **Mortgage history / D3 basis:** 12/36/all reporting periods, count hoặc UPB. D3 share là observed active-stock fraction; denominator loại unknown-state và không phải PD.
3. **Review queue type:** lọc data quality, qualification hoặc unavailable inputs. Investigate mở workflow thật: quality/model readiness/retail dossier/ABS terms/exposure contract. Những row này không là borrower alerts hoặc SLA.
4. **Xuất monitor JSON:** giữ đúng filters, native measurements, provenance và queue. Export private; null EL vẫn null. P4 dùng pinned actual-source observation import, không dùng workbook EXAMPLE mới nhất.
5. **Đọc lại evidence:** đọc lại snapshot APIs; read-at là thời điểm đọc, không nguồn live hoặc calendar freshness SLA. Nếu một source lỗi, panel đó hiển thị unavailable; các source còn lại giữ riêng.
6. **Mở 5 workspace:** tới các hàng ảnh/domain và task cũ. Detailed capability plan tiếp tục nằm trong từng workspace.

[Nghiên cứu enterprise monitors từ 14 hãng](ENTERPRISE_CREDIT_MONITOR_RESEARCH.md).
