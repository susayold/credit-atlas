# CreditAtlas — nhật ký triển khai theo plan mới

Ngày cập nhật: **17/10/2026**. Plan tổng và thứ tự N01–N24: [PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md](PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md).

## Đợt đang thực hiện: N01–N03 và N05–N06

### N01 — tiến độ dùng chung

- Thêm API `GET /api/project-register`; tổng 50 yêu cầu và tỷ lệ hoàn thành được tính từ `COMPLETION_REQUIREMENTS_50.json`, không gõ riêng số tổng vào UI.
- UI có tổng P1–P5 và D01 R0–R4 ở hai khối riêng. Phần trăm hiển thị chỉ là tỷ trọng capability acceptance của toàn CreditAtlas.
- Completion flags của ledger không đổi. API giữ scope note để giải thích điều kiện còn lại của từng capability.

### N02 — danh mục nguồn dữ liệu

- Tạo catalog ban đầu gồm **24 nhóm dữ liệu trọng tâm**, có domain, grain, kỳ, trạng thái acquisition/audit, quyền truy cập, mục đích, giới hạn, bước tiếp và đường dẫn evidence/nhà phát hành.
- Phân biệt Freddie annual samples đang chờ authenticated access, Ginnie production chưa tải, dữ liệu exposure private và nguồn public đã audit.
- Đây chưa phải census mọi raw source trong workspace và chưa map đủ mọi KPI trong app. Việc nối từng receipt/source version và kiểm tra rights theo từng release tiếp tục trong N02.

### N03 — provenance và phương pháp

- Ghi nhận bảy loại giá trị: reported, derived, publisher-imputed, model-preprocessing-imputed, model prediction, declared scenario và forecast.
- Thêm tám method cards gắn dataset, target, cách tính/protocol, validation đã lưu, giới hạn và model/data evidence. Các card bao gồm D01 transitions, UCI350, UCI365, NMDB, HMDA fixed-mix, P4 scenario/ECL và Toyota/Nissan reconciliation.
- Các giả định P4 hiển thị đúng scope illustrative: lịch bullet 36 tháng, monthly EIR 0,004, weights 0,7/0,3; source expected loss vẫn unavailable. Không tạo biến dự phóng mới.
- N03 vẫn đang làm: mọi KPI/output số trên toàn app chưa được liên kết tới method ID và input lineage ngay trong view.

### N05 — canonical FHFA NMDB aggregate mart

- Dựng `data/derived/fhfa-nmdb-market-statistics/market-statistics.parquet` trong private workspace từ hai ZIP có receipt PASS; dữ liệu public raw không được chép vào public checkout.
- Mart chứa 3.573.564 hàng aggregate, khóa có product để giữ riêng annual origination flow và quarterly outstanding stock. Raw strings, nullable numeric values, geography, units, suppression, release và source hashes được giữ.
- Đối soát source profile: 3.038.100 New + 535.464 Outstanding; 4.980 dòng New suppressed; missing VALUE1/VALUE2 lần lượt 135.084/337.292 ở New và 0/57.888 ở Outstanding; zero invalid numeric rows.
- Phân biệt series theo FHFA Appendix B/C. Các series được publisher ghi VALUE1-only không cho chọn VALUE2 dù file raw có thể chứa ô ở cột VALUE2.
- Dataset profile cho thấy 37 Outstanding series IDs, không phải 38 như dòng trong research checkpoint cũ; đã sửa tài liệu nguồn.

### N06 — app và Excel

- Thêm P2 view `nmdb` với product, geography level/id, market, series, trọng số và year filters; có time-series chart, latest-period KPI, liền-kề delta, missing/suppression, provenance và use limits.
- Thêm API catalog/report và query-scoped `.xlsx` endpoint. Workbook reference National / USA / All Mortgages có 1.680 New annual + 1.998 Outstanding quarterly rows, 97 codebook definitions, latest KPIs và quality/lineage.
- Export giữ VALUE1/VALUE2 raw, giá trị đã parse, suppression, selected measure, filter context, source release và mart SHA-256. Excel không nhồi toàn bộ 3,57 triệu aggregate rows vào một sheet.
- N05/N06 chưa đóng acceptance tổng: API và download đã có smoke check runtime ngày 17/10; browser acceptance và mở workbook trong Excel desktop vẫn còn mở. Không tăng completion 26/50 chỉ vì thêm implementation.

### Runtime review N05/N06 — 17/10/2026

- Catalog runtime trả đúng 3.038.100 New annual / 60 series / 27 markets và 535.464 Outstanding quarterly / 37 series / 4 markets.
- New National / USA / All Mortgages, `AVE_INTRATE`, VALUE1 trả 28 năm 1998–2025; giá trị cuối 2025 là 6,3% theo source scale. Outstanding `AVE_MTMLTV`, VALUE2 trả 54 quý đến 2026Q2; giá trị cuối là 54,2%.
- VALUE2 cho Outstanding `TOT_UPB` bị từ chối HTTP 400 theo quy tắc VALUE1-only của FHFA.
- Query-scoped Excel export cho New annual và Outstanding quarterly đều trả HTTP 200. Đã đọc cấu trúc XLSX: bốn sheet; biểu đồ bind cột `Selected value` và nhãn kỳ dạng text, không che bảng dữ liệu. Workbook tham chiếu tải qua route HTTP 200, 389.862 bytes.
- Đây là runtime/API/export check; chưa thay thế browser visual acceptance hay Excel desktop open/recalculate review.

## Giao diện

Trang **Tiến độ & registry** trong điều hướng chung hiển thị capability acceptance, D01 releases, dataset filters, quyền truy cập, method cards và giới hạn. Register JSON có thể tải xuống. Không đưa raw borrower rows hoặc private exposure values vào catalog.

Workbook plan ở `docs/reviews/` đã cập nhật trạng thái N01–N03 thành **Đang làm** và ghi cụ thể phần còn lại; không đổi tỷ lệ acceptance 26/50.

## Trạng thái kiểm tra

JSON/Python/JavaScript syntax và `git diff --check` được kiểm tra. Không chạy test suite. API catalog/report, weight restriction, dynamic XLSX và static workbook download đã được kiểm tra trên server local. Browser visual acceptance và Excel desktop open/recalculate check chưa chạy; do đó N06 vẫn mở. N01–N03 cũng chưa được đánh dấu nghiệm thu cuối. Lượt trước có public regression riêng 1.670 passed/196 skipped; kết quả đó có trước các thay đổi này và không kiểm chứng code mới.

## Bước kế tiếp

1. Browser review N06 và Excel desktop open/recalculate; xác nhận bộ lọc, chart, bảng, missingness và lineage hiển thị đúng.
2. Mở rộng N02 từ 24 nhóm trọng tâm tới nguồn thực sự cấp dữ liệu cho mỗi KPI, bind release/hash receipt khi có.
3. Nối KPI outputs vào method cards, gồm numerator/denominator, data release/as-of, formula và missingness; giữ các score/final holdout đã freeze nguyên trạng.
4. Tiếp tục N07–N09: Toyota/Nissan ABS reconciliation và surveillance finding/export theo plan tổng.
