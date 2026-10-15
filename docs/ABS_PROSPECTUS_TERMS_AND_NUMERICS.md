# WOART 2025-A: điều khoản được đọc và numerical reconciliation

## Nguồn và phạm vi

Prospectus chính thức ngày 22/01/2025:
https://www.worldomni.com/abs/WOART_2025-A_Final_Prospectus.pdf

File nguồn đã tải ở `private evidence omitted from public release`,
SHA256 `dc34695537492fd7f452e3dd735d4938e76eedde87f441e127e94875e708e653`.
Module chỉ hỗ trợ đúng document version này. `abs_contract.py` lưu terms
được review thủ công từ các trang liên quan, không tự claim parser đầy đủ
cho mọi prospectus hoặc executed trust documents.

Số trang dưới đây là **PDF page một-based**, khác printed page: ví dụ PDF94
là trang in85. Đã đọc các trang liên quan; đã render/quan sát cover, page94
và glossary page151 để kiểm tra bảng, day count và definitions. Text extract
không dùng thay visual review của bảng cover.

Terms run hiện tại **`abs-terms-4367aa1a54a3`** trên canonical case
**`abs-case-fcbaa9573ac3`**. Status RECONCILED_REVIEWED_PROSPECTUS_TERMS,
626 checks/0 failed,20 periods Jan2025–Aug2026.

## Catalogue tranche và conventions

| Issued tranche | Initial face USD | Coupon fraction | Day count | Final scheduled payment |
|---|---:|---|---|---|
| A-1 | 241,400,000 | 0.04411 fixed | ACT/360 | 2026-02-17 |
| A-2a | 309,760,000 | 0.0449 fixed | 30/360 | 2028-04-17 |
| A-2b | 110,000,000 | reported SOFR + 0.0033, floor0 | ACT/360 | 2028-04-17 |
| A-3 | 419,760,000 | 0.0473 fixed | 30/360 | 2030-03-15 |
| A-4 | 89,300,000 | 0.0486 fixed | 30/360 | 2030-11-15 |
| B | 36,760,000 | 0.0508 fixed | 30/360 | 2030-11-15 |
| C | 18,380,000 | 0.0517 fixed | 30/360 | 2031-10-15 |

Cover PDF1 xác nhận bảy issued tranches, tổng face1.225.360.000USD. D/E
của workbook là template slots, không thêm vào issued catalogue.
Closing29/01/2025, first payment18/02/2025.

PDF93–94: A-1/A-2b dùng actual ngày từ closing/previous payment đến payment
hiện tại, end-exclusive. Các tranche fixed khác dùng kỳ ngày15 với30 ngày,
initial16ngày. Vì vậy initial actual20ngày khác initialfixed16ngày; business-day
delay của payment không kéo dài fixed coupon accrual. Module dùng payment
dates từ báo cáo đã verify; chưa xây future business-day calendar.

SOFR input là giá trị báo cáo, chỉ kiểm tra spread/floor và arithmetic.
Chưa độc lập xác minh fixing observation, publication/revision hoặc benchmark
fallback. Không lấy coupon giả định trong bảng minh họa cash flows của
prospectus làm coupon hợp đồng; catalogue dùng cover terms.

## Principal và credit enhancement

PDF95/110: principal theo A-1 → nhómA-2 → A-3 → A-4 → B → C.
Nhóm A-2 phân bổ pro-rata theo beginning outstanding balances giữa A-2a/A-2b.
`allocate_principal` nhận **funded principal amount**, không tự coi nó là
contractual principal due. Không dùng pro-rata toàn bộ bảy tranches.
Cent convention của implementation: HALF_UP cho A-2a, residual cent cho
A-2b và cap mỗi số dư. Đây là convention được khai báo của numerical module;
prospectus chưa xác minh rounding tie chính xác. Source comparison tolerance
0,01USD. Tiền vượt tổng notes được trả thành `unallocated`, không âm balances
hoặc biến thành realized loss.

PDF111/151: OC target dựa trên adjusted pool, có floor theo initial adjusted
pool. Implementation max(0,009 × endingpool,0,005 × initialpool), round cents.
Actual OC=endingpool−endingnotes. Reserve base0,0025 × initialadjustedpool;
source initialdeposit3.063.404,27USD. Prospectus cho phép increase trước
closing; current source không thể biến baseformula thành universal restriction.
YSOA giữ theo publisher report, chưa reconstruct từ từng khoản vay.

PDF100: review trigger so **>**0,047, numerator hơn60days delinquent,
denominator endinggrossreceivables trước trừYSOA. Đây là review/vote trigger,
không tự acceleration hoặc chuyển waterfall. Source fraction được đối chiếu
ở độ chính xác0,0001fraction, boolean dùng unrounded ratio.

PDF105: standard monthlyservicing fee1%/12 × beginninggrossreceivables.
19 kỳ tháng chuẩn kiểm tra đạt. Initial fee cần proration; triển khai hiện tại
không suy ra convention từ actualfee hoặc tự fit để làm checkPASS.

## Đã kiểm tra gì

626 checks gồm20period ×30checks,7initialfaces,19standardfees:
actual/fixeddays,7coupons,7baseinterest,7fundedprincipalallocations,
unallocatedprincipal,OCtarget/actual,reserveformula/sourceamount,delinquency
sourcefraction và reviewflag. Bảy slot không có reportedcarryovershortfall
trong cả20kỳ. Baseinterest comparison có điều kiện này; không tạo full
carryover/unpaid-interest model. Dữ liệu nguồn/typed schema vẫn được
`abs_servicer.verify_case` đọc lại và rederive trước termchecks.

`abs_contract.verify` rebuild terms/evidence từ original source, so toàn bộ
receipt; qualification hoặc arithmetic bị sửa không được chấp nhận chỉ bằng
việc đổi file hash. Qualifications full_contractual_waterfall,
loan_level_projection,benchmark_fixing_independently_verified,
legal_regime_certified,executed_agreements_and_amendments_verified đềuFalse.

17new contract/numerical tests kiểm tra catalogue isolation, initialdaycounts,
floatingfloor/missingbenchmark,OCfloor,priority/pro-rata,centties/excesscash,
negative/sub-cent/nonfinitecash,unknown/missingbalances,float/boolinputs,
alteredqualificationclaim. Software full-suite result được ghi tại statusdoc.

Full software regression: **772PASS** (375engine+397application),127,47s.
Independent exact-rational benchmark `abs-interest-audit-2dc6b99f32f5`
**140checksPASS**,0failed,maxsource/benchmarkdifference0,00USD. Dùng
Fraction từ coverrate constants, sourcebalances/reportSOFR và dateintervals;
không gọi các hàm Decimalinterest/coupon/cents của implementation. Mỗi khoản
lưu exactnumerator/denominator và kết quả centrounding. Nó xác minh baseinterest
numerics, chưa xác minh independentSOFRfixing hoặc carryover/acceleration.

## Phần phải làm tiếp để đạt full P5

Update: conditional pre-acceleration state machine và declared maturity/
terminal scenarios đã có trong [ABS_WATERFALL_WORKFLOW.md](ABS_WATERFALL_WORKFLOW.md).
Nó chưa đóng các full-obligation/legal/event qualification gates dưới đây.

1. Lấy executed agreements/amendment/event evidence hoặc giữ legalstate
   chưa xác nhận. Asset-level ABS-EE vẫn là source track riêng, không được
   thay bằng 20aggregate tháng.
2. Pre-acceleration cash state machine đủ priority clauses, principal due
   và paid riêng, reviewer annualcap/unpaidfees, interestcarryover, reserve
   draws/replenishment, finalmaturity treatment và residual/redelivery.
3. Acceleration và benchmarkfallback là nhánh khác, cần inputs/terms và
   independent benchmark. Không silently áp dụng pre-acceleration cho chúng.
4. [ABS app](ABS_APP_WORKFLOW.md) đã có source periods, issued notes,
   source comparisons, selected terms, qualification và private period export.
   Scenario input workbench và full term/obligation history còn tiếp tục.
5. Scenario projection từ collateral assumptions; không biến reported cash
   thành forecast hoặc cho rằng đã có loan-level loanstate persistence.

## Chạy và kiểm tra

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\build_abs_terms.py abs-case-fcbaa9573ac3
.\.venv\Scripts\python.exe -X utf8 .\scripts\audit_abs_interest.py abs-terms-4367aa1a54a3
```

Mỗi build tạo receipt mới, không sửa receipt cũ. Termsprototype
`abs-terms-a59c935b1af3` giữ lịch sử nhưng không current vì method đã thay
bằng defensive copy của pageevidence; dùng termsID hiện tại ở trên.
No new mortgage/model finalholdout inference; scope ở nguồn ABS và numerical
methods mới. Full suite goal vẫn mở.
