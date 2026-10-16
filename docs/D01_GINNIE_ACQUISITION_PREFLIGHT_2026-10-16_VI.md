# D01 — Ginnie Mae production-download preflight (2026-10-16)

## Kết quả kiểm tra hiện tại

Đã đọc lại catalog chính thức của Ginnie Mae bằng HTTPS và đối chiếu với downloader trong repo. Tại thời điểm kiểm tra, `LoanPerf_202606.zip` vẫn là quarterly Loan Performance release mới nhất trong catalog: 782.688.297 bytes, ngày catalog ghi `07/16/2026 6:48 AM`. Đây là dữ liệu hiệu suất khoản vay nằm trong Ginnie Mae MBS disclosure universe; không đại diện toàn bộ mortgage Mỹ và không thay thế Freddie Mac D01.

Người dùng đã xác nhận đọc và chấp nhận Terms of Use. Tuy nhiên, file session Netscape trên D: chưa được tìm thấy tại thư mục access mặc định; không có credential nào được đọc, in hoặc ghi vào repo. Vì endpoint production yêu cầu xác thực, chưa tải ZIP sản xuất và không ghi nhận đây là dữ liệu đã có.

## Kiểm chứng đường chạy đã chuẩn bị

- Bộ kiểm thử của bounded downloader và structural auditor: **13/13 PASS** (`test_ginnie_acquisition.py`, `test_ginnie_performance.py`).
- Gọi trực tiếp catalog parser: tên file, kích thước và timestamp khớp với mục catalog đang công bố.
- Chạy auditor trên ZIP sample chính thức hiện có: 213 loan-period rows, 104 disclosure keys, kỳ 202304–202306; HH/LP/TT và schema 59-field đạt structural contract. Đây chỉ là kiểm thử định dạng trên sample, không phải production coverage, không phải 104 người vay độc lập và không hỗ trợ tỷ lệ default.
- Downloader yêu cầu file cookie Netscape trên D:, chỉ giữ secure/unexpired `gm_up_token` áp dụng cho domain tải chính thức, kiểm tra phiên qua profile endpoint, khóa redirect vào host HTTPS chính thức, giới hạn 1 GiB, đối chiếu bytes với catalog, kiểm ZIP/member và SHA-256, ghi receipt private; nó không ghi nội dung cookie hoặc xuất loan rows.

### Recheck catalog endpoint and downloader auth flow — 2026-10-16 (later same day)

- Public metadata API `https://www.ginniemae.gov/bulk-content/api/disclosure-data` returned HTTP 200 JSON. Current catalog still lists quarterly `LoanPerf_202606.zip` (782.688.297 bytes); annual `LoanPerfAnn_202512.zip` (2.302.624.988 bytes); and payment history `llpaymhist_202609.zip` (67.497.851 bytes, catalog modified 15/10/2026).
- Production request to the official `/disclosure-api/api/download?dlfile=data_bulk/LoanPerf_202606.zip` returned HTTP 401 without an authenticated token. A guessed static path returns HTML, not the ZIP. No bypass was attempted.
- Inspection of the official portal's published JavaScript shows its interceptor copies cookie `gm_up_token` to `Authorization: Bearer …` for both the profile and download APIs. The Python downloader previously forwarded the cookie but omitted that header; it now mirrors the official request flow, keeps the token in memory only, restricts the destination host, and still omits it from receipts/logs. Synthetic-token tests verify both Authorization headers and the credential-free receipt: **7/7 tests pass**.

### Fresh access recheck — 2026-10-16

- D: access folders đã được kiểm tra lại; hiện chưa có cookie file do user lưu.
- Freddie Clarity unauthenticated probe mới nhất trả **HTTP 403 / `AUTHENTICATION_REQUIRED`**, không tải data. Credential/cookie không được cung cấp trong probe; receipt private: `D:\data\Codex\credit-atlas\artifacts\private\source-access-2b88beade3dc.json`.
- Ginnie downloader + structural-auditor tests được chạy lại với pytest temp đặt trên D:: **13/13 PASS**. Một lượt thử đầu dùng pytest temp mặc định trên C: và bị `PermissionError`; chạy lại bằng `--basetemp` trên D: đã pass.
- Ginnie official catalog page vẫn là source of truth cho byte size/release; không tải production ZIP khi thiếu authenticated session.

Khi cookie Netscape đã được lưu, đặt một bản private ở, ví dụ,
`D:\data\Codex\credit-atlas\data\private\access\ginnie.cookies.txt`, rồi
chạy từ public checkout:

```powershell
python scripts/download_ginnie_loanperf.py --root D:\data\Codex\credit-atlas --cookie-file D:\data\Codex\credit-atlas\data\private\access\ginnie.cookies.txt --terms-accepted-by-user
```

Không gửi nội dung cookie qua chat. Chỉ cần báo đường dẫn file nếu tên/vị trí
khác ví dụ trên. Downloader kiểm tra phiên trước khi tải; nếu hết hạn hoặc sai
scope, nó dừng trước khi lấy production ZIP.

## Gate trước khi phân tích

Khi nhận được đường dẫn cookie trên D:, chạy `scripts/download_ginnie_loanperf.py` với `--terms-accepted-by-user`, sau đó chạy `scripts/audit_ginnie_loanperf.py` trên ZIP private cũng với xác nhận này. Chỉ sau khi receipt, hash, ZIP integrity, HH/LP/TT counts, key-period uniqueness, date range, code domains và blankness qua kiểm tra mới cập nhật coverage. Không tạo nhãn PD hoặc projection từ file này cho đến khi source-specific target, exit/censoring và follow-up được nghiên cứu, kiểm chứng.

## Ảnh hưởng tới D01

Production data mới tải được trong lượt này: **không có**. Freddie Mac vẫn là critical path cho D01: trang chính thức xác nhận SFLLD có khoảng 56 triệu mortgage, performance đến 2026-03-31, nhưng annual files chỉ tải sau khi đăng ký/đăng nhập Clarity. Ginnie production nếu tải thành công sẽ mở một case song song riêng và vẫn không làm tăng số Freddie vintages hay mở model gate R2/R3.

Nguồn: [Ginnie Mae Disclosure Data Download](https://bulk.ginniemae.gov/), [Ginnie Mae loan-level Terms of Use](https://tst.ginniemae.gov/investors/disclosures_and_reports/Pages/Single-Family-Loan-Level-Terms-of-Use.aspx), [Freddie Mac SFLLD](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset).
