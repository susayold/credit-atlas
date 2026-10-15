# D01 — Event rows, unique loans và mẫu số follow-up

**Ngày:** 15/10/2026. Scope là episode ledger của frozen Freddie Mac origination sample 2012. Audit độc lập hash-check `episodes.parquet`, canonical `dim_loan`, snapshot và projection follow-up; không xuất raw loan ID. [Audit JSON](../artifacts/private/d01-episode-denominators-a3a3093f04b8/audit.json), [receipt](../artifacts/private/d01-episode-denominators-a3a3093f04b8/receipt.json). Tạo lại bằng `scripts/audit_d01_episode_denominators.py`.

## Hạt dữ liệu và số đếm

Có **4.902 confirmed event occurrences** thuộc **1.713 khoản vay có ít nhất một event**. Một khoản có thể có nhiều lần cure/redefault. Vì vậy `event rows`, `distinct loans theo event type`, và `distinct loans toàn cohort` là ba số khác nhau.

| Loại event | Event occurrences | Distinct loans | Event lặp ngoài occurrence đầu | Nhiều event nhất trên một khoản |
|---|---:|---:|---:|---:|
| First observed D3 | 1.713 | 1.713 | 0 | 1 |
| One-month cure | 1.694 | 1.152 | 542 | 11 |
| Sustained cure confirmed | 1.224 | 1.053 | 171 | 5 |
| Redefault after sustained cure | 271 | 216 | 55 | 5 |

Tổng các unique-loan counts theo event type là 4.134 nhưng không phải 4.134 khoản vay: một khoản có thể xuất hiện trong nhiều loại event. Tổng đó cũng không thể dùng làm denominator cho tỷ lệ. Ở app, bảng “Forward-only episode events” giờ hiển thị đúng unique-loan support ở `Toàn sample` bằng cách cộng hai segment Relief/non-Relief loại trừ lẫn nhau; các dòng lặp vẫn được giữ là event occurrences.

## Follow-up support denominator

Với mỗi event type, segment và horizon 6/12 tháng, mẫu số follow-up là **tất cả event occurrences đã confirmed** thuộc đúng event type/segment. Mỗi event occurrence được xếp đúng một trạng thái support (complete contiguous nonterminal follow-up, source end, terminal exit hoặc terminal at confirmation). Độc lập kiểm tra **24/24** tổng status event rows khớp lại mẫu số event type/segment/horizon.

Distinct loans của các status rows không cộng được thành số khoản vay unique: một khoản có repeated event và các event của nó có thể rơi vào nhiều support status. Ví dụ ở Toàn sample, One-month cure có 1.694 event occurrences/1.152 unique loans; khi chia status theo horizon 6 tháng, tổng `distinct_loans` trên các status rows là 1.201, còn horizon 12 là 1.240. Đây là support count theo từng status, không phải số loan mới và không phải xác suất.

## Không diễn giải thành cure/redefault rate

Audit chỉ xác nhận định nghĩa grain và denominator cho descriptive event/support tables. Nó **không** tạo cure rate, redefault rate, survival probability, treatment uplift hoặc borrower-level probability. Muốn estimate các đại lượng này phải dựng spell-level risk set, eligibility/landmark, event-before-competing-exit, censoring/maturity và loan-cluster uncertainty riêng rồi kiểm tra trên nhiều origination vintages. Đủ tháng quan sát sau confirmation chỉ có nghĩa follow-up status có support; nó không nói rằng loan không redefault.

## App và regression

UI ghi rõ event rows là occurrences, distinct loans là support và không cộng ngang event types. Bảng follow-up nói rõ status rows phân hoạch event occurrences, còn unique-loan support có thể lặp giữa statuses. Browser regression kiểm tra 1.713 khoản Toàn sample, 1.094 Relief, 619 non-Relief, cùng disclosure về denominator; [browser receipt](../artifacts/private/browser-qa-f35adbcaeddf/receipt.json) ghi **25 checks PASS**.
