# Freddie Mac SFLLD 2012 — nguồn, receipt và giới hạn sử dụng

**Ngày rà soát:** 17/10/2026 · **Mục tiêu:** xác định chính xác dữ liệu Freddie 2012 đang phục vụ D01, phân biệt bằng chứng local với xác nhận của publisher, và đặt điều kiện trước khi tải thêm vintage.

## Kết luận

Đã bind được file Freddie 2012 đang chạy D01 với local source-use receipt và exact archive hash. Đây là bước cải thiện lineage; nó **không** chứng minh file đã được Freddie Mac phát hành đúng như receipt khai báo, không xác nhận terms của chính file, và không biến một vintage thành model multi-vintage.

Source register ghi object là **user-supplied, private, receipt-bound; Release 47 unauthenticated**. App chỉ dùng cohort cho descriptive monitoring/transitions. Không public raw data, không train model từ thay đổi của lượt này và không tăng capability completion.

## Bằng chứng từ archive và receipt local

Private receipt khai báo:

| Thuộc tính | Giá trị đã kiểm |
|---|---|
| Tên ban đầu trong receipt | `sample_2012.zip` |
| Release / data kind khai báo | Release 47 / annual_sample |
| Release authentication | Receipt ghi: user-supplied; không xác thực bởi file hash registry |
| Local received-at | 2026-09-09 20:02:22 UTC; đây không phải timestamp download |
| Archive | 70,532,871 bytes; SHA-256 prefix `35c415821578` (full hash chỉ nằm trong private workspace) |
| Origination member | `sample_orig_2012.txt`, 50,000 records / 50,000 loan IDs |
| Performance member | `sample_perf_2012.txt`, 4,510,559 loan-month rows / 50,000 loan IDs |
| Observed performance | 2012-01 đến 2026-03 theo D01 source audit |
| Visibility / approval | Private; public release approval = false |
| Model status | Không model fit; 2012 case chỉ descriptive |

Archive hash được băm lại trên D: và khớp local receipt. Receipt lineage của case D01 khớp hash; full ZIP read đã kiểm CRC/member counts. Các kết quả này xác nhận **file local và quy trình nội bộ**, không xác thực nguồn phát hành. Source URL gốc, publication date, archive-specific performance cutoff evidence và bằng chứng terms/click-through áp dụng cho file chưa được lưu. Do đó register để `retrieved_at_utc=null` và lưu riêng `receipt_received_at_utc`.

## Đối chiếu tài liệu Freddie Mac hiện hành

Freddie Mac cho biết muốn lấy SFLLD cần đăng ký/đăng nhập Clarity; Standard sample có 50,000 loans cho mỗi full vintage, và monthly performance được cập nhật đến performance cutoff. Trang hiện hành nói dữ liệu qua 2026-03-31, non-commercial/academic research được cung cấp miễn phí nhưng tùy terms áp dụng, còn commercial redistribution cần licensing agreement. [Trang chính thức SFLLD](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset) · [General User Guide](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf) · [Terms and Conditions](https://www.freddiemac.com/terms).

Các thông tin trên phù hợp với 50,000-loan cohort và kỳ quan sát local đến 2026-03, nhưng **không** chứng minh ZIP local được tải từ Freddie, thuộc Release 47, hoặc tuân thủ terms nào. Hướng dẫn hiện hành liệt kê member sample performance theo mẫu tên `sample_svcg_YYYY.txt`, còn archive local có `sample_perf_2012.txt`; khác biệt tên file có thể do thay đổi phiên bản nhưng chưa được publisher giải thích, nên không dùng nó để xác thực hoặc bác bỏ archive. Hướng dẫn về 50,000-loan random sample mô tả product design; nó không thay thế receipt, provenance URL hay publisher hash cho file cụ thể.

Release 47 public sample ZIP và file-layout reference đã audit riêng trước đó: đó là ví dụ định dạng nhỏ (1,000 origination IDs và 12 performance IDs, không overlap), không phải annual performance vintage bổ sung và không thể dùng để “xác thực” archive 2012. [Freddie Mac Release 47 sample announcement](https://capitalmarkets.freddiemac.com/clarity/whats-new/december-2025-clarity-updates).

Freddie Mac terms nói quyền truy cập/download tùy terms của dataset; terms chung hạn chế redistribution/commercial use khi không có license bằng văn bản và cấm automated access trừ khi được cho phép. Vì vậy các annual files tiếp theo chỉ lấy qua Clarity/publisher-authorized workflow; không dùng scraper, không chia sẻ session/cookie và không đưa raw data vào public GitHub.

## Ý nghĩa đối với D01 và model

D01 có một origination vintage 2012 với lịch sử loan-month dài. Độ dài quan sát của cohort không tạo thêm vintage: phân chia train/test theo loan vẫn có thể đặt các khoản vay cùng vintage/regime ở hai phía và không thay thế out-of-time validation trên nhiều origination vintages.

Các D01 KPI hiện được giữ ở phạm vi mô tả stock, delinquency state, transition/cure và count/UPB. Release 47 declared label hoặc local schema alignment không tự xác lập event target, availability-at-origination, source representativeness hay final-holdout integrity. R2 multi-vintage và R3 modeling tiếp tục mở cho đến khi có annual samples hợp lệ, compatibility/maturity audit và protocol thời gian đã khóa.

## Điều kiện cho bước tải dữ liệu kế tiếp

1. Đăng nhập Clarity bằng tài khoản được phép và tự xem/hoàn tất dataset-specific terms; không đưa credentials/cookies vào repo hoặc chat.
2. Tải đúng **một** annual sample qua giao diện hoặc API mà publisher cho phép, lưu raw vào private D: và lập receipt có URL/redirect, retrieved-at, release label, performance cutoff, member names, sizes, SHA-256 và terms/acknowledgement status.
3. So khớp layout/version, loan key, 50,000/sample design khi applicable, origination/performance IDs, loan-month grain, status/event semantics, maturity, missingness, resource size và observed cutoff; ghi bất kỳ field drift nào trước khi batch.
4. Chạy D01 descriptive side-by-side và test outcome/feature availability; nếu source/terms/label không đủ, dừng ở descriptive. Không forecast hoặc fill dữ liệu thiếu.

**Trạng thái sau lượt này:** Freddie local object-to-receipt binding đã có; publisher authentication, original acquisition route, exact release/cutoff proof, dataset terms, thêm vintage và R2/R3 qualification vẫn mở. Capability ledger giữ nguyên 26/50.
