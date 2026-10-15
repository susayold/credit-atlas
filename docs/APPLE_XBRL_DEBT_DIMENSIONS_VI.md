# Apple 2025 — debt dimensions và giới hạn nhận diện instrument

Đã tải gói XBRL trực tiếp qua HTTP từ URL loại XBRL trong issuer SEC feed, cùng rendered XBRL report của filing 10-K ngày 31/10/2025. Dữ liệu nằm trong `data/private/sec-documents/apple-annual-xbrl-a596bfb03297`; archive ZIP giữ nguyên, kiểm CRC và giới hạn kích thước trước đọc XML. Không thực thi nội dung tải về hoặc giải nén tùy ý vào filesystem.

## Dữ liệu và kiểm chứng

Profile giữ 155 facts có tên chứa debt/interest, gồm context, period, dimensions, unit, decimals, value và nil. Đây là tập tìm kiếm rộng: có cả khoản đầu tư debt securities, noncontrolling-interest income và narrative blocks; không được gọi là 155 khoản nợ của Apple.

Audit `artifacts/private/apple-xbrl-debt-audit-b216f108cb2d/receipt.json` PASS:

- 150 facts numeric khớp raw XML instance bằng parser DOM độc lập với parser ElementTree tạo profile, kể cả multiplicity theo concept/context/value.
- Năm facts không numeric được giữ riêng: ba narrative blocks và hai duration values. Không tuyên bố đã kiểm numeric các facts này.
- Hai số tiền issuance groups được đối chiếu thêm với hai hàng trong bảng annual HTML gốc; đơn vị bảng triệu USD được đổi thành USD bằng số nguyên.
- CIK trong context, feed linkage, archive/profile/HTML và method hashes được kiểm.

Issuer URL loại `XBRL_HTML` trả rendered XBRL report, không phải original inline document. Hai lần thử đối chiếu toàn bộ facts với inline tags không thành công do định dạng này. Audit cuối dùng raw XML DOM cho 150 facts và annual HTML cho hai số tiền nhóm; không báo cáo 150-fact HTML parity.

## Nhóm được công bố tại 27/09/2025

| Nhóm trong debt instrument axis | Số tiền hiển thị trong bảng annual | Phạm vi |
|---|---:|---|
| Phát hành 2013–2023 | 86.781 triệu USD | Nhóm phát hành, không phải từng ISIN |
| Phát hành 2025 | 4.500 triệu USD | Nhóm bốn series đã có terms; chưa có dư nợ riêng từng series |
| Tổng hai nhóm | 91.281 triệu USD | Khớp total term debt principal |

Một điểm cần giữ trong normalization: các nhóm được tag `DebtInstrumentCarryingAmount`, nhưng bảng annual trình bày tổng 91.281 triệu USD trên cơ sở principal. Sau discount/costs và hedge adjustments, carrying thực trong bảng là 90.678 triệu USD. Chỉ dùng tên concept để suy ra analytical basis sẽ cho kết quả sai.

Coupon/effective-rate ranges có dimension Minimum/Maximum; maturity year range có duration context. Không biến range thành coupon hay maturity date của từng series. Các dimension asset-backed/treasury/corporate securities thuộc investment disclosure cũng không được cộng vào issuer borrowing.

## Tác động đến dự án

Nguồn mới bổ sung dimension lineage cho P3.02/P3.08 và chứng minh sự cần thiết của source-table basis trong debt reconciliation. Annual bridge hiện có trong app vẫn dùng bảng annual đã kiểm chứng; gói XBRL mới chưa được tự động phân bổ xuống bốn note series.

Để hoàn thiện full debt-service cần số tiền outstanding theo instrument/date, paid/unpaid principal và interest events, effective amendments và payment-place/calendar evidence. Qualification cho per-series outstanding, actual payments và debt service vẫn false. Không tăng số capability đã nghiệm thu từ dữ liệu này.

Nguồn trực tiếp: [Apple issuer SEC filings](https://investor.apple.com/sec-filings/), [annual filing HTML](https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/c636d8a7-8025-47d2-9b13-bcf5465343b3.html), [issuer XBRL archive](https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/0453c202-7e60-443d-b451-d785ee48e1f9.zip), [rendered XBRL report](https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/2e9ed198-d231-4a8f-9dd8-c811c01aca35.html).
