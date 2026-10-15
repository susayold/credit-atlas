# EBMUD — dữ liệu debt service và DSCR thực tế lịch sử

## Phạm vi

Case bổ sung cho P3.03/P3.07/P3.08 và KPI C4. Issuer: East Bay Municipal Utility District, hai hệ thống Water và Wastewater. Đây là municipal utility case; không thay thế debt-service của Ford, corporate underwriting hoặc mortgage PD/LGD.

Nguồn chính thức: https://www.ebmud.com/about-us/financial-information/financial-reports

Đã tải index và năm PDF: ACFR 2023/2024/2025 và Continuing Disclosure 2024/2025. Receipt: `data/private/business/utility-debt-source-51fc6939e77e/acquisition-complete.json`. Hash receipt: `422e0503926a71b4f0944b606e9d0bd86f0952b039599bd8f2a48d4677387a48`.

## Dữ liệu được chuẩn hóa

- Continuing Disclosure: 20 system-year-edition records, 13 trường/record, 260 vị trí; mỗi edition gồm 5 năm cho hai hệ thống. Các năm overlap giữa editions không phải observations độc lập mới.
- ACFR statistical tables: 60 records, 5 trường/record, 300 vị trí, mỗi edition gồm 10 năm cho hai hệ thống. Amounts là USD million đã làm tròn; tỷ số là reported DSCR.
- Profile: `artifacts/private/utility-debt-profile-9b7023d435f2/profile.json`, SHA `7f159bed4a7e979f8c3afc98d623e8f8aa8c9c46b95920926dec2a9ff5bfacba`.
- Source text, physical PDF pages và PNG giữ cùng profile. Bảng Continuing 2025 Water/Wastewater physical pages 13/19 đã xem trực tiếp.

Continuing Disclosure và statistical section của ACFR là unaudited. Không gọi toàn bộ bảng này là audited chỉ vì nằm trong ACFR.

## Tính toán

DSCR parity = net revenues / parity debt service. DSCR total = net revenues / (parity + subordinate debt service). Hai scopes phải chọn rõ; không thay bằng EBIT/interest coverage.

FY2025 Water: net revenues 526,596,219 USD; parity debt service 200,370,894 USD; total debt service 209,515,790 USD. Reported parity DSCR 2.63, total DSCR 2.51. FY2025 Wastewater: net revenues 78,505,411 USD; parity và total debt service đều 29,880,166 USD; reported DSCR 2.63.

Giữ bốn residual bridges: revenue transfers, maintenance/tax adjustment, net revenue và parity/subordinate debt service. Source Water2025 net-revenue bridge lệch +1 USD; Wastewater2025 maintenance bridge lệch +1 USD. Không sửa source để ép reconciliation bằng 0.

ACFR Water/Wastewater comparisons dùng mức làm tròn 0.1 triệu USD. Wastewater FY2024 maintenance: ACFR có 82.1 triệu, Continuing có 82,158,220 USD (82.2 triệu khi làm tròn). API giữ mismatch, không tự chọn một nguồn làm sự thật duy nhất.

## Kiểm tra độc lập

`scripts/audit_utility_debt_service.py` dùng pdfplumber tọa độ chữ và Fraction, không gọi parser production. Receipt PASS: `artifacts/private/utility-debt-audit-381643544e02/receipt.json`.

Kiểm tra sáu source hashes, 52 annual column vectors, 60 ACFR rows, 560 selected positions và 40 DSCR ratios. Một typography issue ban đầu: PDF tách 425.1 thành hai glyph runs chạm nhau. Auditor chỉ nối numeric runs có bounding boxes tiếp giáp dưới 0.1 point, giữ giới hạn baseline và kiểm tra toàn vector. Receipt thất bại trước sửa vẫn được lưu ở `utility-debt-audit-7fe694506188`.

## API và phần còn mở

Backend cung cấp `/api/utility-debt-service` và `/api/utility-debt-service-report`; filters string: edition 2024/2025, year trong five-year source window, system water/wastewater, basis parity/total. Default: 2025/2025/water/total. Calendar prior year và previous-edition same-year là hai trường riêng. Nguồn/profile bị thay đổi phải từ chối; response private/no-store. Chưa tích hợp pane giao diện tại checkpoint này.

Các tests bao gồm lien denominator, negative stabilization transfers, source zero, one-dollar residuals, cross-document mismatch, invalid scope, tampering, HTTP/HEAD/private JSON export. Không là full-report accounting audit.

Kết quả: 29 backend/HTTP checks PASS tại `artifacts/private/utility-debt-http-tests-20261011-warm.xml`. Hai lượt trước có business-export socket timeout do scientific dependencies import trên request thread; test boundary đã pre-import real projector trước socket assertion, không mock projector hoặc tăng timeout. Cold-start response performance chưa được qualified từ bộ test này. Failed XML vẫn giữ nguyên. Partial evidence ghi cho P3.03/P3.07/P3.08 trong `COMPLETION_REQUIREMENTS_50.json`; không đổi trạng thái.

Threshold/headroom/compliance luôn null: chưa acquire/qualify full indenture và amendment chain, applicable covenant test hoặc đầy đủ legal adjustments. Không dùng policy DSCR target làm legal covenant. Không thêm forecast FY2026 thành actuals. Không tuyên bố original-publication vintage availability, calibrated PD/LGD hoặc public-release approval.

Không nâng trạng thái hoàn thành 50 capability hoặc đóng C4 từ checkpoint này. Bước tiếp: UI/filter/source evidence/export và browser QA; sau đó chốt applicable legal terms trước covenant assessment.

## Giao diện đã tích hợp

P3 Issuer financials → Utility DSCR. Đây là case EBMUD riêng, độc lập với SEC issuer selector. Chọn edition/system/fiscal-year/debt-basis; year bounds thay theo edition. Màn hình có selected DSCR, USD inputs, bốn reconciliation bridges, ACFR precision comparisons, five-year source history, previous-edition same-year values, source PDF links/physical pages/text/footnotes/hashes và private JSON export. Display DSCR làm tròn 6dp; Decimal50 vẫn có trong details/API/JSON.

Browser receipt mới: `artifacts/private/utility-debt-qa-dfe72cbf4cef/receipt.json`, 5 groups PASS, không browser error, frozen holdout ledger không đổi. API/export parity, đổi scope, source mismatch, URL reload, edition year reset, mobile no page overflow và outage/recovery được kiểm tra. Hai lượt đầu phát hiện mất filter khi reload và hash overflow trên mobile; đã sửa state persistence và scoped wrapping, sau đó chạy lại. Screenshot mobile-summary/desktop-checks đã xem trực tiếp.

Facility/covenant regression: `artifacts/private/facilities-qa-eb8a3159a041/receipt.json`, 5 groups PASS. Pane mới không thay hoặc bổ sung actuals vào facility/covenant Ford.

Shared-app sovereign archive regression: `artifacts/private/sovereign-archive-qa-d33cb49e65a8/receipt.json`, 5 groups PASS sau các sửa giao diện; không browser errors hoặc holdout-ledger changes.

Phần UI ở checkpoint source/API trước nay đã được bổ sung. Legal threshold/headroom/compliance vẫn unavailable; C4 và P3.07 chưa đóng.
