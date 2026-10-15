# P4.01/P4.02 — typed intake, inventory và concentration

Checkpoint 15/10/2026. Nghiệm thu workflow research trong plan: InputPositions/InputControl XLSX, verified import/input quality/private inventory, native-currency reconciliation, concentration rows/meters và bucket → review draft. Không chứng nhận owned institution portfolio, borrower concentration, FX policy hoặc calibrated PD/ECL.

## Intake và nguồn

`p4-intake-current-tests.xml`: 47 tests PASS cho XLSX adapter, typed imports/views và HTTP errors. Bao phủ 20 MB, 50.000/50.001 input rows, cached formulas không được tin cậy, unsafe numeric precision, trailing zeros/ambient Decimal context, duplicates/units/dates/pool representations, optional declared-risk semantics và source-lineage mutation. Row-bound test dùng minimal rows để cô lập giới hạn; full semantic rows được kiểm riêng, không tuyên bố đây là một portfolio ngân hàng 50.000 positions thực.

`p4-acceptance-qa-b6a5a8af88d0/receipt.json` PASS năm nhóm actual UI/HTTP. Unsafe 30-significant-digit numeric XLSX bị từ chối và không tạo import. Workbook mẫu EXAMPLE được nhập thành `exposure-import-9954c9a8d217`, ba positions: USD 250.000 và VND 1.000.000, một USD zero balance; EL vẫn null. Review bucket draft giữ observation grain và reported amount khác EAD. Đây là synthetic template, không phải hồ sơ vay thực.

Nguồn thực `exposure-import-57b88e00bedb` có 9.698 Freddie sample loan-month observations tại 2026-03, reported UPB USD 915.208.989,12 và 141 zero balances. Risk inputs thiếu nên source EL null. `exposure-audit-7c271e6aa162/audit-complete.json` PASS 66 independent Fraction checks cho raw CSV → typed amounts/ordinals/EL availability và toàn bộ aggregates. Không suy ra ownership hay borrower identity từ records này.

## Native Excel

`native-excel-qa-input-6f3311baa851/receipt.json`: Excel 16.0 PASS 78 populated cells trong InputPositions/InputControl của guided template; không formula/errors/differences/### clipping. New owned Excel instance, bản QA read-only, CalculateFullRebuild, Close(false), source/copy hashes không đổi. Đây là native value/text readback của template, không phải native visual PDF review hoặc large-portfolio execution.

Không khôi phục được precision đã bị Excel làm tròn trước khi file được lưu. Các amounts/IDs cần exact precision lớn phải dùng text cells theo contract; không dùng native double readback để chứng minh precision vượt khả năng lưu trữ của Excel.

## Reconcile, shares và private inventory

`p4-inventory-scope-audit-9ee97f218c01/receipt.json`: PASS 20 scopes / 664 checks trên nguồn thực và EXAMPLE import. Bao phủ all/individual currencies và bốn dimensions region/segment/source_state/representation. Count, zero count, unit-scaled amounts và concentration key sets khớp raw CSV; share được tính độc lập bằng Fraction với currency denominator, tolerance cho decimal representation 120 digits.

USD/VND không được cộng thành global total. Missing risk giữ null/UNAVAILABLE_NO_RISK_INPUTS, reported amounts không tự thành EAD. Report contract giữ ownership/overlap/borrower linkage/production PD/accounting ECL/regulatory qualification false.

## UI và sửa zero-denominator meter

`p4-concentration-browser-bc8433735b24/receipt.json` PASS 12 actual currency/dimension UI scopes trên hai imports: meter values, sort theo records, search, selected bucket detail, no-match disables review và mobile overflow guard. Source/example actual API numerical correctness do audit 20 scopes ở trên chứng minh.

Trước đây `Number(null) || 0` vẽ meter thành zero khi tổng currency amount bằng zero và share không xác định. Đã sửa: null share không tạo meter; chỉ hiển thị Unavailable. Synthetic zero widget được dựng từ aggregate helper và render trong content area để kiểm nhánh này. Đây là UI fixture, không phải một backend upload zero portfolio. Zero reported balance vẫn hiện USD 0, source EL và share unavailable.

Đã xem trực tiếp ảnh zero widget và mobile concentration cuối cùng, cùng intake-mobile/movement-desktop của browser checkpoint. Những ảnh viewport/panel không chứng minh toàn bộ template native layout. Backend/native, source math và UI evidence được giữ tách theo phạm vi.

## Kết luận phạm vi

P4.01/P4.02 đáp ứng typed input/inventory và native-currency concentration workflow hiện tại. Các next steps giữ nguyên: source/facility column mapping, domain templates, obligor/group identity và explicit FX policy nếu cần global totals. Risk calibration, accounting ECL, owned institution positions và authenticated review governance chưa được chứng minh; không chuyển các phần đó thành hoàn thành bằng fixture.
