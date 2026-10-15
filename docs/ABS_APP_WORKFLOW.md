# P5 — Auto ABS Cashflow Evidence app

Snapshot hiện tại: `abs-view-1ea94d36115b`, từ waterfall
`abs-waterfall-762205cf20db`, canonical `abs-case-fcbaa9573ac3` và reviewed
terms `abs-terms-4367aa1a54a3`. World Omni 2025-A có 20 collection periods,
Jan 2025–Aug 2026; mỗi kỳ có 36 đối chiếu nguồn. Đây là **conditional
reported replay**, không phải legal-state hoặc full-obligation certification.

## Đọc kết quả trong ứng dụng

 Mở `http://127.0.0.1:8785/?view=abs&workspace_tab=absee-profile` để xem ABS-EE coverage, peer/anomaly QA, Toyota 2022-B longitudinal history và Toyota 2024-B validation deal, certificate tie-outs, temporal holdout và feature availability mới nhất. Waterfall view dùng `http://127.0.0.1:8779/?view=abs&abs_view_id=abs-view-1ea94d36115b`.
Navigation có mục **P5 · ABS waterfall**, độc lập với mortgage run selector.

1. Chọn source collection end. Control ghi cả payment date; collection
   tháng 12/2025 được thanh toán 15/01/2026, YTD reviewer dùng năm 2026.
2. Đọc available funds sau servicing, adjusted pool sau YSOA, reserve cuối
   kỳ và số checks. Đây là source inputs, chưa phải collateral forecast.
3. Bảng waterfall có 11 priorities, due/paid/unfunded riêng, cash used,
   reserve drawn/credited và cash/reserve còn lại sau từng bước.
4. Bảng tranche có bảy issued classes, beginning/ending balances,
   interest due/paid/unpaid và principal paid. D/E template không trở thành
   issued notes. Details cho thấy từng bước trả tranche nào.
5. Bảng source comparisons giữ calculated/reported/delta/tolerance.
   Conservation checks có tolerance zero; source comparisons dùng tolerance
   theo frozen engine. Terms là selected prospectus terms có nguồn liên kết.
6. Biểu đồ pool/notes dùng toàn bộ kỳ trong snapshot. Giá trị trên đồ thị
   hiển thị gần đúng; bảng và private JSON export giữ numeric strings gốc.
7. Export xuất **kỳ đang chọn**, cùng inputs, state ledger, allocations,
   checks, assumptions và qualification. Không chứa đường dẫn máy cục bộ.

Tháng đầu regular principal due 10.704.708,94 USD, paid 6.321.560,55 USD,
unfunded 4.383.148,39 USD. Không cộng priority shortfalls thành credit loss:
thresholds có thể chồng lặp, OC build gap không tự trở thành loan default loss.
Second priority principal thực tế trả A-1 trước; tên priority không có nghĩa
trả trực tiếp cho B. Reserve replenishment là transfer nội bộ.

## Source verification và API

`abs_views.py` rederive source replay qua frozen verifier mỗi lần đọc,
so projection với snapshot và receipt digests/methods. JSON equality phân
biệt false với 0. Source success flags phải là bool và failed count là int;
không đọc một saved PASS để bỏ qua source verification.

| Endpoint | Filters | Kết quả |
|---|---|---|
| `/api/abs-views` | Không có | Verified/unavailable snapshot catalog |
| `/api/abs-view` | `view_id` | Period catalog, selected terms, timeline, scope |
| `/api/abs-period` | `view_id`, optional `period` | Kỳ nguồn; default latest nếu bỏ period |
| `/api/abs-report` | Như abs-period | JSON attachment riêng tư |

Period phải đúng collection end có trong nguồn. Empty/unknown period, future
dates, duplicated query parameters, extra scenario/PD/regime fields bị từ chối.
URL dùng prefix `abs_`; selected snapshot/period giữ qua reload. Fetch kết quả
cũ không ghi đè màn hình khi chuyển kỳ hoặc workspace. Origin/Host chỉ local;
responses no-store, không có public-release approval.

15 focused tests kiểm tra period/payment identity, exact allocations,
unknown filters, forged projections dù cập nhật hash, source receipt changes,
type-confused qualifications, HTTP attachment và origin/duplicate guards.
Browser acceptance chạy actual issuer data bằng `scripts/browser_abs_qa.py`: 
`abs-browser-qa-287c96275587`, **12 checks PASS**, không JS/console error.
Actual first-month OC gap, tranche priority, exact export, payment-year boundary,
URL reload, later A-1 paid-off period, styled chart, 390px mobile và P2/P3/P5
navigation đều đã kiểm tra; desktop/mobile screenshots đã đọc.
Full regression **818 tests PASS** (375 engine + 443 application), 151,16 giây.

## Phạm vi còn lại

### ABS-EE official fields and KPI history

Trong ABS workspace, mở tab **ABS-EE · coverage** để xem monthly aggregate KPI history từ SEC XML chính thức và tab **ABS-EE · định nghĩa trường** để tra Schedule AL mapping cùng field profile. KPI timeline có 20 kỳ/880.773 row-months, ending pool, Pool + YSOA, 31+/61+ delinquency amount/rates, defaulted receivables, certificate recovery/net loss và asset-reported recovery. Chart ratios dùng `Pool Balance + YSOA` làm denominator theo certificate. Field table kiểm tra 15 trường XSD liên quan PTI, balances, due/payment, interest/fee rates, delinquency, zero-balance, charge-off, recovery và repossession; hiển thị XSD type, present/NULL, raw min/max, observed decimal scale và raw code values.

Cross-check hiện có: ending XML balance khớp Pool + YSOA ở 20/20 kỳ; asset charge-off sum khớp certificate Defaulted Receivables ở 20/20; 31+/61+ buckets khớp certificates 200/200 field checks. Cả 939 row-months có zero-balance code 4 đều có charged-off principal amount; không có amount nào ngoài code 4. Asset recovery chỉ exact với certificate ở 3/20 kỳ, nên bảng giữ recovery deltas. Recovery, repossession indicator và proceeds là snapshot/row-month observations, không xem là unique lifetime borrower counts. 6.445 key-month observations biến mất khỏi filing kế tiếp không có reason code ở snapshot trước; không gán nguyên nhân exit.

Dashboard vẫn là aggregate surveillance cho securitization; chưa có individual-loan drilldown hay forecast. Toyota 2022-B hiện có 51 kỳ liên tục, 2.508.991 row-months, 77.626 asset keys và 1.122 charge-off events phân biệt theo kỳ event đầu tiên, không đếm repeated code-4 snapshots. Certificate đối soát exact 51/51 pool balances, contract counts, charge-off counts/principal và 408/408 delinquency count/balance checks. Recovery exact 2/51; 49 monthly deltas được hiển thị, không dùng thành recovery rate/LGD. Tab peer có charge-off/recovery flows theo kỳ, EX-103 definitions, risk-set classes 6/12/24 tháng, embargo split và feature coverage train/test. H12 có 8/8 candidate features present ở cả hai split; SEC filing lag median 27 ngày nên prediction clock phải theo filing availability. Geographic field đổi ở 2.870 khoản; UI cảnh báo cần provenance review. H6/H12 có OOT support hai phía, nhưng không có validation/calibration thứ ba; H24 chưa đủ history. Candidate target là servicing-time, bắt đầu outcome ở t+1, có competing code 1/3 exits; nhãn chưa qualify để huấn luyện hoặc gọi là origination PD. PTI > 1 và recovery âm từ WOART vẫn giữ scale/dấu; certificate account count WOART khớp XML nonzero balance ở 16/20 kỳ, bốn kỳ lệch đúng một account. Xem [research note WOART 2025-A](WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md), [Toyota panel audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [certificate tie-out](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [target feasibility](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [temporal split audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [feature availability](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [EX-103 field profile](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [feature anomaly audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [Toyota 2026-C profile](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), và [official KPI report](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). Raw XML/Parquet vẫn private.

Toyota 2024-B có thêm 29 tháng liên tục (04/2024–08/2026), 1.518.106 row-months và 70.254 asset keys. Pool/count, gross liquidation count/principal tie 29/29; 4 delinquency buckets tie 232/232 count/balance checks. Recovery exact 1/29, signed aggregate delta +$1.764.558,08. App gọi đây là deal validation cùng issuer family, không phải external issuer validation; xem [research note Toyota 2024-B](TOYOTA_2024B_VALIDATION_RESEARCH_VI.md) và [browser receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). Mở trực tiếp: `http://127.0.0.1:8785/?view=abs&workspace_tab=absee-profile`.
Nissan 2024-B bổ sung external issuer transfer test 23 kỳ (10/2024–08/2026), 1.154.259 row-months / 63.688 asset keys / 63 fields. Pool/count exact 23/23; positive charge-off count 20/23, first code-4 count 21/23, gross principal 21/23, first-code-4 amount 20/23; DPD bucket checks literal 178/184; recovery exact 17/23 với aggregate delta +$8.859,23. SEC submissions refresh live đến 25/09/2026 byte-identical acquisition census, xác nhận không có 10-D/A hoặc ABS-EE/A cho kỳ 07/2025. Hai 10-D net-loss identities đúng 23/23; current ratio 0,08%→0,56% (range −0,39%–0,86%), four-month average 0,02%→0,26% (range −0,01%–0,53%); trigger 4,90% báo No cả 23 kỳ. Recovery deltas sáu kỳ đều có code-4 ở tháng trước, vẫn chưa khép amount. Tháng 06/2025 bucket residual gắn đúng với 2 accounts ở 60 DPD ($50.837,98) và 1 ở 90 DPD ($22.729,88); boundary shift khớp tháng đó 8/8 nhưng giảm toàn-panel exact checks 178 xuống 86 nên giữ nguyên mapping và cảnh báo local. 07/2025 vẫn unresolved: 33 first rows $577.420,34 + 3 repeated $77.765,22, certificate ghi 1 receivable/−$59.000,49. App có chart + bảng 23 kỳ và các exception explanations; không qualify PD/LGD. Xem [Nissan external issuer research](NISSAN_2024B_EXTERNAL_VALIDATION_VI.md), [live SEC census audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [recovery/DPD diagnostic](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [DPD boundary comparison](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [certificate audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [browser QA](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). Mở app: `http://127.0.0.1:8785/?view=abs&workspace_tab=absee-profile`.

Reviewer total due/YTD và prior interest carryover đang giả định bằng zero;
source paid-zero không chứng minh due-zero. PRE_ACCELERATION là declared
replay regime, chưa independent legal-event evidence. Cả bốn qualifications
full contractual waterfall/legal regime/obligation completeness/realized loss
model đều false. Executed agreements, amendments, benchmark fixing/fallback,
automated carryover, acceleration và actual maturity instructions còn thiếu.

Declared maturity/terminal scenario có ở engine nhưng chưa có app input
workbench. Loan-level ABS-EE, future collateral projections, tranche loss,
valuation/positions và findings/review là các bước tiếp theo của full P5.
Giữ nguyên full 50-capability suite trong `PLAN_FIVE_WORKSPACES.md`.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_abs_view.py abs-waterfall-762205cf20db
.\.venv\Scripts\python.exe -X utf8 scripts/browser_abs_qa.py
```

Build tạo receipt mới; không cập nhật receipt lịch sử để chấp nhận methods mới.
