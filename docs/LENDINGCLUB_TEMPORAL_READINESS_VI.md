# LendingClub — kiểm tra thời gian, cutoff và maturity

Ngày 12/10/2026. Phạm vi: accepted file của publisher snapshot đã acquire. Đây là temporal evidence, chưa phải PD12 labels hoặc nghiệm thu OOT model.

## 1. Các trường ngày đo những việc khác nhau

| Field | Ý nghĩa quan sát | Valid records | Earliest month | Latest month |
|---|---|---:|---|---|
| issue_d | Funded month |2,260,668|2007-06|2018-12|
| last_pymnt_d | Tháng nhận payment gần nhất |2,258,241|2007-12|2019-03|
| last_credit_pull_d | Tháng credit pull gần nhất |2,260,596|2007-05|2019-04|
| next_pymnt_d | Tháng payment tiếp theo theo lịch |915,358|2008-01|2019-05|

Không có nonblank unparsed value ở bốn fields trong census. Các giá trị là month-level; dùng ngày đầu tháng làm anchor tính month difference không biến chúng thành ngày giao dịch thật.

Latest activity hoặc scheduled date không chứng minh observation cutoff chung. Đặc biệt next_pymnt_d là lịch, không phải kết quả tương lai đã quan sát. Ngày creation/upload/compression của file cũng không tự chứng minh ngày tất cả loans được cập nhật đồng nhất.

## 2. Payment span và chronology

Census trên 2,260,701 raw records có 1,024 nhóm issue-month/status/term:

- 1,519,965 records có khoảng cách booked month đến last payment month ít nhất 12 tháng.
- 0 records có last-payment month trước booked month.
- 2,255 records có last credit-pull month trước booked month.
- 33 records thiếu booked month/term; giữ ngoài dated cohort counts.
- member_id thiếu ở toàn bộ raw records, chưa xác minh grouping theo borrower.

Span ≥12 tháng chỉ mô tả hai timestamps. Nó không chứng minh 12 tháng observation liên tục, không có gaps, không từng default hoặc target đã đủ maturity. Payment sau cure/default cũng chưa được phân biệt bởi terminal snapshot.

Credit pull trước booking có thể phù hợp đánh giá trước giải ngân; không tự là lỗi. Không dùng chronology count này làm quy tắc loại records khỏi modelling nếu chưa có semantics/protocol.

## 3. Vì sao chưa thể tạo PD12 labels

Cần default-event definition, first-event time, exits/censoring, certified observation cutoff và chronology của feature values. loan_status hiện tại không cung cấp toàn bộ event history; last payment không thay thế first default date. Rejected applications không có repayment outcome của khoản không được cấp.

Không tự gắn Fully Paid thành chưa từng default trong 12 tháng; không gắn Current thành đã quan sát đủ 12 tháng; không lấy một tháng latest date của toàn file làm cutoff cho từng loan. Trạng thái sau quyết định không dùng làm application-time predictor.

Một temporal split theo issue_d là cohort partition. Nó chưa là OOT qualification nếu target/horizon, population, maturity và leakage constraints chưa đạt. Borrower grouping chưa được kiểm chứng do member_id thiếu.

## 4. Phương pháp và verification

Profile DuckDB với memory limit 512 MB, temp storage trên D: `artifacts/private/lendingclub-temporal-profile-1333a9b4a286/profile.json`.

Profile SHA-256: `8b4b6cbee90ef9b9ff09f29f62a183c28a000cf0cb9725e23582ecc7ec529425`.

Independent Arrow/GZIP audit: `artifacts/private/lendingclub-temporal-audit-eb737547b85a/receipt.json`, PASS 4 date profiles và 5,120 metrics của 1,024 cohort groups. Parser, month-ordinal arithmetic và aggregations khác implementation chính. Source hashes và frozen holdout ledger được kiểm tra; không fit/rescore model.

Windows Arrow không parse English abbreviated months trực tiếp trong runtime này. Auditor chuyển literal month sang numeric year/month, dùng day1 chỉ làm anchor tháng và parse numeric date. Không sử dụng timezone hoặc diễn giải thành actual event day. Các lượt lỗi parser trước sửa không được dùng làm evidence PASS.

Backend/HTTP: `artifacts/private/lendingclub-temporal-http-tests-20261012.xml`, 34 tests PASS. Kiểm tra scope Current, global date profiles, missing-date records, integrity guard, rejected-not-applicable và giữ cutoff/PD12/maturity unavailable.

## 5. API/UI

Full LendingClub report thêm `temporal_evidence`. Accepted trả source date profiles toàn file và cohort/term/span counts trong window/category đã chọn. Rejected trả not-applicable, không nhận follow-up của accepted.

App hiển thị date roles/min/max, selected payment-span counts, chronology counts, table cohort evidence và inputs cần trước fit. Các output certified cutoff và PD12 labels vẫn null; maturity và application-feature timing vẫn chưa qualified.

Browser receipt `artifacts/private/lendingclub-full-source-qa-2ac428dd27c2/receipt.json`: 4 groups PASS, gồm distinct date maxima, payment-span counts, cutoff/label unavailable, accepted/rejected applicability, source/filter/export parity, URL reload, mobile và outage recovery. Không browser errors; holdout ledger không đổi. Desktop temporal screenshot đã xem trực tiếp.

## 6. Đầu vào cần bổ sung để đóng gate

1. Observation cutoff có nguồn/version và bằng chứng availability.
2. First-event, exit/censoring history cho target và horizon cụ thể.
3. Feature values tại application/decision time và borrower identity phù hợp.
4. Mature support, entity-safe temporal protocol được chốt trước final access và intended-use review.

Không nâng C1/P1.02 hoặc trạng thái 50 capability từ temporal census này. Các output mô tả hiện có được lưu riêng để hỗ trợ review và thiết kế data intake.
