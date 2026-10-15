# ABS-EE — đối chiếu định nghĩa trường với Schedule AL, 11/10/2026

P5 có tab **Định nghĩa ABS-EE**: tìm theo tên trường/mục Schedule AL, mở chi
tiết định nghĩa và coverage, đọc nguồn XML GovInfo, xuất private JSON.
Mở app: http://127.0.0.1:8770/?view=abs&workspace_tab=absee-dictionary

## Nguồn mới đã tải

- GovInfo, CFR2025/title17/volume3/section229.1125: PDF22pages277027bytes và
  XML126324bytes, tổng403351bytes. Edition2025-04-01, không gọi là bản luật
  hiện hành2026 chưa xác minh.
- Folder: private evidence omitted from public release
- Receipt SHA256:4cfb99d09c146fb50bd81ef83ca0b7009fe0c1c94d5e968748c5f8833a28b91b.
- PDF SHA256:8660bd608ed6055846f6d18d7da096ed65e6b23823dd0c7bb9bb0bea2a83690b.
- XML SHA256:555d156af01886b7dba75b89158215ea95fe0055c24debeac1224ad1268213b9.
- Link PDF: https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec229-1125.pdf
- Link XML: https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/xml/CFR-2025-title17-vol3-sec229-1125.xml

SEC technical-specification index dẫn ABSv3.1ZIP; tải trực tiếp HTTP trả403.
Lần thử được lưu tại private evidence omitted from public release
acquisition-failed.json. Không đổi endpoint/credentials để vượt restriction.
GovInfo là nguồn định nghĩa CFR riêng, không phải bản thay thế XSD.

## Mapping và phạm vi

62tên trường là union schema của11monthly Parquet đã có. Mỗi trường có
correspondence đề xuất tới Item3 automobile loans, full paragraph text và
XML paragraph index. Không tạo số ID khách hàng/asset hay gửi raw IDs ra UI.
Mapping do analyst lập từ ý nghĩa tên trường; chưa xác minh XML namespace,
XSD technical types/enum hay mapping thực tế của issuer EX103.

| Nhóm / ví dụ | Mục Schedule AL | Cách sử dụng / giới hạn |
|---|---|---|
|Asset identifiers|3(a)(1–2)|Nguồn identifier và unique asset number; chưa chứng minh mirror identity luôn ổn định|
|Reporting dates|3(b)(1–2)|Kỳ bắt đầu/kết thúc; giữ month gaps|
|Original amount/term/rate|3(c)(3–6)|Thông tin origination, không tự là dư nợ/rate hiện tại|
|Obligor score/PTI|3(e)(1–6)|Score và PTI tại origination; không thay affordability hiện tại|
|Beginning/end balance|3(f)(5)/(16)|Phân biệt hai mốc, đơn vị/giá trị mirror chưa xác minh|
|Scheduled/actual payments|3(f)(13–21)|Lịch dự kiến và tiền thực thu giữ riêng; nguồn thu có thể ngoài obligor|
|Zero balance date/code|3(f)(24)(i–ii)|Không suy default/prepayment từ số0 hoặc từ code chưa có enum|
|Delinquency status|3(f)(25)|Định nghĩa CFR mô tả số ngày quá hạn theo transaction agreement; sentinel/encoding chưa chốt|
|Charge-off/recovery|3(i)(1–2)|Tách principal charged off và thu hồi sau charge-off; chưa tính qualified LGD|
|Modification/extension|3(j)(1–2)|Loại sửa đổi và số tháng kéo dài; code chưa được decode|
|Repossession/proceeds|3(k)/(k)(1)|Tách indicator và proceeds; definition nói net of repossession fees/expenses|

Coverage đọc trực tiếp saved profile: số kỳ có cột, số kỳ không có cột,
tổngasset-period rows có schema và null/blank trong schema đó. Absent column
không biến thành0 hoặc được cộng vào parser-missing count. Source acquisition
không thêm observations: mirror vẫn488219asset-period rows,11files,3month gaps.

## Evidence đã đạt

- dictionary: private evidence omitted from public release
- Backend8testsPASS: dictionary+existingprofile. Kiểm tra definition semantics
  đại diện, không lẫn auto lease, roman zero-balance clauses, missing schema,
  source mutation, forbidden filters và XMLDTD.
- Independent audit: private evidence omitted from public release
  receipt.json:62full XML paragraph matches,62full PDF definition matches,
  62aggregate coverage comparisons và2source hashesPASS.
- Auto-loan evidence ở PDFphysicalpages16–18/printed606–608; đã xem ảnh render.
  Audit ban đầu cần bỏ footer/header khi nối paragraph qua trang; không sửa
  source để làm audit đạt. ReceiptISSUES_FOUND ban đầu vẫn giữ.
- Browser: private evidence omitted from public release
  5groupsPASS: search/detail/source flags, API/export, missing schema/reload/
  mobile, outage/retry, invalid scope/noerrors/holdoutledger unchanged.
- Existing coverage browser regression: absee-profile-qa-efd98c82ee7c,
  4groupsPASS. Desktop/mobile tab mới đã visual-review.

API: /api/absee-dictionary; export: /api/absee-dictionary-report.
Source files/receipt được verify hash trước mỗi response; no-store/private.

## Phần chưa đạt

XSD acquisition, enum/sentinel/currency/percentage precision, original filing
XML/EX103 fidelity, complete monthly coverage, servicer reconciliation,
forecast/target/OOT/LGD và full contractual waterfall vẫn chưa đạt. Các flags
xsd_verified/mirror_fidelity_verified/model_ready/current_rule_verified đều
false. P5.02/P5.03/P5.10 tiếp tục chưa complete;50capability giữ21Đãcó,
9Cóđiềukiện,12Mộtphần,8Cầndữliệu. Goal100% tiếp tục active.
