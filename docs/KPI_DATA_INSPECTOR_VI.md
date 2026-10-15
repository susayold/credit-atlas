# CreditAtlas — tra cứu dữ liệu và phân tích KPI

Ngày cập nhật: 10/10/2026. Mở **Risk monitor → Dữ liệu & phân tích KPI**.
Năm nhóm P1–P5 giữ 88 KPI và 22 quality controls hiện có. Không phải tất cả
chỉ số đều có actual hoặc baseline: các trường thiếu giữ `Unavailable`.

## 1. Quy trình đọc một chỉ số

1. Chọn domain; đọc population và kỳ trong scope.
2. Tìm tên KPI, công thức hoặc diễn giải. Lọc Có số liệu / Thiếu số liệu /
   Có baseline. Bộ lọc này chỉ tra cứu catalogue, không đổi population tính.
3. Bấm tên KPI để mở hồ sơ: actual, đơn vị, công thức, scope, baseline,
   delta tuyệt đối và tương đối nếu được hỗ trợ, evidence ID và bước điều tra.
4. Với các tỷ số SEC: xem tử/mẫu USD exact, support, start/end, accession
   và source candidates. Có thể đối chiếu chính kết quả exact của backend.
   Với D3 share, unknown-state share và loss resolution coverage: xem trực tiếp
   hai đầu vào đã cung cấp trong snapshot. Stock kỳ cuối và lifetime loss subset
   có grain khác nhau; ngày/grain của đầu vào được giữ trong hồ sơ.
5. Chọn bảng ở **Tra cứu dữ liệu phân tích**, tìm trên mọi cột, chuyển trang
   25 dòng và tải CSV của toàn bộ các dòng đang lọc, không chỉ trang hiện tại.
6. Đọc quality controls, danh sách KPI thiếu dữ liệu và mở workspace nghiệp vụ
   để kiểm tra cohort, transition, filings hoặc cash ledger cụ thể.

Các metric supplied/saved khác giữ kết quả của pipeline; không giả lập input
trace từ bảng đã làm tròn. Bảng hỗ trợ CSV giữ chính values đang tra cứu, có
BOM UTF-8 và quote cell; ký tự mở đầu công thức được escape. Đây là CSV bảng
phân tích đã định dạng, không thay raw data dump. Monitor JSON giữ source
payloads, metadata và metric details; nút Excel hiện có vẫn dùng metric schema cũ.

## 2. Nội dung phân tích theo domain

| Domain | Dữ liệu đối chiếu | Câu hỏi phân tích | Không được suy ra |
|---|---|---|---|
| P1 Retail | Split support, validation candidates, reliability bins, policy assumptions/actions/costs | Ranking, calibration, base rate, scenario review capacity và chi phí khai báo | Actual application approval rate, realized profit, temporal stability |
| P2 Mortgage | Monthly history, segments, lifetime transition cells, confirmed episodes/follow-up, loss component bridge | D3 numerator/denominator movement, count/UPB, migration và coverage của observed loss | Qualified PD12, LGD/EL hay sustained cure từ stock giảm |
| P3 Business | SBA program/status denominators; SEC fields và concept candidates riêng cho từng issuer | Program outcomes, amount coverage, liquidity/leverage/margin/cashflow ratios với filing-specific inputs | Join SBA borrowers với SEC issuer; covenant/DSCR/default probability |
| P4 Portfolio | Region partitions, principal, comparison imports, exact-cent region bridge | Concentration, HHI, top shares, amount movement và partition reconciliation | Owned exposures, qualified EAD/EL/ECL từ source principal |
| P5 Structured | Collection/payment periods, balances, conditional replay allocations, cash/reserve ledger | Pool/note runoff, reported uses, reserve moves, unpaid amounts và residual checks | Full legal trigger compliance hoặc forward valuation |

## 3. Đọc biến động

- Share delta đọc theo điểm phần trăm; relative delta là một phép tính khác.
- Auto baseline lấy đúng tháng lịch trước, không lấy kỳ gần nhất thay thế.
- Baseline có thể tắt hoặc chọn exact prior period khi nguồn hỗ trợ.
- Decomposition và region bridge là phân rã số học; cần borrower/event data
  để kiểm tra giả thuyết nguyên nhân.
- Chưa có approved targets/risk appetite. Tăng/giảm không tự chuyển thành
  màu tốt/xấu hoặc một kết luận ra quyết định.

## 4. Tài liệu sâu và phần cần tiếp tục

[88 KPI và công thức chi tiết](KPI_ANALYSIS_GUIDE_VI.md) là tài liệu tra cứu
từng chỉ số hiện tại. [Plan tiếp theo](PLAN_KPI_ANALYTICS_NEXT_VI.md) giữ
qualification/input gates cho PD/LGD, affordability, collections, DSCR/covenant,
institutional ECL và structured valuation. [Annual trends](SEC_ANNUAL_TRENDS_VI.md),
[interest coverage](SEC_INTEREST_COVERAGE_VI.md) và
[maturity principal](SEC_DEBT_MATURITIES_VI.md) bổ sung phân tích doanh nghiệp
ngoài catalogue 88 KPI hiện tại.

Checkpoint11/10: cả88KPI đã có source/input mapping:61derived,26saved
aggregates và1required-input EL. Mỗi input giữ source namespace, JSON pointer,
value supplied, units và context. Saved AUC/Brier/logloss vẫn là aggregate
pipeline; không refit/rescore hay tái tạo từng prediction. Derived source
checks hiện trong hồ sơ; missing giữ unavailable. JSON export giữ trace_sources
để pointer không bị lệch khi bảng monthly chỉ hiển thị36tháng. Chưa phải
record-level input trace cho mọi KPI. Đây là phạm vi cần mở rộng tiếp, cùng với
compatible-history baselines và dữ liệu nghiệp vụ còn thiếu.
