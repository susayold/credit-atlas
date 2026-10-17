# NSMO v7.0 — workbook tra codebook và category

Người dùng app có thể tải [CreditAtlas-NSMO-Reference.xlsx](../apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx) ngay trong khu vực “Tra từ điển 587 trường dữ liệu”. Workbook gom các bảng tra cứu vốn nằm ở nhiều file CSV thành một file Excel có filter, Excel Table, hàng tiêu đề cố định và sheet hướng dẫn.

Để thao tác toàn bộ dữ liệu D02 trong một file, tải [CreditAtlas-D02-Data-Reference.xlsx](../apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx) ở đầu phần NSMO. File 24 sheet bao gồm mọi bảng CSV công khai trong `docs/data/`: 9 bảng NSMO, NMDB national và state, FHFA state HPI, 7 bảng HUD FHA (monthly, subgroups, lý do mới vào 90+, foreclosure, REO recovery theo địa lý, REO loss components và serious-delinquency transitions), cùng bốn sheet định nghĩa NMDB national/state, HUD, FHFA HPI và sheet hướng dẫn. Mỗi bảng nguồn là Excel Table có filter, tiêu đề cố định và các cột số để sort/tính toán; các mã category được giữ như mã gốc. JSON receipt là hồ sơ provenance/method, không phải bảng dữ liệu để lọc; vẫn giữ riêng làm bằng chứng kiểm tra. Workbook HUD riêng cũng có đầy đủ bảy bảng của các report HUD; FHA Production Report Table 2 được tách khỏi FHA Loan Performance Trends.

Workbook có năm sheet: **Bắt đầu** giải thích phạm vi; **Từ điển 587 trường** giữ đầy đủ field name, tên trong codebook, câu hỏi, wave, SAS label/format, thời điểm và predictor gate; **Nhãn và category** nối mã category với label SAS; **Coverage theo wave** ghi wave có giá trị không thiếu trong PUF, not-asked và not-applicable; **So sánh wording item** ghi nhận kiểm tra questionnaire và giới hạn khi so trend. FHFA có thể impute câu trả lời thiếu vào biến `X`, nhưng PUF không có cờ `J` theo item để nhận diện từng giá trị đã impute. Do đó coverage không phải borrower response rate; các biến `Z` chỉ ghi nhận trả lời thực tế ở một số item được chọn. Mã gốc, gồm `-2`/`-3`, được giữ nguyên để người dùng lọc và đối chiếu.

Workbook D02 tổng hợp có 24 sheet: hướng dẫn; 9 bảng NSMO gồm fields, feature gates, routing, question-reference reconciliation, categories, wave coverage, item wording, returns và usability; NMDB national/state, FHFA HPI state, 7 bảng HUD; và bốn sheet định nghĩa NMDB national/state, HUD, FHFA HPI. Sheet **HUD 90+ reasons** giữ tỷ trọng nguyên nhân báo cáo (tổng 100%, không xem là predictor/cause); **HUD foreclosure** tách số bắt đầu, tồn kho đang foreclosure, claims và annualized rate; **HUD REO recovery** giữ recovery theo bang/lãnh thổ, kể cả tỷ lệ có thể trên 100%; **HUD REO loss** ghi các thành phần không cộng trực tiếp thành net loss; **HUD transitions** giữ flow/stock serious delinquency theo tháng cùng hai phép đối soát. Sheet **NSMO feature gates** phân loại đủ 587 trường theo thời điểm đo, phạm vi sử dụng và review còn mở; hiện không feature nào được duyệt. Sheet **NSMO routing** crosswalk 319 trường khảo sát với câu hỏi, wave và điều kiện codebook; 7 reference không ghi tường minh trong dictionary đã được đối chiếu với questionnaire, trong đó x17g_1 vẫn cần rà biến thể wording. Sheet question-reference cho phép lọc riêng bằng chứng của 7 dòng này. Routing gắn cờ 12 dòng dùng gateway cũ. Xem `NSMO_PREDICTOR_TIMING_REVIEW_VI.md` và `NSMO_ROUTING_REVIEW_VI.md` để hiểu giới hạn và việc cần rà tiếp. Sheet **NSMO returns** có 48 dòng tổng hợp Table 3; sheet **NSMO usability** nối Table 4 với Tables 5–6 cho 46 wave, giữ riêng returned, usable, disposition và scope gap. Wave 47–48 được đánh dấu ngoài PUF v7.0. Đây là thống kê cấp wave, không chứa response-mode hay disposition gắn với từng mortgage.

Workbook chỉ chứa metadata/codebook đã làm sạch, không có bản ghi khoản vay. Các CSV tại `docs/data/` vẫn là nguồn chuẩn cho API, schema validation và tái tạo workbook; chúng không bị đổi thành file nhị phân hoặc xóa. Khi cập nhật các bảng CSV, chạy:

```powershell
node scripts/build_nsmo_reference_workbook.mjs . apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx
node apps/excel/build_d02_data_reference.mjs . apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx
python scripts/add_nmdb_state_to_reference_workbook.py
```

The D02 workbook is built in two steps because re-importing the 79,968-row NMDB
state panel together with all other sheets exceeds the bundled spreadsheet
runtime's memory limit. The second step appends that verified panel and its
definitions to the workbook without rebuilding the other sheets.

Sau đó chạy `python -m pytest tests/test_nsmo_reference_workbook.py tests/test_d02_data_reference_workbook.py tests/test_nsmo_views.py -q`. Endpoint tải workbook từ điển riêng là `/downloads/nsmo-reference.xlsx`; file tổng hợp D02 được tải tại `/downloads/d02-data-reference.xlsx`.
