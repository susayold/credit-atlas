# NSMO v7.0 — rà soát routing của biến khảo sát

## Phạm vi và kết quả

Sheet **NSMO routing** trong workbook crosswalk toàn bộ 319 trường `survey_response` với question reference, wave range, điều kiện ghi trong codebook và cờ biến thể. Kết quả được tạo từ dictionary công khai đã chuẩn hóa; nó không suy diễn rằng trường không có điều kiện ghi kèm chắc chắn được hỏi ở mọi wave hoặc cả hai phương thức.

| Trạng thái rà soát | Số trường | Cách xử lý |
|---|---:|---|
| `CONDITIONAL_ROUTING_DOCUMENTED` | 58 | Codebook ghi rõ điều kiện; kiểm tra bảng hỏi đúng wave và mode trước khi diễn giải câu trả lời/missing. |
| `LEGACY_GATEWAY_MAPPING_REQUIRED` | 12 | Codebook nói một gateway đã nghỉ hưu từng quyết định việc hỏi câu; cần ánh xạ gateway cũ theo wave. Không mặc định -3 là cùng một lý do qua thời gian. |
| `NO_CONDITION_LISTED_IN_CODEBOOK` | 249 | Dictionary không ghi điều kiện tại dòng đó; đây không phải bằng chứng tính bất biến qua wave/mode. |

Mỗi trường có đúng một loại điều kiện routing. Question reference là chiều riêng: 312 ghi tường minh trong dictionary; 7 dòng từng thiếu mã đã được đối chiếu bằng variable ID `X##` với câu hỏi cùng số trong questionnaire package áp dụng. Kiểm tra lại 22 package PDF bao phủ wave 1–46 nhận diện 91 số câu và xác nhận cả 7 mapping có câu tương ứng trong các wave liên quan. Sáu trong bảy có phrase item tương ứng; `x17g_1` được gắn `WAVE_VARIANT_REVIEW` vì nhãn mô tả biến thể cũ “term less than 30 years” còn câu hỏi cho waves 7–46 ghi “A term of 30 years”. Bốn trong bảy dòng đối chiếu có điều kiện routing, nên hai chiều không cộng loại trừ nhau. Sáu câu hỏi đã có review so sánh wording/scale riêng trong `nsmo-v70-wave-item-comparability.csv`; routing inventory này bổ sung trường-và-điều kiện, không thay thế đánh giá comparability hoặc chứng minh câu hỏi đo cùng một khái niệm.

## Cách dùng trong Excel

Mở sheet **NSMO routing**, bật filter trên `Question-reference reconciliation = RECONCILED_FROM_FIELD_ID_AND_QUESTIONNAIRE` để rà 7 mã được khôi phục, hoặc `Routing review status = LEGACY_GATEWAY_MAPPING_REQUIRED` để xem gateway cũ. `Codebook wave range` và `Wave variation flags` giúp xác định nhóm bảng hỏi cần đọc. Ghi lại phiên bản questionnaire, mode, wave và logic rẽ nhánh đã kiểm tra trong bản làm việc. Không chuyển missing hoặc không hỏi thành “No”, “không có rủi ro”, hay trạng thái borrower.

Nguồn questionnaire chính thức cho wave 1–46 đã được tải và hash-audit thành 22 package PDF trong workspace nghiên cứu riêng; các PDF/receipts không nằm trong public repository. Bảng routing public chỉ chứa crosswalk metadata, không chứa response records.

## Việc còn mở trong D02-2

- Xác nhận 10 gateway đã nghỉ hưu ứng với question/response path nào trong từng nhóm wave và phương thức mail/online.
- Giữ liên kết 7 reference đã phục hồi với trang codebook và package questionnaire để người dùng tái kiểm tra; xác nhận riêng wording-variant của x17g_1.
- Rà 56 điều kiện có điều kiện với wording và skip logic thực tế; codebook condition là điểm xuất phát, không phải full path graph.
- Rà những trường không có điều kiện theo phiên bản questionnaire; status `NO_CONDITION_LISTED_IN_CODEBOOK` không tự cấp quyền gộp trend hoặc dùng làm predictor.

Vì các bảng hỏi có cấu trúc online và paper khác nhau, và không có trường response-mode ở cấp mortgage trong PUF, inventory này không thể xác định đáp viên nào gặp đường rẽ nhánh nào. Nó làm rõ phần cần kiểm tra nhưng không đóng được routing equivalence hay feature allowlist.

Nguồn: FHFA [NSMO PUF và technical documentation](https://www.fhfa.gov/data/nsmo), questionnaire package được liên kết từ cùng trang phát hành.
