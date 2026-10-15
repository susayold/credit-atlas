# EBMUD — covenant và debt-service definitions, checkpoint 11/10/2026

## Nguồn đã acquire

Official issuer index: https://www.ebmud.com/about-us/financial-information/official-statements

Hai PDF được lấy từ links có label trên index, không đoán URL hoặc dựa vào filename. Water statement ngày March 31, 2026 có 308 physical pages; Wastewater ngày April 15, 2026 có 282 pages. Tổng 590 pages. Đây là official statements/summary provisions, chưa phải executed full indenture chain.

Source: `private evidence omitted from public release`; receipt SHA `99a9782c07621805b5a437a389953d097bec71e389382493c225e8d59fa3eeb1`. Source/profile integrity được kiểm tra trước mỗi report. Profile hiện tại `private evidence omitted from public release`; SHA `c31ab0fc82e030f38c5c457d7b95731059ebdd8a1ba322fb8671e52dd8b083f5`.

## Phân biệt ba phạm vi

1. **Reported rate covenant 1.1x:** được mô tả cho adjusted net revenues / Bonds and Parity Debt trong fiscal year, gắn nghĩa vụ đặt/thu rates. Không mặc định dùng total debt-service DSCR hoặc EBIT/interest coverage làm phép test.
2. **Board policy target 1.6x:** mục tiêu quản lý, được mô tả là cao hơn rate covenant và có thể thay đổi theo Board discretion. Không dùng làm legal breach threshold.
3. **Qualified historical test:** chưa có. Các actuals đang phục vụ là Continuing Disclosure editions 2024/2025 cho các fiscal years 2020–2025; một summary statement công bố năm 2026 không tự chứng minh operative rules của từng năm đó.

## Định nghĩa debt service không chỉ là cộng cash payments

Appendix C mô tả adjusted revenues gồm nguồn thu và rate stabilization withdrawals, trừ O&M và stabilization deposits. Debt Service có conventions: excluded principal/assumed debt service, variable-rate SIFMA assumptions, nguồn tiền đã dành để trả nợ, swap treatment và liquidity-facility repayment. Hai trang tiếp giáp cho mỗi system được giữ; chưa chứng minh lịch annual actuals hiện có đã đáp ứng toàn bộ convention áp dụng.

## Sửa đổi đề xuất và default exceptions

Water: Thirty-Second Supplemental Indenture; Wastewater: Twenty-Second. Official statements mô tả springing amendments cần majority principal-owner consent **và** District certificate gửi/nộp Trustee. Các estimates consent sau contemplated issuance không phải bằng chứng certificate đã được nộp. Effective date vẫn null.

Appendix H là color redline: blue underlining additions, red strikethrough deletions. Plain-text extraction trộn cả hai; app giữ role “proposed” và link PDF, không gọi text đó là clean operative clause. Proposed rate language nhấn mạnh reasonable expectation/rate-setting; caveat nêu thiếu actual revenues cuối năm có thể không là default nếu các nghĩa vụ được quy định đã được đáp ứng. Không kết luận compliance/breach từ mỗi DSCR hoặc từ proposed text chưa verified effective.

| Bằng chứng | Water physical page | Wastewater physical page |
|---|---:|---:|
| Statement cover/date |1|1|
| Future amendment conditions |19|19|
| Reported rate covenant |22|22|
| Adjusted revenue / annual debt definitions |263|237|
| Debt Service and continued conventions |264–265|238–239|
| Policy target |119|92|
| Appendix C covenant summary |273|247|
| Appendix H notice |303|277|
| Proposed rate redline |304|278|
| Proposed default caveat |305|279|

## Verification và app

Independent audit dùng pdfplumber, không gọi production parser: `private evidence omitted from public release`, PASS 3 source hashes, 2 document identities và 22 clause-role/page checks. Audit đầu phát hiện predicate Fiscal Year ở nhầm definition page; đã dùng đúng anchor và bổ sung continuation page, không sửa source PDF. Failed receipt `utility-contract-audit-f832fb85bca8` được giữ.

Visual review trực tiếp Water rate-covenant page22, Water redline page304 và Wastewater default-caveat page279 xác nhận layout/redline/proposed scope. Backend/HTTP: `private evidence omitted from public release`, 36 checks PASS về scopes, thresholds/policy, future effective-date guard, integrity và existing HTTP boundary.

`/api/utility-debt-service`/private JSON trả thêm `legal_evidence`. P3 → Utility DSCR có Covenant description & proposed amendments, statement date, policy/rate distinctions, page evidence và required inputs. Applicable historical threshold/headroom/compliance vẫn null. Chưa nâng 50 capability states hoặc đóng C4.

Browser receipt: `private evidence omitted from public release`, 5 groups PASS sau bổ sung legal pane: hai systems/dates/supplements,reported covenant/policy distinctions,proposed default text,scope/export parity,URL/year bounds,mobile vàoutage recovery. Không browser errors,holdout ledger unchanged.

## Đầu vào còn cần

- Executed indenture và supplements đầy đủ, với ngày hiệu lực.
- District certificate/consent evidence tại Trustee để xác minh springing amendments.
- Applicable fiscal-year test/rate-setting scope và adjusted numerator/debt-service reconciliation.
- Certificates/actions liên quan cure/default exceptions.

Các kết luận hiện tại là source-qualified research evidence, chưa là đánh giá pháp lý về default hoặc certification covenant compliance.
