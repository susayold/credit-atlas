# CreditAtlas — kiểm tra tính lại bằng Microsoft Excel, 11/10/2026

Đã sửa lỗi export SEC: tham chiếu trực tiếp tới ô Facts trống làm Excel trả0,
khiến ratio hiện0 dù thiếu tử số. Công thức lấy input nay kiểm tra ISNUMBER
trước khi tham chiếu; số0 hợp lệ được giữ, ô trống/text trở thànhUnavailable.
Các reference hiện tại và kỳ trước đều dùng cùng quy tắc. Không thay đổi
ratio definitions, model, source snapshots hay lịch sử export cũ.

## Kết quả đã thực hiện

- Backend SEC workbook:7testsPASS.
- Tải export từ app:3nhóm kiểm traPASS;30calculation rows,44numeric results,
  20driver bridges,328formula cells. Kiểm tra cả công thức guard ở export mới,
  đối soát nguồn/exact text, mobile và lỗi tải; frozen holdout ledger không đổi.
- Microsoft Excel16.0/build17932: sáu workbook được CalculateFullRebuild;
  9264ô,746ô công thức khớp cached baseline;0differences,0formula errors,
  0ô hiện#### trong phạm vi đọc.
-18ca thay đổi input trong bộ nhớ:59checksPASS. Gồm KPI delta/zero/missing;
  SEC numerator/denominator zero/missing/text, prior numerator/denominator
  zero/missing và driver bridge; maturity zero/missing; portfolio selector
  baseline/unselected missing/selected missing.
- Excel mở các bản sao ReadOnly, đóng không lưu. Bản gốc và bản sao giữ hash.
  Chỉ dùng Excel.Application mới không có workbook, không thao tác workbook
  người dùng. Preview artifact của Analysis đã xem, bố cục giữ như bản trước.

## Evidence

- Native baseline: private evidence omitted from public release
- Native perturbation: cùng folder/perturbation-receipt.json
- Native raw readback: cùng folder/native-results.json
- UI export: private evidence omitted from public release
- Backend: private evidence omitted from public release
- Bản SEC đã sửa: private evidence omitted from public release

Giữ receipt cũ native-excel-qa-49ba87348c99/perturbation-receipt.json FAIL:
13ca ban đầu phát hiện SEC_missing_numerator lỗi tại I23/B10. Receipt mới
chứng minh sửa lỗi, không ghi đè bằng chứng lỗi ban đầu.

## Giới hạn còn mở

Đây là native recalculation và các tình huống đại diện của sáu workbook;
chưa chứng minh mọi input/phiên bản workbook/mọi native feature. Chưa visual
review trực tiếp bằng Microsoft Excel, chưa qualification full debt service,
source semantic validity, model OOT, decision-grade ECL hoặc reviewer roles.
Native test không làm21/9/12/8trạng thái của50capability tự tăng. Goal100%
vẫn chưa đạt; dữ liệu và gates còn thiếu tiếp tục giữ nguyên trong ledger.
