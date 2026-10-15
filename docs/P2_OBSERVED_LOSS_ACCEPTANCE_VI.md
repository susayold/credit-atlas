# P2.09 — observed loss bridge: nghiệm thu phạm vi hiện tại

Đã đối chiếu source loss/recovery/cost fields, periods và terminal information của corpus hiện tại; kiểm tra components, signs, missing, coverage, reconciliation và exports. Chức năng này là descriptive source-reported loss, không phải qualified LGD hoặc accounting ECL.

## Population và số liệu chính

Loss population gồm zero-balance codes **02,03,09,15**: 381 terminal loans, không phải toàn bộ loans đã kết thúc bởi mọi nguyên nhân. Corpus không có duplicate terminal record trong nhóm này. Có 374 khoản reported loss và 7 khoản unresolved: 6 withheld-defect, 1 recent disposition. Không gán missing thành zero.

| Thành phần signed · USD | Tổng exact |
|---|---:|
| Removal UPB |63.571.075,41|
| Net sales proceeds |−50.439.065,41|
| Delinquent accrued interest |3.602.168,34|
| Total expenses |5.717.231,01|
| MI recoveries |−3.096.864,77|
| Non-MI recoveries |−694.587,03|
| Reported actual loss |18.659.957,55|

374 component-complete records khớp công thức signed-additive của guide Release 47, residual Decimal chính xác 0. Expense breakdown gồm legal, maintenance, taxes/insurance và miscellaneous: 374 records cũng khớp chính xác 0. Không đưa modification/bankruptcy costs vào actual-loss bridge.

## Hai khoảng thiếu đã xử lý bằng diagnostics riêng

Snapshot frozen tính legacy `severity_*_uncapped` bằng `abs(actual_loss)/abs(removal_upb)`: đây là **magnitude ratio**, không phải signed severity. Diagnostics mới trình bày song song:

| Ratio | Mean | Min | Max |
|---|---:|---:|---:|
| Signed actual loss / abs(removal UPB) |0,325279365|−0,638627259|1,456044945|
| Magnitude abs(loss) / abs(removal UPB) |0,330967669|0,000053372|1,456044945|

Có 17 loss âm; signed ratio giữ các gain này âm, không clipping. Cả hai ratio chưa là qualified LGD.

Summary frozen ghi 0 expense-formula checked rows vì input parquet của summary không giữ bốn expense fields. Source audit trước đó vẫn có expense residual. Diagnostics mới đọc các fields canonical và hiển thị **374 checked rows**, không sửa snapshot hoặc che sự khác biệt. Giao diện bổ sung field-level known/missing/negative/zero/positive counts để kiểm coverage thực tế.

## Bằng chứng

- `private evidence omitted from public release`: toàn bộ 381 records, 4.191 raw-to-canonical Decimal checks, 3.810 saved-row field checks, signed components, coverage, availability, exact loss/expense residuals và source hashes. Receipt giữ trạng thái finding lúc audit; hai presentation gaps được xử lý bằng diagnostics được kiểm tra sau đó.
- `private evidence omitted from public release`: 26 tests PASS, gồm signed gain, magnitude, missing/zero exposure, repeated terminal selection, query scope, frozen service và vendor loss contracts.
- `private evidence omitted from public release`: 4 segment scopes PASS; 220 field-quality values, signed/magnitude ratios, component table và 7 bridge rectangles khớp source; hai loại exports đúng scope; mobile 390px không overflow; cross-origin/query bị từ chối; ledger holdout không đổi.

`/api/observed-loss-details[-report]?run=...` là whole-source loss-code scope; không áp portfolio segment/date/horizon. Main aggregate report vẫn xuất legacy snapshot; JSON diagnostics riêng có signed ratios và expense checks. Cả hai được ghi rõ scope, không đại diện thị trường. API không trả raw loan IDs hoặc paths; frozen case được verify trước/sau đọc canonical.

Các browser regressions P2.01–P2.07 và audit lifecycle/privacy mới đã PASS, được ghi vào sổ requirements cùng hashes.

## Phần còn mở

Checkpoint P2.09 vẫn **Có điều kiện** về data/model qualification. Nghiệm thu chỉ đóng chức năng observed-loss bridge theo yêu cầu hiện tại; không nâng qualified LGD/ECL. Gate vẫn blocked bởi resolved support dưới 1.000, denominator support dưới 1.000 và partial component coverage. Recovery cashflow timing, contract-specific loss treatment, mature multi-vintage cohorts chưa được chứng minh.

Guide January 2026 mới tải là reference lịch sử có sign convention khác guide July 2026/Release 47 gắn với corpus. Không áp công thức hoặc dấu của bản cũ vào bản mới. ZIP release vẫn receipt-declared; source provenance không được xác thực bằng publisher hash registry. Mục tiêu 100% toàn dự án chưa đạt.
