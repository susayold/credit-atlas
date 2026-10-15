# D01 — Cách đọc denominator trong transition matrix

**Ngày:** 15/10/2026. Scope là 2012 origination sample trong frozen case `d01-a24484b21a21`; 4.510.559 loan-month observations tạo **4.460.559 adjacent observed month-pairs**. Independent acceptance dựng lại bằng destination-side LAG trên panel đầy đủ và đối soát 1.091 year/segment cells cùng 94 lifetime/segment cells. [P2.05 acceptance](P2_TRANSITION_ACCEPTANCE_VI.md), [independent receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).

## Một transition row là gì?

Mỗi pair là một khoản vay từ tháng t sang tháng quan sát kế tiếp t+1. Chỉ ghép đúng hai calendar months liền nhau; gaps không được nối tắt, terminal origin không được đưa vào risk set như trạng thái active. Kỳ/năm được gán theo **opening month t**; do đó 12/2020→01/2021 thuộc reporting year 2020.

Count weight ở một origin/segment/year là `destination pairs ÷ all admitted pairs từ origin đó`. Balance weight là `tổng known opening UPB ở destination ÷ tổng known opening UPB của origin`; dùng dư nợ tại tháng bắt đầu, không phải ending balance. Missing starting UPB được báo riêng và không được đổi thành zero. Không có denominator count hoặc known-UPB hợp lệ thì metric giữ unavailable. Distinct-loan support là số khoản khác nhau tại cell; pair rows lặp cùng loan qua tháng, nên support không cộng được qua các destination hoặc years và không phải cỡ mẫu độc lập.

## Ví dụ ở lifetime, toàn segment

| Origin tháng t | Destination tháng t+1 | Pair rows / origin-pair denominator | Count share | Opening UPB destination / origin | Balance share |
|---|---|---:|---:|---:|---:|
| Current | Current | 4.363.335 / 4.415.313 | 98,823% | $710,099bn / $718,180bn | 98,875% |
| Current | D1 | 12.474 / 4.415.313 | 0,283% | $1,981bn / $718,180bn | 0,276% |
| Current | D2 | 69 / 4.415.313 | 0,00156% | $12,847m / $718,180bn | 0,00179% |
| Current | D3+ | 31 / 4.415.313 | 0,000702% | $5,367m / $718,180bn | 0,000747% |
| D2 | D3+ | 2.316 / 5.409 | 42,818% | $389,674m / $878,142m | 44,375% |
| D3+ | D3+ | 15.319 / 17.668 | 86,705% | $2,669bn / $3,064bn | 87,100% |

Các tỷ lệ này là empirical shares của adjacent pairs trong sample được quan sát. Ví dụ **31 Current→D3+ pairs** không có nghĩa 31 khoản vay mới default trong một tháng, và 0,000702% không phải origination PD hoặc fixed-horizon monthly PD: một khoản có thể đóng góp nhiều Current-origin pairs trong suốt lịch sử. D2→D3+ là phần destination pair trong 5.409 D2-origin pairs; cũng không được diễn giải thành xác suất người vay D2 chuyển D3 độc lập nếu chưa xử lý repeated-loan dependence, cohort selection và censoring.

## Reconciliation và sản phẩm

Independent audit tái dựng toàn bộ pair rows từ source, kiểm numerator, origin denominator, known opening-UPB sum, missing balance pairs, distinct loans và sparse-cell flags; sai khác xác suất lớn nhất khoảng `2.22e-16`, dưới tolerance `1e-12`. Filter year được áp sau khi xác định adjacency; transition-year và monthly chart date ranges không trộn nhau. Export giữ segment/year context và whole-period lifetime comparator riêng.

App hiển thị count/balance basis, numerator/denominator và support khi người dùng chọn cell. Gaps/terminal axis, absent reporting year, sparse support và lifetime comparator giữ trạng thái riêng. Kết quả này hoàn thiện phần denominator interpretation của M01-011 trên sample 2012; composition qua nhiều origination vintages và temporal transition model vẫn mở.
