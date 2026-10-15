# P3.08 — maturity schedule audit, checkpoint 15/10/2026

Original scope gồm selected-filing principal buckets, exact candidates/definitions, subtotal/complete total/first-three-year share, JSON/Excel và new memo capture. Không đổi scope thành actual facility payment schedule hoặc debt service.

## Source/API

`private evidence omitted from public release`: PASS toàn bộ67annual filings ×2explicit debt families =134scopes/804bucket cells. Raw companyfacts candidate selection được làm độc lập, exact CIK/accession/form/filed/end/instant/USD và six concept definitions khớp API. 228supported/576missing;228candidate evidence entries. 38complete disclosed schedules/96partial. Real corpus không cónegative/all-zero/ambiguous buckets trongscope này;23synthetic tests bao phủcác boundary cases.

Summary/subtotal/complete-total/shares/first-three-years vàtied largest buckets khớp Decimal80. Unsupported share không trở thànhzero; debt-only vàdebt/capital-lease families khôngfallback hoặc cộngchồng. After-year-five giữopen-ended; principal amounts không trở thànhcarrying debt,EAD,interest payment hoặcDSCR.

Actual browser `private evidence omitted from public release`: PASS bốnissuers,raw-source JSON exports,explicit family/reload/mobile,outage/recovery vàholdout ledger không đổi. MSFTzero bucket vẫn supported;Ford/GMmissing không thànhzero debt.

## Excel

`private evidence omitted from public release`: PASS8latest issuer/family scopes. DownloadSHA khớp immutable server capture;23formulas mỗi workbook khớp source/cached ratios vàmissing guards.

`private evidence omitted from public release`: Excel16.0 CalculateFullRebuild PASS1408populatedcells và184formulas trên8read-only copies. Không lưu thay đổi;date serial vàoptional simple-sheet quoting được chuẩn hóa trongcomparison,mọireference/logic còn được so sánh.

`private evidence omitted from public release`: actual UI workbook download/source parity choAAPL/MSFT/AAPL-lease,mobile,error/recovery vàsingle export control PASS. CLI helper import đãsửa đểchạyđược cảscript vàpackage context; khôngsửa production debt calculations hoặcsource.

Tests:`private evidence omitted from public release`,23PASS.

## Kiểm tra bổ sung đã hoàn thành ngày 15/10/2026

- **Metadata:** receipt `maturity-excel-metadata-3245a487a50e/receipt.json` PASS cho tám workbook: sáu hàng Facts, nguồn, định nghĩa, accession, ngày, family và metadata của capture.
- **Native Excel:** receipt `native-excel-qa-maturity-cases-81cc3e93cc8b/perturbation-receipt.json` PASS 48 tình huống / 336 kiểm tra. Bao gồm toàn zero, toàn missing, toàn positive, partial, negative và text input. Các thay đổi chỉ nằm trong bộ nhớ của bản QA; không lưu vào workbook nguồn.
- **Trực quan:** đã xem trực tiếp đủ 16 PNG của bốn issuers × hai families × hai phạm vi summary/Facts. `maturity-native-render-20261015/visual-review.json` lưu SHA của từng ảnh. CIK giữ leading zeros, exact text và ngày đúng; missing không thành zero. Các cột Facts từ I trở đi và Metadata được kiểm bằng XML, không nằm trong ảnh render này.
- **Memo:** `maturity-memo-capture-qa-53be504b0819/receipt.json` PASS tám capture trong kho QA riêng: đúng issuer/filing/family, trend và coverage cutoff theo filing date, evidence hash, hai revision giữ nguyên capture, từ chối stale revision và đọc được bằng chứng đã lưu khi giả lập source outage. Nội dung memo là synthetic, trạng thái review tự khai báo; chưa chứng minh quy trình phê duyệt thực.
- **Tests:** `maturity-memo-acceptance-tests.xml`, 33 tests PASS.

Script `scripts/record_maturity_verified_delivery.py` kiểm tra các receipts, source/workbook/capture/method hashes trước khi ghi partial evidence vào sổ yêu cầu. Giữ nguyên yêu cầu, checkpoint và remaining inputs; chưa nâng nghiệm thu toàn bộ P3.08.

## Dữ liệu gốc mới: Apple annual debt reconciliation

Đã tải báo cáo 10-K 2025 qua HTTP, lưu ở `private evidence omitted from public release`. Issuer SEC feed liên kết trực tiếp URL HTML với CIK 0000320193, form 10-K và filing date 31/10/2025. Hai bảng debt được lưu kèm SHA; acquisition receipt ban đầu chưa kiểm feed, bằng chứng liên kết bổ sung nằm trong audit receipt.

`private evidence omitted from public release` PASS: hai bridge principal → carrying → noncurrent cho 2025/2024; sáu fiscal maturity buckets khớp capture SEC hiện có; tổng bốn original note sizes khớp aggregate issuance 2025. Phép đối chiếu dùng số nguyên với đơn vị USD millions, không dùng production debt parser.

Năm 2025: principal 91.281 triệu USD, discount/costs −309 triệu và hedge adjustment −294 triệu cho carrying 90.678 triệu USD. Current carrying 12.350 triệu và noncurrent 78.328 triệu khớp. Principal bucket năm đầu 12.393 triệu USD cao hơn current carrying 43 triệu USD: hai đại lượng không thể thay thế nhau.

Nguồn trực tiếp: [Apple 2025 Form 10-K](https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/c636d8a7-8025-47d2-9b13-bcf5465343b3.html), [issuer SEC filings](https://investor.apple.com/sec-filings/).

## Annual debt bridge đã tích hợp vào app

Trong **SEC → Debt maturities**, scope Apple/debt-only và filing 2025 hiện có bảng principal → discount/costs → hedge adjustment → carrying → current/noncurrent cho 2025/2024. Bảng giải thích chênh lệch 43 triệu USD giữa principal bucket năm đầu và current carrying, liên kết annual filing gốc, giữ hai bảng nguồn và xuất private JSON.

API `/api/sec-annual-debt-bridge` và `/api/sec-annual-debt-bridge-report` chỉ trả bridge khi accession/report-end/filing date/issuer/family khớp chính xác. Cutoff trước filing, filing cũ, issuer khác hoặc debt/lease family không nhận dữ liệu thay thế. Runtime kiểm hash audit cố định, method và toàn bộ source graph; kiểm lại sáu bucket với SEC evidence đang chọn. Bằng chứng thay đổi làm request fail closed.

Kiểm chứng: `annual-debt-bridge-tests.xml` 33 tests PASS; `annual-debt-http-regression.xml` 25 tests PASS; `annual-debt-cache-regression.xml` 9 tests PASS. Browser receipt `annual-debt-bridge-qa-31cb1e375e1e/receipt.json` PASS actual UI/download, family/reload/issuer/pre-filing boundaries, mobile, outage/recovery và HTTP origin/unknown/duplicate-filter guards. Đã xem trực tiếp ảnh desktop/mobile của bản cuối. Holdout ledger không đổi.

Module có dữ liệu annual thực, nhưng qualification cho per-series outstanding/actual payments/calendar/full debt service vẫn false. Phần này mở rộng nội dung phân tích trong app; không nâng toàn bộ P3.08 lên hoàn thành.

Workflow maturity gốc sau tích hợp cũng đã chạy lại trên bốn issuers: `sec-debt-qa-2ee0574c85ee/receipt.json` PASS raw candidate/JSON parity, family/reload/mobile/outage và holdout ledger guard. AAPL/MSFT có sáu bucket supported; Ford/GM không có bucket supported trong explicit family này, không bị hiển thị thành zero debt.

## Phạm vi còn thiếu

Full amendment chain, dated utilization/outstanding theo từng instrument, actual principal/interest payments và payment-place/calendar qualification vẫn thiếu. Tổng original issuance khớp bảng annual không chứng minh từng series còn nguyên dư nợ hay coupon đã trả. Memo UI/review-package nghiệm thu đầy đủ cũng còn mở ở P3.06/P3.10. Không suy ra EAD, DSCR hoặc covenant compliance từ các bucket này.

Suite vẫn **20/50 = 40%** theo nghiệm thu; goal 100% còn active.
