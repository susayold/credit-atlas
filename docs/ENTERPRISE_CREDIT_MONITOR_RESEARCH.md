# CreditAtlas — enterprise credit monitor: nghiên cứu và triển khai

Ngày kiểm tra: 10/10/2026. Mục tiêu: nâng app thành màn giám sát có dữ liệu, diễn biến, concentration, investigation và lineage; tiếp tục giữ năm workspace nghiệp vụ. Đây là nghiên cứu tài liệu công khai của 14 hãng, không phải kiểm thử tài khoản thương mại. Khả năng hãng công bố không chứng minh hiệu quả thực tế. Tài liệu lịch sử/roadmap được ghi rõ; không sao chép giao diện, logo, screenshot hay dữ liệu proprietary.

## 1. Oracle — Financial Services Credit Risk Analytics

**Ai dùng / công việc:** risk analyst và quản lý danh mục cần đọc overview, biến động, chất lượng tín dụng và concentration trong một run/as-of. User guide 8.1.2.0.0, November 2024 mô tả portfolio summary/variance/trend/inflows-outflows, top exposures, concentration, rating migration, capital và retail collections. Cấu trúc tách enterprise, wholesale, retail và trading book.

**Bài học thiết kế đề xuất:** một tầng tổng quan liên kết sang câu hỏi riêng; scope/run phải đi cùng kết quả. CreditAtlas dùng historical D3 trend, concentration và source quality ở màn monitor; không dựng RWA/capital hoặc rating migration từ delinquency categories. Capital cần risk weights, collateral, entity/legal aggregation và conventions đã kiểm định.

[User guide chính thức, mục 10–31](https://docs.oracle.com/en/industries/financial-services/ofs-analytical-applications/credit-risk-analytics/81270/cra_ug/cra_81271_ug.pdf).

## 2. Moody’s — CreditView và CreditLens

**Ai dùng / công việc:** analyst theo dõi entities, credit quality, peers, scorecard scenarios và portfolio changes. CreditView mô tả entity pages, standardized financials, ratings/news và portfolio monitoring. Presentation CreditLens June 2023 có mockup early-warning/entity signals; đây là thiết kế lịch sử, không xác nhận tất cả roadmap đã phát hành.

**Bài học đề xuất:** review list phải giải thích signal, nguồn và next action. CreditAtlas tạo investigation queue từ findings/gaps thật, chưa gọi đó là early-warning khách hàng. Chưa có licensed ratings/news, entity master hoặc behavioral updates để tái tạo CreditView.

[CreditView](https://www.moodys.com/web/en/us/capabilities/credit-risk/creditview.html) · [Presentation lịch sử CreditLens](https://ma.moodys.com/rs/961-KCJ-308/images/CreditLens%20Ambassador%20Club%20-%20Chicago%20June%202023.pdf).

## 3. S&P Global — CreditPro

**Ai dùng / công việc:** phân tích lịch sử rating transitions/default/recovery và benchmark internal credit assumptions. Hãng mô tả sampling theo rating histories, marginal/cumulative default rates, migration matrices và recovery information.

**Bài học đề xuất:** matrix cần population, horizon và support, không chỉ tô màu. CreditAtlas giữ Freddie delinquency transitions riêng rating transitions; không gọi empirical D3 share là calibrated PD. Muốn rating/default benchmark phải có comparable licensed histories và định nghĩa event.

[CreditPro](https://www.spglobal.com/market-intelligence/en/solutions/products/creditpro).

## 4. Bloomberg — MARS

**Ai dùng / công việc:** front office, risk, collateral; xem exposures, pricing/risk sensitivities và portfolio scenarios. MARS công bố market/credit/XVA modules, pricing/market data, mortgage cashflow engine và API. Các portfolio calculations sử dụng unified market snapshot.

**Bài học đề xuất:** snapshot nhất quán và tách observed positions khỏi scenarios. CreditAtlas hiện có native reported principal và assumption-only bond/ECL/tail engines; không có netting sets, derivative pricing hoặc collateral exposures để gọi là counterparty monitor/XVA.

[MARS](https://professional.bloomberg.com/products/risk/mars/).

## 5. BlackRock — Aladdin Risk

**Ai dùng / công việc:** investment/risk managers muốn tổng hợp risk/return across assets và kiểm tra portfolio resilience bằng stress/scenario analysis. Sản phẩm công bố integrated analytics và risk-factor framework.

**Bài học đề xuất:** portfolio overview phải cho phép đọc contribution/drivers rồi drilldown, đồng thời giữ entity/security mapping. CreditAtlas không cộng P2 và P4: chúng là hai cách nhìn cùng Freddie observations. Whole-portfolio risk cần actual holdings, pricing, factor model, currency conversion và overlap contracts.

[Aladdin Risk](https://www.blackrock.com/aladdin/platforms/products/aladdin-risk).

## 6. MSCI — RiskMetrics RiskManager

**Ai dùng / công việc:** institutional risk teams dùng VaR, factor, stress, liquidity và counterparty analytics trong cùng nền tảng. Hãng mô tả RiskMetrics calculation engine và portfolio risk monitoring.

**Bài học đề xuất:** overview phải gắn risk measure với engine/scenario/cutoff. CreditAtlas không diễn giải source principal thành VaR; research tail assumptions và convergence giữ riêng khỏi observed concentration. Counterparty/liquidity analytics vẫn cần inputs và model qualification riêng.

[RiskManager](https://www.msci.com/data-and-analytics/risk-management-solutions/riskmetrics-riskmanager).

## 7. SAS — Credit Risk Management / model governance

**Ai dùng / công việc:** credit model/risk teams tích hợp data, develop/backtest/deploy models, champion/challenger và reporting. SAS công bố Python/R/SAS model integration và governance workflow. Paper MRM 2016 minh họa drilldown theo model families/business units; là tài liệu lịch sử.

**Bài học đề xuất:** model status và evidence quan trọng như metric. Retail monitor đọc saved final test/calibration; mortgage drift vẫn unavailable khi chưa có model/reference/mature labels. Không tạo drift PSI hoặc daily performance bằng số giả.

[Credit Risk Management](https://www.sas.com/en_sg/solutions/risk-management/solution/credit-risk-management.html) · [MRM paper lịch sử](https://support.sas.com/resources/papers/proceedings16/SAS6485-2016.pdf).

## 8. FIS — Credit Assessment / Commercial Lending Suite

**Ai dùng / công việc:** commercial credit officers và relationship managers quản lý spreading, customer risk rating, PD/LGD và commercial lifecycle. FIS mô tả centralized commercial credit data và integrated workflows.

**Bài học đề xuất:** tổng quan phải dẫn sang hồ sơ/phân tích và hành động review có bằng chứng. CreditAtlas có SEC filing facts, bankruptcy benchmark và SBA aggregates riêng; chưa có borrower master hay full commercial loan file để tạo unified rating/memo như lending system.

[FIS Credit Assessment](https://www.fisglobal.com/products/fis-commercial-lending-suite/fis-credit-assessment).

## 9. Numerix — Oneview Counterparty Credit Risk

**Ai dùng / công việc:** counterparty risk desks xem EE/EPE/PFE, margin/collateral, trade-level exposure, pre-deal impact và capital reporting. Hãng công bố dynamic drilldowns và intermediary result analysis.

**Bài học đề xuất:** risk measure phải có trade/netting/CSA scope, không chỉ currency total. CreditAtlas chưa có derivatives/CSA/market paths; không bổ sung PFE panel giả. Học cách mở chi tiết calculation và assumptions từ summary; phần này sẽ cần domain riêng sau khi có trade inputs.

[Oneview CCR](https://www.numerix.com/oneview-counterparty-credit-risk).

## 10. Experian — account management / monitoring

**Ai dùng / công việc:** quản lý accounts để theo dõi credit changes, derogatory information, trends và điều chỉnh policy. Account-management page công bố scoring/monitoring customer base; business monitoring công bố reports và change alerts.

**Bài học đề xuất:** một signal cần change history và baseline. Historical static UCI không đủ cho ongoing bureau-change alerts. CreditAtlas hiện theo dõi source availability/qualification, không giả bureau score update. Muốn customer watchlist cần authorized customer/account identifiers và event feed.

[Account management](https://www.experian.com/business-information/account-management-solutions) · [Business monitoring](https://www.experian.com/small-business/business-credit-monitoring).

## 11. nCino — Analyst Digital Partner / portfolio review

**Ai dùng / công việc:** commercial credit teams; webinar 2026 mô tả early-warning monitoring, covenant testing, relationship reviews, financial spreading và human oversight. Đây là vendor-published capability/use-case, không là benchmark độc lập về productivity.

**Bài học đề xuất:** monitor nên đưa analyst từ evidence sang review nhanh, nhưng review action không phải approval tự động. CreditAtlas giữ source-bound versions; chưa có identities/RBAC/approval matrix, covenants hoặc customer lifecycle để tạo bank workflow đầy đủ.

[Webinar use cases](https://info.ncino.com/WBR-2026-03-18-AnalystDigitalPartners.html).

## 12. CreditRiskMonitor — company monitoring

**Ai dùng / công việc:** commercial/trade-credit teams theo dõi watchlists, financial data và risk indicators. Product page mô tả dashboards, alerts và financial analysis.

**Bài học đề xuất:** queue phải searchable/filterable và mở evidence liên quan. CreditAtlas không tái tạo FRISK/proprietary scores, news feed hoặc company coverage; chỉ sử dụng data/model gaps được API xác nhận. Danh sách này là investigation queue, không score-ranked list of distressed companies.

[Platform](https://www.creditriskmonitor.com/solutions/creditriskmonitor-platform/).

## 13. Taktile — Case Manager

**Ai dùng / công việc:** analyst quản lý case queues, configurable workspaces/templates, audit history và workflow analytics. Product page mô tả case investigation/human-in-the-loop workflows.

**Bài học đề xuất:** mỗi row cần rationale, evidence và next action. Monitor queue mở đúng existing tab; data/policy interpretation không bị chìm trong plan. Chưa hiển thị assigned reviewers, due dates, SLA breach hoặc adjudication khi app chưa có operational identity/task service.

[Case Manager](https://www.taktile.com/case-manager).

## 14. Regnology — RRiH Ascend / OneSumX heritage

**Ai dùng / công việc:** CFO/CRO và treasury/risk teams. Regnology thông báo hoàn tất mua FRR của Wolters Kluwer ngày 01/12/2025. Thông báo 30/06/2026 về Risk Hub Ascend mô tả tích hợp ALM, liquidity, market/credit risk, profitability và stress testing với governed intelligence. Đây là thông báo hãng, chưa phải kiểm định độc lập về hệ thống. Các URL OneSumX cũ redirect/404 nên không dùng để xác nhận product hiện hành.

**Bài học đề xuất:** finance-risk dùng source/conventions chung, nhưng risk measures vẫn có inputs và qualification riêng. CreditAtlas giữ actual principal và conditional ECL/scenarios tách rõ; chưa certified accounting/capital output.

[Acquisition completed](https://www.regnology.net/en/resources/news/regnology-completes-acquisition-of-wolters-kluwers-finance-risk-regulatory-reporting/) · [Risk Hub Ascend, June 2026](https://www.regnology.net/en/resources/news/regnology-risk-hub-ascend-delivers-ai-intelligence-to-balance-sheet-and-enterprise-risk/).

## 15. Những thay đổi đã triển khai cho CreditAtlas

| Câu hỏi | Thành phần monitor | Evidence / giới hạn |
|---|---|---|
| Chỉ số nào cần đọc ngay? | Năm KPI cards, riêng domain | Retail saved AUC; mortgage D3 count; SBA records; USD principal; ABS pool — không cộng chung |
| Credit quality thay đổi thế nào? | D3 history, count/UPB, 12/36/all periods | Native monthly shares; state-usable denominator; observed stock, không phải PD |
| Balance tập trung ở đâu? | Six geographic buckets | USD principal share; same Freddie import; source observations, không phải holdings |
| Model probability có đáng đọc? | Retail reliability + saved metrics | Frozen random holdout; chưa OOT; đọc bins có support |
| Business outcomes có scope gì? | SBA 7A/504 composition | Program-specific denominators, source stock status; chưa fixed-horizon default |
| ABS cashflow thay đổi thế nào? | Pool vs total-note runoff | Reported periods, conditional replay; không phải projection |
| Cần investigate gì? | Filterable queue, direct workflow action | Source checks/missing model/input/legal qualification; không fake deterioration alerts |
| Có thể tra/export lại? | Native history inspection, lineage, JSON export | Domain/window/queue filters preserved; private aggregate data; read-at khác source as-of |

Các panel tải độc lập; nguồn lỗi có trạng thái riêng. Không chọn import ba dòng EXAMPLE mới nhất làm portfolio thật: monitor dùng pinned verified source-observation import. Nút đọc lại đọc API; không tạo scheduled refresh hoặc rescore holdout. Trang 5 workspace/banner và toàn bộ capability plans vẫn truy cập riêng.

## 16. Để tiến tới operational monitor

1. **Source operations:** acquisition jobs, source/release lag contracts, DQ snapshots và version history. Không dùng tuổi calendar của historical sample làm source-lag alert.
2. **Credit alerts:** entity/account keys, mutable exposure histories, agreed rules/thresholds và mature outcomes. Mỗi alert có event/as-of, evidence, severity rationale và lifecycle.
3. **Work management:** authorized user identities, assignment, due dates, permissions, audit log, concurrent editing và approval rules. Existing research reviews không chứng nhận quy trình ngân hàng.
4. **Model monitoring:** frozen training reference, schema/drift comparisons, consistent features, score logs, labels, calibration/performance uncertainty và OOT gates. Tách data shift khỏi deterioration của borrower.
5. **Portfolio risk:** actual holdings/entity map, risk parameters, currency conversion và legal/security overlap để aggregate đúng; ECL/capital/XVA có independent validation riêng.

Đây là dependencies cho production mở rộng, không là phần đã hoàn thành trong UX release. Xem [50 capability plans](PLAN_WORKBENCH_DETAIL.md) và [trạng thái thực tế](FIVE_WORKSPACES_STATUS.md).
