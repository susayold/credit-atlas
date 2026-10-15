# P2.05 — nghiệm thu Transition Matrix theo plan

Ngày 12/10/2026. Đối chiếu nguyên yêu cầu P2.05 trong `PLAN_WORKBENCH_DETAIL.md` và `COMPLETION_REQUIREMENTS_50.json`. Nghiệm thu **chức năng mô tả** trên case `d01-a24484b21a21`, pipeline `pipeline-307c354f3d74`, official annual sample2012. Không thay mục tiêu bằng model, không đổi scope sang dữ liệu Fannie sample.

## Yêu cầu và bằng chứng

| Yêu cầu gốc | Evidence kiểm tra | Kết quả |
|---|---|---|
|Adjacent loan-month pairs|Independent destination-side LAG trên toàn canonical panel; không dùng lại engine transitions.sql|4.460.559 pairs khớp|
|Opening UPB|SUM Decimal theo opening month; đối chiếu cell và origin denominator trước JSON float conversion|2.370 amount checks khớp representation|
|Selected reporting year/segment|4 segments × all/15years/absent1990; filter sau khi dựng adjacent pairs|68 phạm vi export khớp|
|Count hoặc opening-balance weights, origin denominator|So pairs/origin pairs và known openingUPB/origin openingUPB|Max probability difference2,220446049250313e−16, tolerance1e−12|
|Matrix|Toàn bộ1.091year cells +94lifetime cells; pairs,distinct loans,missing balances,sparse flags đối chiếu|1.185cells khớp|
|Selected-cell detail|Browser click cell, numerator,origin denominator,distinct loan và missing-balance support|6scope/basis cases PASS|
|Year-scoped export|JSON downloaded đúng segment/year/basis; monthly chart range và horizon không thay transition scope|API/report và browser download khớp|
|Không nối gaps/terminal pairs sai|Synthetic fixture December→January,March gap,terminal origin/destination và missing UPB; source-wide LAG parity|PASS|
|Năm không có pairs giữ unavailable|Year1990 export rows[]; UI không tạo matrix zero; reload giữ1990|PASS|
|Lifetime comparator ghi rõ scope|Export lifetime_rows giữ whole-period comparator cùng segment; scope_note/filters_applied được kiểm tra|PASS|

## Receipts và current-state checks

- Independent audit: `private evidence omitted from public release`; full served projection ở cùng folder. Verify bốn source Parquet hashes, frozen case receipt và method hashes. Không fit model, không mở retail final predictors; frozen retail ledger không đổi.
- Tests: `private evidence omitted from public release`, **22 PASS**, gồm gap/terminal/year/missing-UPB/distinct support, invalid join/grain, scoped export, cross-case/method/source integrity và filter validation.
- Browser: `private evidence omitted from public release`, **6scope cases PASS**: all/all/count; relief2012/count; non-relief2025/balance; unknown2012/count; all2020/balance; all1990/count. Có mobile,absent-year reload,cross-origin rejection và invalid-year400. Desktop matrix/all và empty-year đã visual review.

Lần independent audit đầu dùng sai tên JSON key `supplemental` thay vì `supplemental_evidence`; đã sửa script audit, không sửa service để khớp test. Lần chạy có receipt PASS ở trên là lần dùng đúng contract. Không lấy output chưa hoàn tất làm evidence.

## Giới hạn giữ nguyên

JSON existing contract dùng floating point cho amounts/probabilities; UI amounts làm tròn để đọc. Audit xác nhận Decimal aggregates và đúng conversion sang representation hiện có, không chứng nhận export là accounting ledger. Missing-UPB support được báo riêng; repeated pairs không independent; distinct-loan counts không cộng qua cells/years.

Temporal comparison/confidence intervals khi có thêm vintages là **bước phát triển tiếp theo** ghi riêng trong P2.05, chưa thực hiện. P2.08/R2/R3 về multi-vintage,PD12/calibration/OOT vẫn mở và không được đóng từ transition acceptance.

Kết luận: đủ evidence cho **toàn bộ yêu cầu hiện tại của P2.05**. Chỉ P2.05 được đánh dấu `full_completion_proven=true` tại checkpoint này; không thay trạng thái49capability còn lại hoặc tuyên bố goal100% đã hoàn thành.
