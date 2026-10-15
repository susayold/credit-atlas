# NSMO v7.0 — workbook tra codebook và category

Người dùng app có thể tải [CreditAtlas-NSMO-Reference.xlsx](../apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx) ngay trong khu vực “Tra từ điển 587 trường dữ liệu”. Workbook gom các bảng tra cứu vốn nằm ở nhiều file CSV thành một file Excel có filter, Excel Table, hàng tiêu đề cố định và sheet hướng dẫn.

Để thao tác toàn bộ dữ liệu D02 trong một file, tải thêm [CreditAtlas-D02-Data-Reference.xlsx](../apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx) ở đầu phần NSMO. File tổng hợp gồm NSMO field/category/coverage/wording, số lượng phản hồi và kênh trả lời theo wave, NMDB quarterly, HUD FHA monthly và subgroup tables. Mỗi bảng là Excel Table có filter, hàng tiêu đề cố định và kiểu dữ liệu số phù hợp để sort/tính toán. Các workbook nguồn riêng vẫn được giữ trong app để người dùng tải theo chủ đề.

Workbook có năm sheet: **Bắt đầu** giải thích phạm vi; **Từ điển 587 trường** giữ đầy đủ field name, tên trong codebook, câu hỏi, wave, SAS label/format, thời điểm và predictor gate; **Nhãn và category** nối mã category với label SAS; **Coverage theo wave** ghi wave có phản hồi, not-asked và not-applicable; **So sánh wording item** ghi nhận kiểm tra questionnaire và giới hạn khi so trend. Mã gốc, gồm `-2`/`-3`, được giữ nguyên để người dùng lọc và đối chiếu.

Workbook D02 tổng hợp có 10 sheet: hướng dẫn; NSMO fields, categories, wave coverage, item wording và returns; NMDB quarterly và definitions; HUD monthly và subgroups. Sheet **NSMO returns** có 48 dòng tổng hợp theo wave từ FHFA Table 3; wave 47–48 được đánh dấu không thuộc PUF v7.0. Đây là thống kê phản hồi cấp wave, không phải response mode gắn với từng khoản vay.

Workbook chỉ chứa metadata/codebook đã làm sạch, không có bản ghi khoản vay. Các CSV tại `docs/data/` vẫn là nguồn chuẩn cho API, schema validation và tái tạo workbook; chúng không bị đổi thành file nhị phân hoặc xóa. Khi cập nhật các bảng CSV, chạy:

```powershell
node scripts/build_nsmo_reference_workbook.mjs . apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx
node apps/excel/build_d02_data_reference.mjs . apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx
```

Sau đó chạy `python -m pytest tests/test_nsmo_reference_workbook.py tests/test_d02_data_reference_workbook.py tests/test_nsmo_views.py -q`. Endpoint tải workbook từ điển riêng là `/downloads/nsmo-reference.xlsx`; file tổng hợp D02 được tải tại `/downloads/d02-data-reference.xlsx`.
