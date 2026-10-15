# WOART 2025-A cash waterfall

## Hiện trạng và evidence

`abs_waterfall.py` triển khai state machine **pre-acceleration được khai báo**,
nhận đủ inputs và tạo ledger due/paid/shortfall/cash/reserve sau mỗi bước.
Không chọn regime bằng Delinquency Trigger; review trigger khác acceleration.

Current source replay **`abs-waterfall-762205cf20db`** trên terms
`abs-terms-4367aa1a54a3` và canonical `abs-case-fcbaa9573ac3`:
**20 kỳ / 220 stage rows / 720 đối chiếu với nguồn / 0 khác biệt vượt 0,01USD**.
Status CONDITIONAL_REPORTED_REPLAY_RECONCILED, chưa actual certified legal
waterfall. Original selected prospectus terms ở
[ABS_PROSPECTUS_TERMS_AND_NUMERICS.md](ABS_PROSPECTUS_TERMS_AND_NUMERICS.md).
Đã đọc PDF107–108/110–111/150–151 và render/quan sát priority chart PDF109.
Final agreements/amendments chưa được xác minh.

Independent accounting **`abs-waterfall-audit-b0f4a1bcef60` PASS**:
580 SQL check rows gồm220stage,200stagecontinuity,140tranchebalances,
20periodcash/sourceendpoint checks. Đọc ledger values, không dùng claimed
conservation delta/PASS của engine. Mỗi stage kiểm tra cash/reserve chuyển
đúng, paid=availablecash+reservedraw, due=paid+shortfall, nonnegative state.
SQL definitions và source receipt hash nằm trong audit JSON. Check tiền
không chứng nhận legal priorities hoặc đủ obligations.

## Inputs cần đủ và đúng scope

Toàn bộ inputs bắt buộc; key lạ bị từ chối. Money là nonnegative cent Decimal
hoặc exact string; không nhận float hoặc tự điền zero. Seven issued balances
và seven interest due entries riêng; D/E source slots không thành instruments.

- `input_basis`: DECLARED_SCENARIO hoặc CONDITIONAL_REPORTED_REPLAY.
- `regime`: PRE_ACCELERATION; accelerated/unknown bị từ chối.
- Payment date, net Available Funds, beginning notes, interest due, ending
  adjusted pool và OC target. Available Funds đã trừ servicing fees.
- Beginning reserve/required reserve, tổng reviewer fees due (gồm chưa trả),
  đã trả YTD, **payment-calendar-year** của YTD và reviewer sponsor affiliation.
  Caller phải reset calendar year rõ ràng, không dùng collection year thay.
- Certificate redeposit amount là instruction được khai báo, không suy ra
  từ funds còn lại.
- `maturity_policy`: BLOCK_IF_OUTSTANDING hoặc
  DECLARED_SEQUENTIAL_FLOOR_THEN_RESERVE_CURE.
- `terminal_release_instruction`: BLOCK_IF_TERMINAL,
  HOLD_PENDING_FINAL_INSTRUCTION hoặc DECLARED_FINAL_DISTRIBUTION_COMPLETE.

Engine nhận tổng interest due đã được thiết lập bên ngoài. Unpaid interest
được xuất để nối kỳ sau; chưa tự tính interest-on-shortfall/carryover khi chưa
có legal permission/rate/history. Không coi balance0 là không còn interest due.

## Luồng pre-acceleration

| Bước | Khoản trả | Reserve có thể tài trợ |
|---|---|---|
| 1 | Reviewer, trong cap150.000USD/calendar year còn lại | Có nếu không phải sponsor affiliate |
| 2 | Class A interest, pro-rata theo dues | Có |
| 3 | First priority principal | Có |
| 4 | Class B interest | Có |
| 5 | Second priority principal | Có |
| 6 | Class C interest | Có |
| 7 | Third priority principal | Có |
| 8 | Reserve replenishment đến required amount | Không; cash chuyển nội bộ vào reserve |
| 9 | Regular principal, trừ các priority allocations đã trả | Không |
| 10 | Reviewer fees còn lại | Không |
| 11 | Certificate residual, tách cashpaid và instructed redeposit | Không |

Principal threshold uses **original beginning balances**, nhưng trừ các
priority allocations **đã trả** trước đó. Phân phối principal luôn theo
A-1 → A-2a/A-2b pro-rata → A-3 → A-4 → B → C. Không gọi second priority
principal là payment trực tiếp cho Class B. Class A interest thiếu tiền được
chia pro-rata theo interest dues, không theo note faces.

Cent conventions: A-2 HALF_UP cho A-2a/residual cho A-2b; A-interest
integer-cent largest remainder với stable tranche order khi tie. Source
comparison0,01USD; rounding rules này không claim executed agreement certified.

Reserve draw chỉ lấy đúng funding gap của eligible stage, không đưa dư vào
cash cho bước khác. Sponsor affiliate fee không lấy reserve. Reserve deposit
là transfer nội bộ, **không** cộng thêm vào external cash distributions khi
đã giữ nó trong ending reserve. Unfunded step9 có thể là thiếu tiền để build
OC; không tự payment default hoặc realized tranche loss. Priority shortfalls
có thể overlap, không cộng chúng thành tổng loss/unpaid principal.

## Maturity và terminal branches

Khi caller chọn declared maturity policy, principal due được nâng đến mức
clearing mature class cùng các senior groups theo sequential order. Sau
regular principal, phần còn thiếu của mature groups được cure từ reserve theo
tranche priority; A-2 cure chia pro-rata. Placement/convention này được
khai báo, chưa certified bằng executed agreements. Không trả reserve cho
unmatured junior tranches trong mature-class cure.

Sau khi notes đã trả hết, caller có thể giữ reserve chờ final instruction.
Declared final distribution chỉ cho release reserve riêng cho **depositor**
khi notes/interest/reviewer obligations đã settle và không có collection
redeposit. Reserve release khác certificate cash distribution; conservation
giữ cả hai recipient flows. Chưa xác minh instruction từ bên liên quan ngoài
scenario declaration. Default source replay block cả mature-outstanding và
terminal branches nếu source thiếu evidence.

## Historical replay có điều kiện gì

Tất cả20sourceperiods không có reported reserve draw hay remaining mature
A-1 balance. Engine tính baseinterest từ reviewedcoupon/daycount/reportSOFR;
principal allocations được tính lại từ Available Funds/pool/OC/beginningnotes,
không dùng reported principal paid làm input để tạo matching result.

Reviewer due/YTD giả định0; source paid0 không chứng minh due0. Regime được
khai báoPRE_ACCELERATION, không legal-state-certified. Priorcarryover giả
định0; báo cáo servicing/interestshortfall0 là prerequisite, không chứng minh
obligation history đầy đủ. Source reviewer paid/redeposit/shortfall nonzero
bị gate để yêu cầu source mapping/history mở rộng, không bị xóa hoặc fill0.

Tháng đầu, step9 requested10.704.708,94USD nhưng paid6.321.560,55USD;
unfunded4.383.148,39USD. Đây là illustrative OC-build gap trong conditional
replay, không loan/default loss. 720 đối chiếu bao gồm11source distribution
lines,7tranches×interest/principal/endingbalance,2reserve và2conservation
checks mỗi kỳ.

Qualifications **full_contractual_waterfall, legal_regime_certified,
obligation_completeness_certified, realized_loss_model đềuFalse**. Scenario
branches không biến assumption thành realized event.

## Verification và việc còn lại

31 new focused tests: due/paid distinction,starvation,reserve exhaustion,
sponsor-fee restriction,YTDcap,OC/reserve ordering,interestpro-rata,
large exact cents,A-2 layers,certificate redelivery,unknowninputs/regimes,
explicitmaturity/terminal gates,maturitycures,holdvsdepositorrelease,
unpaidobligations/collectionredeposit block,unmutatedinputs và saved
assumption-tamper rejection. Full regression result ở status document.

`verify_replay` rederive từ original verified source/terms và method pins,
so toàn bộ inputs/assumptions/ledger/checks; không chỉ tin hash hoặc savedPASS.
Prototype receipts trước method freeze giữ historical, không sửa chúng để
cho current verifier chấp nhận. Dùng current IDs ở đầu tài liệu.

[ABS app/API/private period exports](ABS_APP_WORKFLOW.md) đã được triển khai.
Tiếp theo: scenario input workbench, full obligation/event/amendment
evidence; automated period-state/carryover conventions, acceleration,
benchmarkfallback,collateral projection/tranche loss/valuation/positions.
Final maturity/terminal declared-scenario support đã có nhưng không thay
certified actual event evidence. Full P5 và full50-capability suite vẫn mở.

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\build_abs_waterfall.py abs-terms-4367aa1a54a3
.\.venv\Scripts\python.exe -X utf8 .\scripts\audit_abs_waterfall.py abs-waterfall-762205cf20db
```
