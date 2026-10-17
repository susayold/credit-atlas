# BLS UNRATE trực tiếp — nghiên cứu nguồn và nghiệm thu tranche D01

Ngày kiểm tra nguồn: **18/10/2026**. Phạm vi là chuỗi thất nghiệp dân sự toàn quốc của Current Population Survey (CPS), dùng làm bối cảnh kinh tế mô tả cho D01. Đây không phải nghiên cứu hay xác nhận mô hình PD.

## Nguồn và quyền sử dụng

Nguồn trực tiếp là [BLS series LNS14000000](https://data.bls.gov/timeseries/LNS14000000), lấy qua [BLS Public Data API](https://api.bls.gov/publicAPI/v1/timeseries/data/). Series là tỷ lệ thất nghiệp của dân số dân sự từ 16 tuổi trở lên, seasonally adjusted, đơn vị phần trăm. BLS nói tài liệu do cơ quan công bố thuộc public domain ngoại trừ ảnh/illustration có bản quyền và yêu cầu người dùng trích dẫn BLS; project lưu attribution cùng snapshot. [Chính sách bản quyền BLS](https://www.bls.gov/opub/copyright-information.htm)

Downloader dùng API v1 không đăng ký. BLS công bố giới hạn tối đa 10 năm mỗi query cho phiên bản không đăng ký; do chuỗi bắt đầu năm 1948, code chia yêu cầu thành 8 đoạn năm không chồng lấn, xác minh identity của `LNS14000000`, tháng hợp lệ, không duplicate, domain 0–100, response size, footnotes và hash từng response. [BLS API FAQ](https://www.bls.gov/developers/api_FAQs.htm)

## Dữ liệu đã tải và đối chiếu

- 945 kỳ tháng từ 1948-01 đến 2026-09, snapshot tải ngày 2026-10-17; một giá trị thiếu được giữ nguyên.
- So với snapshot UNRATE qua FRED đã có trong workspace: **945/945 ngày giao nhau, 0 tháng chỉ có ở một nguồn, 0 mismatch giá trị**. So sánh dùng `Decimal` chính xác theo tháng, không resample và không impute.
- BLS trả tháng 2025-10 là `-` cùng footnote code 9 giải thích dữ liệu không thu thập do shutdown liên bang. Parser chỉ chấp nhận dấu thiếu khi có chú giải nguồn; app giữ null và hiển thị “Unavailable”. BLS xác nhận trong tài liệu seasonal adjustment 2026 rằng October 2025 data were not collected. [BLS revision note 2026](https://www.bls.gov/web/empsit/cps-seas-adjustment-methodology.pdf)
- Exact parity chứng minh định nghĩa/giá trị snapshot phù hợp ở phần dữ liệu quan sát được; nó không tạo quyền đối với dữ liệu FRED, không chứng minh lịch sử vintage, và không cho biết giá trị nào đã có sẵn tại thời điểm quyết định khoản vay.

## Rà soát revisions và cách dùng

BLS re-estimates CPS seasonal factors hằng năm và sửa lịch sử seasonally adjusted trong tối đa 5 năm; giá trị trong snapshot hiện tại vì thế là latest-revised, không phải vintage lúc công bố. BLS cho biết seasonal adjustment dùng chuỗi quan sát tương lai và các revisions thường tích lũy theo kỳ. Riêng 2025, ghi chú revision 2026 cho thấy một số tháng thay đổi 0.1 điểm phần trăm và October không có dữ liệu. [CPS seasonal adjustment methodology](https://www.bls.gov/cps/seasonal-adjustment-methodology.htm), [2026 revisions](https://www.bls.gov/web/empsit/cps-seas-adjustment-methodology.pdf)

Trong D01, chỉ sử dụng UNRATE như **bối cảnh vĩ mô tổng hợp theo tháng**. Không được diễn giải thành unemployment status của borrower, repayment label, default rate, PD, causal effect hoặc predictor đã thẩm định. Route hiện dùng latest-revised series; tuyệt đối không dựng lại PIT lịch sử từ snapshot đã sửa. Nếu model/event-time analysis cần feature này, cần release-vintage hoặc archive có timestamp thực và tái lập được; nếu không có thì đánh dấu unavailable.

## Code và nghiệm thu

`scripts/acquire_bls_unrate.py` lưu responses, normalized `UNRATE.csv`, footnotes, parity report và SHA-256 receipts trong workspace dữ liệu private trên D:, được định danh trong public registry chỉ bằng local receipt ID. `scripts/acquire_public_mortgage_context.py --bls-only` xác minh receipt/hash, dùng BLS trực tiếp, tái sử dụng FHFA HPI và PMMS hiện có chỉ sau khi hash khớp, rồi dựng lại macro context D01; lượt này tạo **0 request mới tới FRED**. CLI mặc định nay tích hợp candidate BLS đã kiểm chứng; đường acquisition FRED cũ chỉ chạy khi truyền rõ `--legacy-fred`, sau khi rights/use gate được giải quyết. Bộ chọn comparator BLS tìm receipt FRED cũ theo đúng `source_url`, không lấy bản BLS mới nhất để so sánh với chính nó. Refresh FHFA sau này cũng chấp nhận receipt UNRATE trực tiếp từ BLS và kiểm hash cả hai series được tái sử dụng. Private raw data và đường dẫn D: không được chép vào repo.

Macro output có 171 tháng; HPI vẫn ở 206 quý, không nội suy; 2025-10 UNRATE vẫn thiếu. `/api/mortgage-macro-context` và `/api/mortgage-macro-context-report` khớp byte-for-byte ở payload 103,225 bytes (SHA-256 `3c1d9d9a4ca91de11a2eee4aba661af9af634cdec015ed32ea477916de59736a`). Browser smoke xác nhận BLS direct, source series ID, attribution, unavailable month, FHFA direct và PMMS qua FRED có nhãn riêng. Model training chưa chạy; predictor qualification false.

PMMS vẫn là Freddie Mac qua FRED; điều khoản/use gate của nó chưa đóng và cần giải quyết riêng. Không suy ra rằng BLS public domain làm sạch quyền của FRED, Freddie Mac, ICE, ALFRED hoặc các nguồn khác. Cũng chưa chạy full foundation rebuild từ raw mortgage sample, model calibration, PIT backtest, Excel-specific acceptance mới cho route này, hoặc tổng nghiệm thu N01–N20.
