# Dữ liệu, phân tích KPI và báo cáo Excel

Checkpoint 10/10/2026. Mở **Risk monitor**: phần **Dữ liệu & phân tích KPI** nằm trước các panel tổng quan. Phần này đọc saved historical evidence, không chạy lại model hoặc chọn cutoff theo final holdout.

## Cách sử dụng trong app

1. Chọn domain P1–P5. Nút domain hiển thị số KPI và quality controls trong nguồn hiện có.
2. Với P2/P4/P5, chọn baseline. Auto dùng đúng tháng lịch trước; manual dùng exact prior period; tắt baseline vẫn giữ comparison YoY riêng của P2 khi có support.
3. Trong **Đọc chi tiết một KPI**, chọn chỉ số. Ô chi tiết có actual, đơn vị, công thức/support, diễn giải, population/period, baseline actual, absolute/relative change và evidence IDs. Đổi KPI không thay dữ liệu hoặc model.
4. Đọc bốn bước điều tra trong domain, các nhận xét từ số liệu và toàn bộ bảng KPI. Không coi hướng kiểm tra giả thuyết là nguyên nhân đã xác nhận.
5. Mở các bảng source support, chất lượng dữ liệu và dependencies. Bảng source đầu tiên và bảng KPI thiếu inputs mở sẵn.
6. Lưu analyst review nếu cần ghi judgement, hypothesis và bước kiểm chứng. Snapshot đã capture giữ nguyên qua các revisions.
7. Bấm **Xuất KPI Excel**. Workbook chụp bộ lọc tại thời điểm bấm; thay bộ lọc sau đó không thay workbook đang tạo.

## Coverage theo domain

| Domain | KPI nghiệp vụ | Quality controls | Nội dung phân tích |
|---|---:|---:|---|
| P1 Retail | 18 | 3 | Final population/prevalence, discrimination, calibration, validation policy action/cost/capacity |
| P2 Mortgage | 19 | 11 | Active stock/UPB/D3, baseline/YoY, numerator-denominator decomposition, lifetime migration/episodes/follow-up, observed loss |
| P3 Business | 26 | 3 | SBA program/status/amount coverage; SEC ratios theo issuer/filing; concept conflicts và period support |
| P4 Portfolio | 8 | 3 | Principal/count/zero balance, region concentration/HHI/top-five, exact-cent regional movement |
| P5 Structured | 17 | 2 | Pool/notes/funds/principal, interest/certificate distributions, cash/reserve bridge và source reconciliation |

88 KPI nghiệp vụ và 22 controls là coverage của saved sources hiện tại. Không phải mọi KPI của ngành credit risk. Handbook [KPI_ANALYSIS_GUIDE_VI.md](KPI_ANALYSIS_GUIDE_VI.md) liệt kê actuals, công thức và support; [plan](PLAN_KPI_ANALYTICS_NEXT_VI.md) giữ các inputs/qualification còn thiếu.

## Workbook gồm những gì

**Overview:** phạm vi, bộ lọc, thời điểm đọc UTC, nhận xét và hướng điều tra từng domain. Không cộng loan counts hoặc balances của các nguồn khác grain/overlap.

**KPI:** actuals typed numeric, baseline period/actual, Excel delta, Excel relative delta, app delta và Excel-minus-app. USD, count, share, decimal và declared cost units giữ riêng. Công thức mô tả nghiệp vụ là text. Các KPI actual được capture từ readout; chỉ delta được Excel tính lại từ actual/baseline. Với share, absolute delta lưu ở đơn vị share và định dạng %, tương đương điểm phần trăm; relative delta là % của baseline.

**Data:** toàn bộ bảng support trong domain xuất và source digests được server verify tại export. Những bảng đã định dạng trong app giữ display/exact strings làm bằng chứng; không tự promote các chuỗi amounts/percentages thành input số của Excel. Các inputs tính delta nằm ở KPI.

**Reviews:** records/revisions, owner, judgement, hypothesis, next action, captured filters/scope/digest và original immutable KPI captures. Captured scope có thể khác bộ lọc export hiện tại. Archived QA records được ghi rõ QA trong title/owner, không phải nhận định nghiệp vụ của người dùng.

## Phạm vi kiểm chứng

Server kiểm tra cấu trúc, kích thước và sự nhất quán của readout với snapshot; verify source artifacts theo evidence refs trước export. Server **không tính lại độc lập mọi actual do browser derive**. Builder đối chiếu các phép trừ/relative changes với app, thử baseline zero và unavailable, rồi export cached formula results. Báo cáo chỉ được tạo trên loopback cùng origin; không nhận output path hoặc executable từ browser.

Browser receipt `artifacts/private/kpi-workbook-qa-08a849344ada/receipt.json`: 4 nhóm checks PASS, gồm cả năm dossiers, download workbook all-domain, filtered P2/disabled baseline và mobile/ledger. Từng actual/unit/baseline của 110 rows được đối chiếu JSON; tám comparison formulas đối chiếu independent arithmetic. Regression KPI/baseline: 19 PASS, `artifacts/private/kpi-analysis-qa-95251bc16b81/receipt.json`. Backend: 31 tests PASS, `artifacts/private/kpi-xlsx-tests-20261010.xml`.

Bốn sheets đã được render và kiểm tra; saved XLSX đã được đọc XML độc lập để kiểm tra formula text/cached values và không có error cells. Chưa kiểm tra trực tiếp recalculation trong Microsoft Excel desktop. Workbook dùng scalar IF/AND/ISNUMBER và phép toán; không macros, external formula links hoặc What-If Data Tables.

## KPI còn cần inputs

- **P1:** approval/reject populations, later-cohort drift/OOT và actual profit inputs.
- **P2:** multi-vintage matured horizon labels để qualified PD12; loss/recovery/discount contracts và support để qualified LGD/EL.
- **P3:** borrower cashflow/debt schedules/covenant terms cho DSCR/ICR/headroom; borrower linkage nếu muốn kết hợp populations.
- **P4:** ownership/EAD, qualified PD/LGD, staging/scenarios/discounting để EL/ECL; record linkage để phân biệt entries/exits/paydowns.
- **P5:** forward collateral forecasts, full legal waterfall và instrument/discount curves để valuation, duration/DV01/spread sensitivity.

Những KPI thiếu inputs giữ unavailable và dependency trong app. Historical descriptive calculations không tự trở thành institution-qualified risk models.
