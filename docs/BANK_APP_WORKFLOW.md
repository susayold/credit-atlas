# P4 — Bank Financial Observatory: app và báo cáo

09/10/2026. Snapshot `bank-view-6363e3f7fd89`, panel
`bank-panel-13a7ad74220f`: 214.809 reports, 42 quý, 6.290 CERT.
Data/units/reconciliation ở [FDIC_BANK_PANEL_WORKFLOW.md](FDIC_BANK_PANEL_WORKFLOW.md).

## Sử dụng

Chạy `scripts/run.ps1`, mở:

http://127.0.0.1:8770/?view=bank&bank_view_id=bank-view-6363e3f7fd89

1. Chọn bank snapshot, reporting quarter và custom asset peer.
2. Selected reports: counts, exact reported money sums (USD **nghìn**),
   known-value counts và source-ratio medians.
3. Quality card luôn thuộc **toàn quý đã chọn**, không theo peer filter.
4. Historical support theo custom peer. Chọn all dùng median từ toàn quý,
   không average peer medians. Asset bands/composition có thể đổi theo thời gian.
5. Matched-certificate asset bridge thuộc toàn quý, cần hai quý liền nhau;
   không nối gaps. Quý đầu hiện unavailable thay vì zero.
6. Nhập FDIC CERT để đọc institution timeline; CERT628 có 42 observed quarters.
   Timeline thuộc toàn lịch sử certificate, độc lập quý/peer dashboard.
7. Header export xuất **aggregate của quý/peer đang chọn**. Timeline qua API
   riêng, không nằm trong aggregate export. URL giữ snapshot/quarter/peer/cert.

Bank snapshot độc lập retail freeze và mortgage run. P2 controls bị ẩn/disable
ở P4; P4 không save findings vào P2 case. Đây vẫn là một ứng dụng nhiều domain,
với namespace dữ liệu và phép tính riêng.

## Projection và API

`bank_views.py` verifies panel/raw hashes rồi ghi aggregate snapshot,
panel-receipt SHA, snapshot SHA và method hashes. Server verifies current/frozen
methods, receipts, raw và output digests; không stale fallback khi evidence đổi.
Timeline checks trước và sau parameterized query; tối đa 42 actual observations.

| API | Scope |
|---|---|
| `/api/bank-views` | Verified/unavailable catalog; không filters |
| `/api/bank-view?view_id=…` | Whole aggregate snapshot; chỉ view_id |
| `/api/bank-report?view_id=…&quarter=…&peer=…` | Private JSON attachment của reporting quarter/custom peer |
| `/api/bank-timeline?view_id=…&cert=…` | Một positive FDIC certificate, observed quarters |

Unknown/duplicate parameters, unknown quarter/peer, invalid cert/path IDs bị
từ chối. Raw paths không trong browser/report. Loopback Host/Origin, no-store
và CSP vẫn áp dụng. Money sums là exact JSON strings; UI format strings,
không chuyển sums sang floating-point money. ROA/book ratios finite numeric.
Report giữ filters, selected count, source links, contract/limits,
whole-quarter quality/matched-change scope và `model_qualified=false`.

## Actual acceptance

Browser `bank-browser-qa-3b92675e9f79`: **11 checks PASS**, Chrome:

- 214.809 reports/42 quarters; latest quarter 4.313 reports.
- P2 controls/findings isolated.
- 2020Q2 / $1bn–dưới $10bn: **765 reports**; quality vẫn toàn quý.
- Export bằng verified selected report, exact money strings và limits.
- Actual CERT628 timeline 42 quarters; URL state/reload giữ scope.
- First-quarter bridge unavailable; mobile390 không page overflow.
- Navigate về actual P1/P3/P2; bank chạy khi mortgage catalog rỗng.
- Không JavaScript/console errors.

Ảnh desktop/mobile, exported JSON và receipt ở
`private evidence omitted from public release`; đã xem trực tiếp hai ảnh.
First run `bank-browser-qa-2b413354807d` qua P4 nhưng timeout khi chuyển sang
cold retail verification với default assertion 5 giây. Giữ failed receipt;
rerun tăng riêng cold-retail assertion lên 30 giây và qua navigation, vẫn giữ
source/model-lineage verification.

**570 tests PASS** (375 engine + 195 application), 63,25 giây. Có 10 tests mới
cho selected export/deep-copy, unsupported filters, bounded timeline,
changed snapshots/methods, actual HTTP attachments và scope/privacy flags.

```powershell
.\.venv\Scripts\python.exe scripts/build_bank_view.py --panel bank-panel-13a7ad74220f
.\.venv\Scripts\python.exe -X utf8 scripts/browser_bank_qa.py
.\scripts\test.ps1
```

## Còn thiếu

Descriptive bank slice đã có data → canonical → checks → snapshot → UI →
export → browser evidence. Full P4 còn institution history/consolidated-industry
population, country observatory, typed loan-book exposures, EL/ECL/stress,
movement/dependence scenarios và bank-specific findings/review.
Latest-revised panel chưa có historical publication availability; negative
book equity không tự thành bank-failure hoặc borrower-default label.
