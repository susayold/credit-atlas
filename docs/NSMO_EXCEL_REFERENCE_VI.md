# NSMO v7.0 — workbook tra codebook và category

Người dùng app có thể tải [CreditAtlas-NSMO-Reference.xlsx](../apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx) ngay trong khu vực “Tra từ điển 587 trường dữ liệu”. Workbook gom các bảng tra cứu vốn nằm ở nhiều file CSV thành một file Excel có filter, Excel Table, hàng tiêu đề cố định và sheet hướng dẫn.

Workbook có năm sheet: **Bắt đầu** giải thích phạm vi; **Từ điển 587 trường** giữ đầy đủ field name, tên trong codebook, câu hỏi, wave, SAS label/format, thời điểm và predictor gate; **Nhãn và category** nối mã category với label SAS; **Coverage theo wave** ghi wave có phản hồi, not-asked và not-applicable; **So sánh wording item** ghi nhận kiểm tra questionnaire và giới hạn khi so trend. Mã gốc, gồm `-2`/`-3`, được giữ nguyên để người dùng lọc và đối chiếu.

Workbook chỉ chứa metadata/codebook đã làm sạch, không có bản ghi khoản vay. Các CSV tại `docs/data/` vẫn là nguồn chuẩn cho API, schema validation và tái tạo workbook; chúng không bị đổi thành file nhị phân hoặc xóa. Khi cập nhật các bảng CSV, chạy:

```powershell
node scripts/build_nsmo_reference_workbook.mjs . apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx
```

Sau đó chạy `python -m pytest tests/test_nsmo_reference_workbook.py tests/test_nsmo_views.py -q`. Endpoint tải workbook là `/downloads/nsmo-reference.xlsx`.
