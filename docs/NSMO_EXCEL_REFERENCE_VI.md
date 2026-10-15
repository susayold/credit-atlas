# NSMO v7.0 — workbook tra codebook và category

Người dùng app có thể tải [CreditAtlas-NSMO-Reference.xlsx](../apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx) ngay trong khu vực “Tra từ điển 587 trường dữ liệu”. Workbook gom các bảng tra cứu vốn nằm ở nhiều file CSV thành một file Excel có filter, Excel Table, hàng tiêu đề cố định và sheet hướng dẫn.

Để thao tác toàn bộ dữ liệu D02 trong một file, tải [CreditAtlas-D02-Data-Reference.xlsx](../apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx) ở đầu phần NSMO. File tổng hợp gồm mọi bảng CSV công khai trong `docs/data/`: NSMO field/category/coverage/wording/routing/question-reference reconciliation, số lượng phản hồi theo wave, NMDB quarterly, HUD FHA monthly và subgroup tables. Mỗi bảng là Excel Table có filter, hàng tiêu đề cố định và kiểu dữ liệu số phù hợp để sort/tính toán. JSON receipt là hồ sơ provenance/method, không phải bảng dữ liệu để lọc; vẫn giữ riêng làm bằng chứng kiểm tra. Các workbook nguồn riêng vẫn được giữ trong app để người dùng tải theo chủ đề.

Workbook có năm sheet: **Bắt đầu** giải thích phạm vi; **Từ điển 587 trường** giữ đầy đủ field name, tên trong codebook, câu hỏi, wave, SAS label/format, thời điểm và predictor gate; **Nhãn và category** nối mã category với label SAS; **Coverage theo wave** ghi wave có phản hồi, not-asked và not-applicable; **So sánh wording item** ghi nhận kiểm tra questionnaire và giới hạn khi so trend. Mã gốc, gồm `-2`/`-3`, được giữ nguyên để người dùng lọc và đối chiếu.

Workbook D02 tổng hợp có 14 sheet: hướng dẫn; NSMO fields, feature gates, routing, question-reference reconciliation, categories, wave coverage, item wording, returns và usability; NMDB quarterly và definitions; HUD monthly và subgroups. Sheet **NSMO feature gates** phân loại đủ 587 trường theo thời điểm đo, phạm vi sử dụng và review còn mở; hiện không feature nào được duyệt. Sheet **NSMO routing** crosswalk 319 trường khảo sát với câu hỏi, wave và điều kiện codebook; 7 reference không ghi tường minh trong dictionary đã được đối chiếu với questionnaire, trong đó x17g_1 vẫn cần rà biến thể wording. Sheet question-reference cho phép lọc riêng bằng chứng của 7 dòng này. Routing gắn cờ 12 dòng dùng gateway cũ. Xem `NSMO_PREDICTOR_TIMING_REVIEW_VI.md` và `NSMO_ROUTING_REVIEW_VI.md` để hiểu giới hạn và việc cần rà tiếp. Sheet **NSMO returns** có 48 dòng tổng hợp Table 3; sheet **NSMO usability** nối Table 4 với Tables 5–6 cho 46 wave, giữ riêng returned, usable, disposition và scope gap. Wave 47–48 được đánh dấu ngoài PUF v7.0. Đây là thống kê cấp wave, không chứa response-mode hay disposition gắn với từng mortgage.

Workbook chỉ chứa metadata/codebook đã làm sạch, không có bản ghi khoản vay. Các CSV tại `docs/data/` vẫn là nguồn chuẩn cho API, schema validation và tái tạo workbook; chúng không bị đổi thành file nhị phân hoặc xóa. Khi cập nhật các bảng CSV, chạy:

```powershell
node scripts/build_nsmo_reference_workbook.mjs . apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx
node apps/excel/build_d02_data_reference.mjs . apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx
```

Sau đó chạy `python -m pytest tests/test_nsmo_reference_workbook.py tests/test_d02_data_reference_workbook.py tests/test_nsmo_views.py -q`. Endpoint tải workbook từ điển riêng là `/downloads/nsmo-reference.xlsx`; file tổng hợp D02 được tải tại `/downloads/d02-data-reference.xlsx`.
