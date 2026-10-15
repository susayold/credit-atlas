# LendingClub — accepted và rejected publisher snapshot

Ngày 12/10/2026. Đây là nguồn bổ sung cho P1.02 và nghiên cứu temporal cohorts, khác bản Mendeley chỉ chứa khoản vay đã kết thúc. Chưa chứng minh application-time features hoặc fixed-horizon target.

## 1. Acquisition

Trang download cũ của issuer trả HTTP 403. Không dùng login, cookies hoặc chạy scraping code của uploader. API công khai của Kaggle trả metadata, inventory và hai GZIP files thuộc `wordsforthewise/lending-club`, version 3.

| File | Compressed bytes | Uncompressed bytes |
|---|---:|---:|
| accepted_2007_to_2018Q4.csv.gz |392,582,231|1,675,133,810|
| rejected_2007_to_2018Q4.csv.gz |255,470,782|1,782,281,620|

Các file được stream xuống D:, có SHA-256 riêng và size khớp publisher inventory. GZIP magic, full decompression CRC/trailer và uncompressed sizes đã kiểm tra khi profiling. Không tạo bản CSV giải nén toàn bộ trên đĩa.

Source folder: `data/private/retail/lendingclub-full-source-3954d375d972`.

Acquisition receipt SHA-256: `8c75b6f45be94ccc7e610f3be8aa1f51246b48bc69331dea8db518c69f657d55`.

Publisher metadata ghi CC0, nhưng uploader description nêu vấn đề TOS của issuer và việc FICO data gốc cần signed-in download. Vì vậy không suy ra issuer/bureau redistribution rights đã được kiểm chứng. Nguồn giữ private, original issuer fidelity và public-release approval vẫn false.

## 2. Coverage của census đầu

| Phạm vi | Accepted file | Rejected file |
|---|---:|---:|
| Raw source records |2,260,701|27,648,741|
| Columns |151|9|
| Date field |issue_d|Application Date|
| Source grain |Funded month|Application day|
| Date range có giá trị |2007-06 đến 2018-12|2007-05 đến 2018-12|
| Populated month/category cells |630|200|

Tổng 590,204,520 vị trí dữ liệu. Accepted có 33 records thiếu loan_amnt, issue_d và loan_status; các records này giữ riêng trong quality counts, không tự biến thành loans hoặc default events. Rejected không có repayment outcome.

Accepted source statuses được giữ nguyên:

| Raw status | Records |
|---|---:|
| Fully Paid |1,076,751|
| Current |878,317|
| Charged Off |268,559|
| In Grace Period |8,436|
| Late (31-120 days) |21,467|
| Late (16-30 days) |4,349|
| Default |40|
| Does not meet the credit policy. Status:Fully Paid |1,988|
| Does not meet the credit policy. Status:Charged Off |761|
| Missing |33|

Không tự gộp Default, Charged Off và Late thành cùng target. Legacy policy statuses có population khác cần đọc protocol trước khi gộp.

## 3. Những giới hạn đã xác định

- `member_id` thiếu ở toàn bộ 2,260,701 accepted records. Loan ID có giá trị không chứng minh borrower identity hoặc shared-borrower grouping.
- Rejected `Risk_Score` thiếu ở 18,497,630 records. Không impute score thành zero hoặc giả định cùng scale với accepted FICO ranges.
- Accepted last_pymnt_d thiếu 2,460 records; last_credit_pull_d thiếu 105. Các trường này không tự là default event date hoặc observation cutoff chung.
- Funded month và rejected application day là hai grain khác nhau. Funded/rejected counts chưa xác định denominator của approval rate, vì còn approved-but-unfunded, repeated applications, source eligibility và snapshot coverage.
- Có active/late statuses giúp nghiên cứu selection/maturity tốt hơn bản terminal-only, nhưng current-status snapshot chưa là PD12 target. Không gán default labels cho rejected applications.

## 4. Preprocessing provenance

Dataset description dẫn tới repo `nateGeorge/preprocess_lending_club_data`. Đã acquire README, concat_data.py, scrape_data.py và commit metadata tại `data/private/retail/lendingclub-preprocessing-source-9a051fd43a9e`, pin commit `a1c4927fee20979dc5f7a3bb3d70742bb977d723`. Không chạy code đã tải.

Source code mô tả đọc quarterly CSV, bỏ dòng banner qua header selection, concat và xuất gzip; bỏ ký hiệu % của int_rate/revol_util rồi chuyển float. Code và description chưa chứng minh version này tái tạo chính xác mọi downloaded file hoặc giải thích transformations của bản Mendeley. Giữ separate provenance cho hai publisher snapshots.

## 5. Profile và kiểm tra

Bounded Arrow/GZIP profile: `artifacts/private/lendingclub-full-profile-f4168e8d746c/profile.json`.

SHA-256: `f8be3a2f137172f019d4cce743c173c03176f1fb5d3e3b54e67350ee34f60098`.

Profile chứa whole-source missingness, month/category counts, raw source statuses, missing-date records và gzip integrity evidence. Không fit/rescore model, không impute và không edit source. Frozen holdout ledger không đổi.

Independent DuckDB census đã PASS: `artifacts/private/lendingclub-full-audit-13dc84314050/receipt.json`. Kiểm tra rows, 160 column missingness counts, 830 month/category cells, category totals và missing-date records. Memory limit 512 MB, temp storage trên D:, frozen holdout ledger không đổi. Kiểm tra SQL null conversions để không làm mất raw blank/NA distinctions. Đây là parser/census verification, chưa là target, original fidelity hoặc rights certification.

## 6. Phần tiếp theo

Bổ sung API/UI phân biệt funded/rejected grains và missing categories; review source dictionary, field availability, snapshot cutoff, borrower grouping, event target và maturity. Independent census đã đóng trong scope nêu trên. Không nâng P1.02/C1 hoặc trạng thái 50 capability chỉ từ số lượng dữ liệu mới.

## 7. API/UI checkpoint

Retail → Accepted & rejected đã có source explorer riêng. `/api/lendingclub-full-source` và `/api/lendingclub-full-source-report` nhận kind, from/to month và category. Server kiểm tra acquisition, compressed source và profile hashes trước mỗi report. Filters không hợp lệ bị từ chối; API/export giữ private/no-store.

Màn hình hiển thị grain/date/category fields, raw whole-source records, selected dated records, all-category window records, whole-source missing dates/category, category counts, timeline và missingness của 151 hoặc 9 cột. Accepted thiếu ngày không được tự phân bổ vào tháng. Rejected giữ Policy Code như source category, không biến thành trạng thái repayment. Category reset về all khi chuyển kind; URL reload giữ nguồn và bộ lọc.

Approval rate và fixed-horizon PD luôn unavailable. Không impute repayment labels cho rejected data. Profile quality counts là whole-source, không được giả như chất lượng cohort đã lọc.

Backend/HTTP: `artifacts/private/lendingclub-full-http-tests-20261012.xml`, 30 tests PASS. Browser: `artifacts/private/lendingclub-full-source-qa-58d41056f7e3/receipt.json`, 4 groups PASS về source/API/export parity, Current/missing scopes, rejected grain/score missingness, kind/category/URL reset, mobile và outage/recovery. Không browser errors, frozen holdout ledger unchanged. Desktop/mobile summary screenshots đã xem trực tiếp.

Bước API/UI ở mục6 đã được bổ sung trong scope này; các target/time/fidelity/rights và intended-use gates vẫn mở.

Prepared-source/dictionary regression: `artifacts/private/lendingclub-source-qa-4f4d7e5c9504/receipt.json`, 4 groups PASS sau khi thêm tab mới. Source filters/export, dictionary aliases/undefined outcomes, mobile và outage recovery giữ nguyên; holdout ledger không đổi.
