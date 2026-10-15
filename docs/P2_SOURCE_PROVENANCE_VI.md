# P2 — nguồn annual sample và thời điểm dữ liệu

Phần Sources đã thay nhãn “Official annual sample / Authorized annual source” bằng **Supplied annual source**. Release 47 là khai báo trong receipt của file được cung cấp, chưa được xác thực bằng publisher hash registry. Có 50.000 khoản vay và 4.510.559 loan-months trong corpus đang dùng; đây không phải toàn bộ thị trường mortgage.

## Metadata hiện tại

| Thuộc tính | Bằng chứng / cách hiểu |
|---|---|
| Origination vintage | 2012; không đồng nghĩa ngày bắt đầu quan sát từng khoản vay |
| Release | Receipt-declared 47; source run khai báo cùng release |
| Research use | Receipt ghi người dùng xác nhận; không phải xác minh độc lập giấy phép |
| Nhận file | 2026-09-09T20:02:22.727558+00:00 |
| Extraction bắt đầu | 2026-10-08T11:50:01.600099+00:00 |
| Extraction kết thúc | 2026-10-08T11:52:16.443585+00:00 |
| Foundation rebuild hoàn tất | 2026-10-08T11:53:13.563368+00:00 |
| Case hoàn tất | 2026-10-08T11:55:27.805531+00:00 |
| Ngày publisher công bố | Không có bằng chứng; API trả null |
| Publisher release authenticated | false |
| Public release approved | false |

Hash byte và các receipt khớp nhau chứng minh tính nhất quán của lineage đã ghi, không tự chứng minh ai phát hành file hoặc ngày công bố. Không dùng ngày extraction/rebuild thay cho publication hoặc point-in-time availability.

## API và bản xuất

`GET /api/mortgage-provenance?run=d01-a24484b21a21` và endpoint `-report` trả metadata whole-source, không áp segment hay khoảng ngày. Case được kiểm tra bằng frozen service; helper đối chiếu raw digest giữa case/foundation/source receipt, hash source-use receipt và source-run receipt, rồi kiểm tra release/data-kind nhất quán. Receipt bị đổi hoặc khai báo mâu thuẫn sẽ bị từ chối.

Kết quả không chứa đường dẫn máy, filename gốc, raw loan ID hay thông tin xác thực. Bản JSON riêng giữ cùng scope với thẻ Sources. Không thay snapshot frozen hoặc train lại model.

## Kiểm tra đã thực hiện

- `private evidence omitted from public release`: 25 tests PASS, gồm 8 tests provenance và frozen-service regression.
- `private evidence omitted from public release`: 4 segment scopes PASS; metadata so trực tiếp với source-use receipt; JSON tải về khớp API; 4 query không hợp lệ bị từ chối và cross-origin trả 403; mobile 390px không overflow; ledger holdout không đổi.
- `private evidence omitted from public release`: cả 4 whole-source quality scopes và exports vẫn PASS sau thay đổi.
- Portfolio: 6 scopes/408 bucket checks/360 chart points PASS; Lifecycle: 10 timelines PASS; Transition: 6 scopes PASS; Competing outcomes: 12 scopes PASS; Cure/Redefault: 8 follow-up scopes và 4 event types PASS. Receipt mới được ghi trong `runtime_regression_evidence` của P2.02–P2.07.
- `private evidence omitted from public release`: audit toàn bộ index/corpus, 16 list scopes, 10 timeline probes và scan 15 static assets PASS sau thay đổi UI/API; holdout ledger không đổi.

Tại checkpoint sửa provenance, P2.01 chưa được nâng nghiệm thu chỉ dựa vào thay nhãn. Audit đầy đủ source/run explorer, lineage và data readiness sau đó được ghi tại [P2_SOURCE_RUN_ACCEPTANCE_VI.md](P2_SOURCE_RUN_ACCEPTANCE_VI.md). Các annual vintages mới, publisher provenance/availability và mô hình multi-vintage chưa đủ bằng chứng. Mục tiêu toàn dự án chưa đạt 100%.
