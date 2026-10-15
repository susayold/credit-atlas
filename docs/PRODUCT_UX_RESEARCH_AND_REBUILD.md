# CreditAtlas — nghiên cứu app và làm lại trải nghiệm nghiệp vụ

Ngày10/10/2026. Yêu cầu: tìm hiểu app credit risk hiện có, làm lại UX/UI và
chức năng chi tiết. Phạm vi vẫn gồm cả5 workspace; thay đổi homepage không
đủ để hoàn thành yêu cầu.

## 1. Bằng chứng sản phẩm

Đây là nghiên cứu tài liệu sản phẩm, help center và brochure công khai.
Không đăng nhập tài khoản SaaS trả phí. Phân biệt capability hãng công bố với
thiết kế đề xuất cho CreditAtlas; không khẳng định đã đo tốc độ hoặc kiểm định
model của hãng. Không tái sử dụng screenshot/mã/branding của hãng trong app.

### Taktile — credit decision platform

Hãng tổ chức credit work quanh kết nối inputs, xây decision logic, backtest
và so sánh strategy, rồi deploy/monitor. Bài học cho CreditAtlas: policy cần
màn riêng để xem assumptions, thử alternative và lưu version; không nằm sau
hàng chục bảng validation. Simulation phải phân biệt preview và study đã lưu.
Không bê production deployment vào benchmark chưa qualified.
[Nguồn](https://taktile.com/credit-decision-platform).

### Taktile — Case Manager

Tài liệu mô tả configurable workspace/queue/template, case history có audit
trail và analytics về thời gian/SLA. Bài học: danh sách hồ sơ → chọn một hồ
sơ → bằng chứng → hành động review. CreditAtlas hiện có token-scoped
explanations và portfolio review versions; chưa có reviewer identity/SLA,
AI case creation hoặc quy trình phê duyệt ngân hàng. Không tạo badge approval
giả để giao diện trông giống sản phẩm thương mại.
[Nguồn](https://www.taktile.com/case-manager).

### CreditRiskMonitor — monitoring và financial analysis

Trang sản phẩm mô tả executive dashboard, risk alerts, watchlists và financial
statements/ratios để so sánh công ty. Bài học: tổng quan phải giúp biết vùng
nào cần đọc sâu; bảng chi tiết phục vụ drilldown. CreditAtlas có SEC facts,
SBA, FDIC/WDI và benchmark, nhưng chưa có proprietary scores hoặc event feed
của hãng. Chỉ hiển thị alerts thật từ contract/quality evidence hiện có;
không giả near-real-time risk deterioration.
[Nguồn](https://www.creditriskmonitor.com/solutions/creditriskmonitor-platform/).

### Moody’s — portfolio analytics

Tài liệu nhấn mạnh portfolio exposure/performance, concentration, what-if,
stress scenarios và instrument-level analysis. Bài học: dùng task-specific
workspace với chung snapshot/currency scope; scenario, ECL và tail là màn
riêng. CreditAtlas có declared engines với pinned assumptions; chưa đạt
qualified capital/IFRS9 hoặc calibrated stress models của sản phẩm thương mại.
[Nguồn](https://www.moodys.com/web/en/us/solutions/portfolio-management.html).

### nCino/RDC.AI — Portfolio Navigator và Alerts

Brochure nSight2025 có Portfolio Alerts/Navigator/Assistant. Navigator dùng
filter để cô lập populations và drilldown về segments/trends; Alerts gắn
signals với threshold policy. Học cấu trúc overview → segment → evidence,
không sao chép AI/early-warning claims khi source chỉ là historical snapshot.
Brochure mô tả transaction-level monitoring, không đồng nhất với dữ liệu
Freddie/UCI của CreditAtlas.
[Brochure chính thức, trang8–11](https://info.ncino.com/rs/775-TRD-708/images/Supercharging%20Portfolio%20Monitoring%20With%20Generative%20AI.pdf?version=0).

### nCino — Loan Officer Dashboard

Help center15/08/2025 mô tả widget về pipeline, new/abandoned applications,
upcoming closings và tasks, bấm widget mở danh sách liên quan. Bài học:
chọn tác vụ bằng câu hỏi nghiệp vụ, có selected context và next action.
CreditAtlas không có origination pipeline/customer PII nên không dựng số
application pending hoặc upcoming closing giả.
[Help center](https://mortgagehelp.ncino.com/hc/en-us/articles/38758198364429-LO-Dashboard-Explained-Web).

### SAS — risk management

Trang solutions nêu stress testing, customer lifecycle risk, cashflow/valuation
và reporting. Bài học thiết kế: scenario inputs, results và report/review cần
phân biệt. Phần tính toán của CreditAtlas tiếp tục dùng method đã audit;
redesign không phải lý do đổi calibrated assumptions hoặc mô hình đã khóa.
[Nguồn](https://www.sas.com/en_us/solutions/risk-management.html).

## 2. Chẩn đoán app hiện tại

Trước redesign, P4 tự tải movement→scenarios→ECL→tail→convergence→review trên
một trang; người dùng phải cuộn nhiều màn và chờ study không cần đọc. Excel
nằm trên cùng thay vì dashboard. P1 bắt đầu bằng technical model/split tables
và đẩy hồ sơ giải thích xuống cuối. Homepage đẹp hơn nhưng chưa là bàn làm
việc. Các select dùng version IDs dài, thiếu cách chọn câu hỏi cần trả lời.

## 3. Blueprint cho cả5 domain

| Domain | Tổng quan | Tác vụ chính | Chi tiết & review |
|---|---|---|---|
| P1 Retail | Saved ranking/probability KPIs và calibration | Validation; policy/subgroup; hồ sơ/giải thích | Token search/paging, signed contribution visualization, private export, model evidence |
| P2 Mortgage | Loan book/state distribution và cohort scope | Portfolio; transitions; vintage/exits; lifecycle | Loan timeline, cure/redefault, supported transitions, loss components, findings |
| P3 Business | Source-specific financial/outcome overview | SBA cohorts; issuer financials; bankruptcy benchmark | Issuer/filing context, ratios, memo/evidence, missing/ambiguous facts |
| P4 Portfolio | Native-currency balance, records, zero balances, risk availability | Concentration drilldown; movement; scenarios; ECL; tail | Review versions, Excel intake/export, source contract |
| P5 Structured | Pool/cashflow/tranche context | Period waterfall; terms; market/bond scenario | Selected period/stage evidence, checks and source exports |

Shared interaction: selected scope luôn rõ; task tabs có URL; keyboard và
mobile hoạt động; đọc evidence khi cần; empty/loading/error theo từng task.
Không gộp unrelated denominators hoặc dùng màu risk rating khi chưa có rule.

## 4. Thiết kế đã triển khai

P4 tám task tabs, tải study theo nhu cầu. Overview dùng đúng saved aggregate;
bar amount shares bấm chọn bucket, tìm kiếm, sort và detail card. Multi-currency
chart chọn currency riêng; không cộng số dư cross-currency. EL unavailable
giữ đúng source contract. Full rows còn trong evidence disclosure.

P1 năm task tabs: overview, validation, policy/subgroup, hồ sơ/giải thích,
model/evidence. Overview đọc saved final-test KPIs và calibration bins, không
rescore. Policy và explanations chỉ tải khi được chọn. Các API/private export
và source/method pinning được giữ nguyên.

Shared task tabs hỗ trợ arrow/Home/End keys, cached completed panes và
`workspace_tab` URL state. Source/filter change làm invalid tab context; response
từ task không còn active không được đánh dấu hoàn tất.

P2 có9 tác vụ dùng chung run/segment/basis/horizon: overview, portfolio,
cohorts/exits, transitions, lifecycle/cure, loss/recovery, chất lượng,
review/evidence và model readiness. Chọn matrix cell đọc denominator/support;
chọn loan đọc events và observed UPB. Danh sách loan cuộn trong card trên mobile,
có selected state cho assistive technology và chống response tìm kiếm cũ.

P3 SBA có5 tasks: tổng quan, cohorts/outcomes, chất lượng, dictionary và
nguồn/giới hạn. Status explorer lấy record share riêng trong mỗi program;
bấm status mở đúng cohort và detail, không biến terminal status thành PD.
SEC có4 tasks: issuer overview, financial fields, concept evidence và quality;
common issuer/accession/cutoff controls giữ nguyên filing-specific context.
Missing/ambiguous facts và ratio unavailable vẫn hiển thị theo nguồn.

P5 ABS có5 tasks: overview, waterfall, tranches, source checks và terms/limits.
Priority explorer chọn từng stage, đọc due/paid/unfunded, cash/reserve và
allocations. Tranche selector đọc beginning/ending balance cùng payments.
Collection/payment dates và conditional legal qualification luôn rõ.
Market có3 tasks: native series, bond scenarios và source/use limits;
giá bond dùng assumptions công khai trên form, không mượn Treasury/OAS làm
actual-security valuation.

Homepage có4 tác vụ mở trực tiếp Excel, portfolio review, hồ sơ Retail và ABS
waterfall, bên cạnh5 domain cards. Ctrl/CmdK mở search theo tác vụ; có no-match,
Escape và Enter. Không dựng hồ sơ pending/SLA/alerts chưa có data.

## 5. Phạm vi nghiệm thu của goal

1. Kiểm tra P4/P1 bản mới trên dữ liệu thật, desktop/mobile, private exports,
   lazy loading, stale response và URL restore; cập nhật harness cũ theo luồng mới.
2. Làm lại task/detail layouts P2/P3/P5; không chỉ đổi navigation shell.
3. Homepage có lối vào tác vụ và tìm chức năng, thay vì thiên về hero/catalog.
4. Hồ sơ/period/issuer detail có evidence visualization và hành động thực tế.
5. Kiểm tra toàn bộ luồng chính của5 domains và ghi completion audit.

Các mục này được nghiệm thu bằng browser/source/export evidence trong phần7.
Capability cần
real-time feeds, affordability/application data, permission roles hoặc qualified
models tiếp tục giữ gap riêng; không thay bằng mock để đóng goal.

## 6. Checkpoint đã kiểm chứng

`product-workbench-qa-b5488dc0d20b/receipt.json`: **14 checks PASS** trên local
server thực. Đối chiếu9.698 records/141 zero balances/USD915.208.989,12; meter
share và selected bucket từ API; search rỗng không fallback; sort/cache; chuyển
bucket sang review draft đúng19 observations/USD2.012.252,51 của AK; private
Excel export; movement/scenario/review; keyboard task tabs; exact URL/reload;
desktop/mobile390px. Không có eager ECL/tail requests trên overview.

Retail đối chiếu saved3.001 final-test clients/AUC0,7779 và tọa độ từng điểm
calibration từ source bins;9 bins có support, bin cuối rỗng không vẽ thành
zero. Policy/subgroup đúng benchmark version; task giải thích có toàn4.499
validation clients/20 rows ở trang đầu và private JSON export rank4.499
không lộ source client ID. Ledger consumed holdout không đổi, không unexpected
browser errors. Không lưu review draft hoặc refit/rescore.

`mvp-ux-qa-acff7c9601fa/receipt.json`: **11 checks PASS** qua cả5 launch routes,
source filter, responsive/menu/reload và command search trên mobile: no-match,
Escape, CtrlK, Enter mở actual Retail validation. Đây là route/shell acceptance
của5 domain, không phải bằng chứng đã redesign màn chi tiết P2/P3/P5.

Các lượt trước được giữ: interrupted harness đếm sai10 calibration points;
lượt fail chọn exploratory policy không có subgroup cùng version; interrupted
textarea text assertion. Không tính là PASS. Empty subgroup đúng scope được
giữ; khi chưa có explicit selection, benchmarkbd4b8623de28 được ưu tiên nếu
còn trong catalog. Explicit version khác không bị thay hoặc fallback.

Node syntax check PASS. Numerical/source methods và API contracts không đổi;
không dùng full regression1.098 của phiên bản trước để tuyên bố full regression
cho tất cả thay đổi UI lần này. Phần trên là checkpoint P4/P1 trước khi
triển khai P2/P3/P5; xem phần7 cho trạng thái bản hiện tại.

## 7. Nghiệm thu mở rộng (10/10/2026)

Các receipt nằm trong `private evidence omitted from public release`.

| Phạm vi | Evidence | Kết quả |
|---|---|---|
| Homepage4 tác vụ,5 domain routes, Excel direct launch, CtrlK/mobile/reload, Market3 tasks | mvp-ux-qa-1fcc1a0657ed |13 PASS |
| P4/P1 source parity, full4499 cases, selected bucket→review draft, cached/keyboard tabs, active-tab repeated clicks | product-workbench-qa-cd84624ad93d |14 PASS |
| Delayed real policy catalog, leave/re-enter pending task; no duplicate controls; uppercase/accent-free task search | task-race-qa-b252361edc23 |4 PASS |
| P3 SBA/SEC, P5 ABS period/priority/tranche, P2 matrix/loan/mobile | remaining-domains-qa-aefc83d0ae39 |7 PASS, có bounded loan list và aria-pressed |
| SBA504/FY2020 exact private export; Retail holdout metrics; independent mortgage navigation | suite-browser-qa-9da56875577f |16 PASS |
| SEC cutoff/no-future-fallback, Ford missing, GM conflicting evidence, exact export | sec-browser-qa-81a305268507 |10 PASS |
| ABS11 stages/7 tranches/36 checks, actual due/paid/shortfall, collection/payment year boundary, export | abs-browser-qa-eaa1a2144464 |12 PASS |
| Market native OAS Sunday,994 quarantined source conflicts, independent7% yield price/duration, export | market-browser-qa-680b3409a688 |13 PASS |
| Mortgage overview,9 workflow routes, cohort/segment/horizon, matrix support, lifecycle, loss, findings/export | browser-qa-1d81ff3991df |24 PASS |
| Portfolio full movement/scenario/ECL/tail/convergence, review revisions, all exact exports, XLSX formula parity, upload3 USD/VND records | exposure-browser-qa-e2cda013ece1 |19 PASS |

Legacy harnesses dùng helper `scripts/browser_navigation.py` để mở grouped
navigation/mobile menu và chọn task qua UI. Các harness bị ảnh hưởng đã chuyển
đến đúng task: suite, exposure, SEC, ABS, market, Retail explanations; các
navigation checks của mortgage, HMDA, FDIC, WDI và bankruptcy dùng helper chung.
Dedicated Retail cohort/policy/subgroup URLs vẫn mở đúng task theo explicit
IDs. Compileall PASS không được tính như browser execution cho các script chưa
chạy lại. Evidence hiện tại và numerical audits trước đây được phân biệt rõ.

Failure `market-browser-qa-491f8156d66c` là5s assertion trước cold FDIC response;
đã tăng assertion timeout và chạy lại13 PASS. Failure
`exposure-browser-qa-2ae832162665` phát hiện bấm active task lúc loader còn chạy
có thể khởi tạo thêm lượt tải. Pending/version guards được sửa; nghiệm thu
Portfolio sau sửa đạt19 PASS trong receipt cuối. Không tính hai lượt này là PASS.
`exposure-browser-qa-7b9fdaa00dde` qua18 checks nhưng fail tại harness chờ
chuỗi `observations` sau khi template đã nhập thành công thành3 declared records.
Actual context là `position/observation records`; assertion đã sửa và
receipt cuối đạt19 PASS. Interrupted task-race harness chờ total trong comparison table
thay vì scope paragraph được giữ riêng, không tính là PASS.

### Đối chiếu yêu cầu

| Yêu cầu từ goal/blueprint | Hiện trạng và bằng chứng |
|---|---|
| Nghiên cứu app hiện có và giải thích cấu trúc nghiệp vụ |7 nguồn chính thức ở phần1; phân biệt capability hãng với CreditAtlas và giới hạn public-doc research |
| Làm lại cả5 workspace | P1/P4 workbenches; P2 nine routes; P3 SBA/SEC tasks; P5 ABS/Market tasks. Source-backed workflow receipts ở bảng trên |
| Homepage giúp bắt đầu công việc |4 real task actions,5 distinct domain routes, task search;13-check MVP receipt |
| Drilldown có chi tiết và hành động thực | P4 selected bucket→review draft, review revisions/exports; P1 all4499 explanations; P2 matrix/loan/finding; P3 status→cohort and concept evidence; P5 priority/tranche/exports |
| Source/selected scope rõ và URL restore | Actual selected import/currency, loan book segment/year, issuer/accession/asof, SBAprogram/bucket, ABSperiod, Marketseries/dates/bondterms được checked qua browser/exact exports |
| Lazy loading/cache/stale response, keyboard/mobile | No eager ECL/tail on overview; cached sort/keyboard tabs; pending re-entry test with actual saved catalog;390px screenshots/overflow checks |
| Cập nhật kiểm thử và tài liệu | Navigation helper và task-specific legacy harnesses; numerical/exact-export assertions giữ nguyên. Portfolio full19 PASS, Mortgage24 PASS và các domain receipts hoàn tất; user guide tiếng Việt đã lưu |

Đã xem trực quan ảnh Business desktop, ABS desktop/mobile và Mortgage mobile
trong receipts. Sau bounded loan-list change, selected timeline tiếp cận được
ngay dưới card danh sách; không phải cuộn qua20 rows trước. Table rộng cuộn
trong card và task strip cuộn nội bộ. Node syntax và Python compileall PASS.

Không có required product gap bị đóng bằng mock: origination/affordability,
live alerts, reviewer roles/SLA và model qualification thuộc kế hoạch suite
trong `PLAN_FIVE_WORKSPACES.md`, vẫn chưa hoàn tất. Goal UX này không chứng nhận
toàn bộ50 capabilities, IFRS9/capital hoặc Freddie multi-vintage model.

### Kết luận nghiệm thu

Các yêu cầu UX của goal và năm bước ở phần5 đã được thực hiện và đối chiếu
bằng10 receipt PASS ở bảng trên, tổng132 checks có một số phạm vi kiểm tra
chồng lấn. Các script legacy chưa chạy lại riêng không được tính như receipt
mới; coverage của các luồng thay đổi được chứng minh bằng các receipt hiện tại.
Không yêu cầu thêm dữ liệu để hoàn thành đợt UX này; source/model gaps vẫn nằm
trong kế hoạch suite và hiển thị đúng trên app.

[Hướng dẫn sử dụng theo công việc analyst](WORKBENCH_USER_GUIDE_VI.md) có
quy trình cho cả5 domain, Excel/review và cách lưu URL/report để tìm lại.
Browser QA reviews/findings dùng database riêng; không ghi vào user reviews.
QA upload chỉ tạo import của file EXAMPLE, không thay nguồn Freddie hoặc model.
Server logs có client-disconnect khi reload rời pending request trong full
Portfolio QA; receipt ghi no browser errors và source/export assertions PASS.

## Enterprise monitor update

Xem [nghiên cứu mở rộng 14 hãng và bản monitor đã triển khai](ENTERPRISE_CREDIT_MONITOR_RESEARCH.md). App mở mặc định Risk monitor; trang năm workspace và 50 capability plans tiếp tục truy cập riêng.
