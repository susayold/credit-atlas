# NSMO v7.0 — ranh giới thời điểm và kiểm duyệt predictor

## Mục tiêu

Tài liệu này đi cùng sheet **NSMO feature gates** trong workbook. Nó phân loại cả 587 trường theo lúc đo và vai trò tiềm năng, để nhóm phân tích có thể lọc, rà soát và ghi chú trong Excel trước khi thiết kế mô hình. Đây là inventory kiểm duyệt; **chưa có trường nào được phê duyệt làm predictor**.

## Các nhóm sử dụng

| Ranh giới | Số trường | Cách hiểu / giới hạn |
|---|---:|---|
| Trường trả lời khảo sát sau khi khoản vay đã mở | 319 | Chỉ dùng phân tích mô tả câu trả lời. Không dùng làm predictor tại thời điểm xét vay; có chọn lọc người trả lời, wave và hình thức khảo sát. |
| Candidate động cần xác nhận as-of | 125 | 102 snapshot điểm tín dụng theo quý và 23 trường forbearance. Chỉ có thể xem xét trong bài toán monitoring tại landmark, sau khi xác nhận thời điểm thông tin thực sự sẵn có. |
| Candidate động cần kiểm tra look-ahead | 51 | MTM LTV theo quý. Phải xác nhận ngày định giá và độ trễ trước landmark; giá trị được công bố sau landmark có thể làm rò rỉ tương lai. |
| Lịch sử kết quả / chỉ dùng lag | 51 | Trạng thái performance theo quý. Dùng để dựng outcome hoặc lịch sử đã quan sát nghiêm ngặt trước landmark; không lấy trạng thái cùng quý/tương lai làm feature. |
| Candidate thuộc tính lúc khởi tạo, cần xem xét | 25 | 20 thuộc tính mortgage/borrower và 5 trường điểm origination. Cần xác minh đúng population, vai trò borrower, định nghĩa và thông tin có mặt tại thời điểm quyết định. Điểm origination trong NSMO là VantageScore 3.0; không đổi nhãn thành FICO. |
| Định nghĩa candidate cần chốt | 1 | Cash-out/refinance flag cần kiểm tra định nghĩa và thời điểm availability. |
| Nhạy cảm hoặc proxy, cần governance | 7 | Các trường tuổi, giới tính và metro/LMI được tách riêng; trạng thái hiện tại yêu cầu rà soát governance độc lập trước mọi quyết định sử dụng. |
| Cohort/thời gian/thiết kế mẫu/trọng số/ID/kết thúc | 8 | Chỉ làm cohort, phân tầng, trọng số ước lượng, join có kiểm soát, competing event hoặc censoring; không phải predictor tín dụng thông thường. |

## Vì sao chưa lập allowlist

Trước khi cho phép bất kỳ predictor nào, D02 phải chốt target và đơn vị quan sát, landmark/risk set, cửa sổ dự báo, xử lý khoản vay trả hết hoặc chấm dứt quan sát, quy tắc censoring và cách tính uncertainty theo thiết kế mẫu. Với predictor, phải có bằng chứng trường đó có thể biết trước hoặc tại landmark, không lấy snapshot tương lai, không trộn câu trả lời khảo sát sau mở khoản vay vào underwriting, và phải đánh giá missingness/chọn mẫu. Quyết định sử dụng trường nhạy cảm/proxy cần governance riêng. Các điều kiện này chưa đồng thời được xác nhận; vì vậy workbook giữ tất cả trạng thái ở dạng chưa phê duyệt.

## Cách thao tác trong Excel

Mở `CreditAtlas-D02-Data-Reference.xlsx` → `NSMO feature gates`. Có thể lọc `CreditAtlas use boundary` để xem từng nhóm; lọc `Current approval status` để tách candidate còn review khỏi trường chỉ làm outcome/control/exclusion. Thêm nhận xét của nhóm vào cột mới trong bản làm việc; không sửa CSV nguồn chuẩn. Khi nhóm thay đổi định nghĩa target hay landmark, ghi lại quyết định, ngày hiệu lực, người duyệt và kiểm tra lại `Open review before use`.

Không dùng cột `Publisher gate` một mình để suy ra CreditAtlas đã duyệt feature. Bảng này kết hợp codebook, family và timing thành phân loại thận trọng của dự án; nó không thay thế đánh giá nghiệp vụ, phương pháp, pháp lý hay governance.

## Nguồn và phạm vi

- FHFA, [NSMO Public Use File](https://www.fhfa.gov/data/nsmo): mô tả release v7.0, phạm vi mortgage và file codebook.
- FHFA, [NSMO Technical Report v7.0](https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf): thiết kế mẫu, trọng số, wave và quy trình khảo sát.
- FHFA, [NSMO questionnaires, waves 15–18](https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-15-to-18): ví dụ về routing/skip logic trực tuyến.
- Bảng feature gates là metadata dẫn xuất từ dictionary đã làm sạch; không chứa mortgage-level PUF records.
