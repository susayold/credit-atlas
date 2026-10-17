# Apple FY2025 — truy vết KPI từ code đến filing, kỳ và đơn vị

Ngày kiểm tra: **17/10/2026**. Đây là một crosswalk N02/N03 cụ thể cho P3 Issuer Financials, được lập từ code hiện hành, read-only readback của SEC view local và đối chiếu với SEC EDGAR. Nó không phải chứng nhận đầy đủ mọi route, toàn bộ XBRL dimension, hay mọi raw dataset trong repo. Bản máy đọc được: [apple-fy2025-kpi-trace-2026-10-17.json](data/apple-fy2025-kpi-trace-2026-10-17.json).

## 1. Một filing, hai đường lấy dữ liệu

SEC EDGAR xác nhận Apple Inc., CIK **0000320193**, Form 10-K, accession **0000320193-25-000079**, nộp ngày **2025-10-31**, kỳ kết thúc **2025-09-27**. SEC filing index ghi nhận cùng form, accession, ngày nộp và report period; file 10-K chính là aapl-20250927.htm. [SEC filing index](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.html) · [SEC 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm).

P3 financial statement/KPI route nhận facts từ acquisition **SEC CompanyFacts + submissions API snapshot**. Code sec_financials.py chuẩn hoá từng fact theo CIK, accession, form, filed date, concept, unit, start/end context; sec_views.py kiểm receipt/method trước khi report; kpi-analysis.js gắn bốn KPI của issuer vào numerator/denominator fields và accession/report date/filing date; app.js hiển thị các tỷ lệ. SEC mô tả CompanyFacts là XBRL facts đã trích xuất từ nhiều hồ sơ và cập nhật real time khi filing được disseminate; API tổng hợp facts theo non-custom taxonomy và toàn filing entity. Vì vậy đây là current API snapshot, không phải bản chụp lịch sử point-in-time. [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

Ba receipt-verified Apple issuer-hosted artifacts trong source register là **một** filing, không phải ba releases. P3 CompanyFacts source là một acquisition riêng: hai đường dữ liệu được crosswalk bằng CIK/accession/form/date/concept/context và giá trị báo cáo; không giả định issuer-hosted files byte-identical với SEC-hosted copy. Hai bản HTML/XBRL khác kích thước ở SEC index so với local issuer copies, nên byte parity vẫn chưa chứng minh. Raw source files và private receipts vẫn private.

## 2. KPI đã nối đúng source field, period, unit và cách tính

P3 report local, đọc chỉ đọc với filing-date cutoff **2026-10-10**, chọn đúng accession nêu trên. Các exact values bên dưới lưu bằng USD; bảng 10-K trình bày cùng amounts theo triệu USD. Ratios được tính từ exact decimal values, không dự phóng hay điền missing. Hai balance-sheet metrics dùng context instant tại 2025-09-27. Các dòng income/cashflow là annual duration 2024-09-29–2025-09-27, đủ 364 ngày inclusive và cùng kỳ giữa tử với mẫu.

| KPI / status | Tử số → source concept | Mẫu số → source concept | Kỳ / đơn vị | Giá trị kiểm tra và tính lại |
|---|---|---|---|---:|
| Current ratio — supported | Current assets **USD 147,957m** → AssetsCurrent | Current liabilities **USD 165,631m** → LiabilitiesCurrent | Instant, 2025-09-27; USD / USD | 147,957 / 165,631 = **0.893292922x** |
| Liabilities / assets — supported | Liabilities **USD 285,508m** → Liabilities | Assets **USD 359,241m** → Assets | Instant, 2025-09-27; USD / USD | 285,508 / 359,241 = **79.475338283%** |
| Net income margin — supported | Net income **USD 112,010m** → NetIncomeLoss | Revenue **USD 416,161m** → RevenueFromContractWithCustomerExcludingAssessedTax | Annual duration, 2024-09-29–2025-09-27; USD / USD | 112,010 / 416,161 = **26.915064122%** |
| Operating cashflow / revenue — supported | Cash from operating activities **USD 111,482m** → NetCashProvidedByUsedInOperatingActivities | Revenue **USD 416,161m** → RevenueFromContractWithCustomerExcludingAssessedTax | Same 364-day annual duration; USD / USD | 111,482 / 416,161 = **26.788190148%** |

SEC-filed statement tables display current assets, current liabilities, assets and liabilities at the fiscal year end, and net sales, net income and operating cash generated over the 2025 fiscal period. Those values cross-check the P3 CompanyFacts readback. The periods align with the 10-K, not with the date the local file was downloaded. [SEC 10-K financial statements](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm).

These are descriptive consolidated-company ratios. Current ratio below 1 means the reported current liabilities exceed current assets under those statement definitions; it is not, by itself, a default prediction or liquidity failure label. Liabilities/assets is a simple balance-sheet share, not a covenant leverage ratio. Net margin and OCF/revenue do not measure scheduled debt service.

## 3. KPI chưa có giá trị và vì sao

For FY2025, the saved P3 coverage route has no candidate for its default selected InterestExpenseNonoperating fact in this accession. The code returns **Unavailable** for operating-income coverage and does not automatically switch to InterestExpense, InterestExpenseDebt, interest paid, or a constructed value. This is correct missing-data behavior. Do not impute interest expense or calculate DSCR from operating cashflow.

The filing-specific note/XBRL work can support limited debt disclosures and issuance-group analysis. It still does not give a verified individual-series carrying balance, actual payment ledger, complete coupon schedule, contractual debt-service denominator, facility-level DSCR, legal covenant threshold/status, EAD, or issuer PD. These require additional evidence beyond a tag or ratio.

## 4. Availability, rights, and what remains open

- **Period end** is 2025-09-27; **public filing date** is 2025-10-31. The app report used cutoff 2026-10-10 to choose the then-current annual snapshot. Never use retrieval time as report date or fact-availability date.
- The current SEC API data model and filed-date filter do not establish a historical point-in-time backtest. historical_availability_qualified remains false.
- The public 10-K can be cited, but the issuer-hosted source payloads remain private. Local issuer files and SEC-hosted files have different byte sizes; byte parity, redistribution permission for each payload, and software/output reuse review are still open.
- This crosswalk closes only the trace for four selected P3 statement ratios for one Apple filing. It does not accept all SEC issuer KPIs, debt-service/covenant analysis, other issuers, every route/export, or the 26/50 capability ledger.

## 5. Relevant code paths

- src/credit_atlas/sec_financials.py — selected concepts, instant/duration context, accession and filed-date matching, supported/missing/ambiguous states, and exact ratio calculation.
- src/credit_atlas/sec_views.py — verified private SEC view, issuer CIK and filing selection.
- src/credit_atlas/sec_trends.py — original 10-K selection, filing cutoff and period comparability.
- src/credit_atlas/sec_coverage.py — explicit interest-expense concept and no automatic alias fallback.
- apps/web/kpi-analysis.js — four P3 KPI formulas, trace inputs and accession/report/filing date.
- apps/web/app.js — statement KPI display and separate workbench routes.

No source fact was forecast, imputed or filled in this review. A null remains null.
