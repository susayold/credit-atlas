# Rà soát dữ liệu BoC–BoE Sovereign Default Archive

Ngày rà soát: **17/10/2026**. Tài liệu này tóm tắt bốn edition Bank of Canada/Bank of England đã được nhận và audit trong workspace riêng. Source register công khai chỉ chứa metadata cần truy vết, byte count và hash prefix; không chứa file gốc hay full hashes.

## Nguồn và ý nghĩa

Ngân hàng Canada nói BoC–BoE database được cập nhật hàng năm cùng Bank of England. Database tổng hợp nhiều nguồn công khai và tư nhân cùng thông tin mới để ước lượng **stocks of sovereign-government obligations in default**, gồm trái phiếu/chứng khoán thị trường, bank loans, official loans và domestic arrears. Technical Report 124 mô tả USD-valued estimates theo country và global; độ phủ thường không đồng đều, với phần lớn quốc gia chỉ có data từ 1990 dù chuỗi toàn cục bắt đầu từ 1960. [Technical Report 124](https://www.bankofcanada.ca/2023/07/technical-report-124/) · [2025 edition](https://www.bankofcanada.ca/2025/10/staff-analytical-note-2025-24/) · [2026 edition index](https://www.bankofcanada.ca/research/staff-analytical-papers/)

Đây là dữ liệu bối cảnh rủi ro **chính phủ quốc gia**. Giá trị tồn đọng trong default không phải tỷ lệ vỡ nợ của người vay, không xác định thời điểm phát sinh default ở cấp khoản vay, và không đủ để fit retail/corporate PD, LGD hoặc ECL. Trong CreditAtlas, nguồn phù hợp với workspace Country/P4: so sánh revision giữa các edition, mô tả debt-in-default/domestic-arrears và làm context cho thảo luận macro. Không chuyển nó thành target cho D01 mortgage hoặc D02 corporate credit.

## Các edition đã nhận

| Edition | Kỳ tham chiếu | Entity-year rows | Workbook ghi Last Update | Source objects đã bind |
|---|---:|---:|---|---|
| 2023 | 1960–2022 | 9.954 | 29 Aug 2023 | Landing page, XLSX, paper PDF |
| 2024 | 1960–2023 | 10.688 | 17 May 2024 | Landing page, XLSX, paper PDF |
| 2025 | 1960–2024 | 10.855 | July 2025 | Landing page, XLSX |
| 2026 | 1960–2025 | 11.022 | 6 Aug 2026 | Landing page, XLSX, paper PDF |

Tổng profile là **42.519 entity-year rows × 16 metric đã chọn = 680.304 value positions**. Con số 16 là phạm vi metric của adapter/audit, không phải số cột raw của workbook. Bốn workbook không phải bốn panel independent: chúng chứa overlapping reference years và revisions, nên phải giữ edition/version khi phân tích.

Audit độc lập đối chiếu 680.304 positions: **515.678 missing**, **72.509 zero**, **1.341 source-marker cells** và **9.954 positions vắng do schema edition 2023**. Không ép blank/schema absence thành zero; không điền edition cũ bằng số ở edition mới. Edition 2023 không có field IADB trong flat sheet. Edition 2024 có header alias `DEBT_TOTAL_2023` và các dấu sao/whitespace được giữ là source text với numeric value unavailable. Các khác biệt entity universe theo edition cũng được giữ riêng.

## Revision, mâu thuẫn và cách dùng

Revision chỉ được tính khi cùng entity, reference year, metric tồn tại trong edition liền trước có trong archive. Nó biểu thị thay đổi của estimate cho cùng reference year, không phải một default event mới trong khoảng năm. Không so sánh bằng cách trộn edition mới nhất cho từng entity hoặc tự tạo panel lịch sử point-in-time.

Audit rà 516 comparisons giữa World summary và flat country sheet; **68 mâu thuẫn nằm ở count**, trong khi 258 comparison về amount đạt độ chính xác đã công bố. Các source values được giữ, sai lệch được báo riêng. Không phân bổ World residual xuống quốc gia, và không đọc số nước có positive stock như xác suất vỡ nợ.

Mọi chart/table phải ghi rõ edition, reference year, đơn vị USD, metric và trạng thái revision/coverage. Khi một edition hoặc entity không có giá trị, hiển thị unavailable. Không dự phóng hoặc nội suy các năm thiếu từ bốn edition này. Một stress linkage với WDI/FRED cần PIT macro vintage, thời điểm công bố, định nghĩa sự kiện và thiết kế kiểm định riêng trước khi báo như tác động nhân quả hoặc kịch bản định lượng.

## Quyền sử dụng và provenance

Điều khoản website Bank of Canada cho phép dùng/copy/phân phối nội dung do chính Bank sở hữu khi ghi nguồn, nêu thay đổi và kiểm tra độ chính xác. Điều khoản đồng thời nói nội dung bên thứ ba có thể mang điều kiện riêng và Bank không cấp quyền tái sử dụng những phần đó trừ khi có chỉ dẫn rõ. Vì database tổng hợp nguồn public/private bên ngoài, lưu cờ **third-party source-rights review required** cho raw workbook/value redistribution; attribution của Bank không tự giải quyết quyền của mọi đầu vào. [Bank of Canada Terms of Use](https://www.bankofcanada.ca/terms/)

Acquisition receipts hiện xác nhận 12 file, SHA-256 và byte count khớp với các file private đã nhận. Source-level records cho từng landing page/workbook/paper/methodology nằm trong [source register](data/creditatlas-source-release-register-2026-10-17.json) và được map tới `country_observatory.py`, `country_views.py` và `/api/sovereign-defaults`. Receipt paths/full hashes vẫn ở vùng private.

## Kế hoạch tiếp theo cho nguồn này

1. Giữ nguyên bốn edition, source text, schema absence, missing và zero trong canonical layer; không trộn revision vào một “final” value duy nhất.
2. Đối chiếu từng KPI/API/export với edition ID, entity, reference year, unit, numerator/denominator nếu là ratio, và formula card N03.
3. Hoàn tất browser/API/Excel export parity và analyst-facing lineage cho route Sovereign Archive; test entity universe, revision boundary và missing-versus-zero.
4. Rà source attribution/rights cho các thành phần third-party trước khi phát hành raw values trong public GitHub package.
5. Chỉ thiết kế stress linkage sau khi có macro vintage phù hợp với ngày quan sát, coverage protocol, event definition và out-of-time validation. Cho tới lúc đó, chỉ hiển thị context lịch sử.

Các giới hạn về revision/schema/exception chi tiết và kết quả runtime hiện có được lưu trong báo cáo edition audit riêng tại workspace private; register công khai không thay thế raw audit evidence.
