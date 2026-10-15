# Kiểm tra nguồn thay thế cho mortgage-performance data — 15/10/2026

Mục tiêu kiểm tra: có annual loan-level performance source nào có thể bổ sung D01 mà không dùng một tài khoản/điều khoản truy cập chưa được chủ sở hữu project cấp hay không. Kiểm tra dựa trên trang/tài liệu chính thức; không tự tạo tài khoản, không chấp nhận điều khoản thay người dùng và không thử vượt access controls.

| Nguồn | Nội dung và grain | Trạng thái access công bố | Quyết định cho D01 |
|---|---|---|---|
| Freddie Mac SFLLD | Khoảng 56 triệu mortgage, origination 1999 đến 31/03/2026; monthly performance đến cùng mốc, gồm prepay, foreclosure alternatives, REO và actual-loss components | Freddie yêu cầu register/sign in Clarity để tải full, annual-by-year, non-standard và sample files. Dữ liệu unaudited; commercial redistribution cần licensing agreement | Vẫn là nguồn chính, nhưng chưa có session/điều khoản được user thiết lập; không download annual ZIP mới |
| Fannie Mae Single-Family Loan Performance | Primary fixed-rate subset và HARP subset; release 31/07/2026 gồm acquisition/performance đến Q1 2026 | Data Dynamics yêu cầu account/registration và xác nhận email; điều khoản cấm redistribution và external commercial use nếu chưa có express written consent. Trang nhắc APIs nhưng cũng yêu cầu đăng ký để truy cập performance data | Có thể dùng làm external validation sau khi có authorized access; không thay thế hoặc ghép vào Freddie run hiện tại |
| Fannie Mae Multifamily Loan Performance | Gần 74.000 loans, acquired 2000 đến 30/06/2026; loan × reporting month, có annual historical DSCR file | Dataset/dashboard qua Data Dynamics; registration/terms áp dụng. Sample files chỉ để dựng database/schema | Nguồn tiềm năng cho P2 CRE/D09; không phải residential D01, chưa thể lấy full data khi thiếu authorized session |
| FHFA/CFPB NSMO Public Use File | 62.359 sample mortgages originated 2013–2024; quarterly credit score/performance through Q3 2025; survey + mortgage/borrower supplemental fields | Public-use formats listed by FHFA; download/use requires acknowledging FHFA Notice of Monitoring and Terms. This acknowledgement has not been made | Strong separate external-cohort candidate; not equivalent to Freddie monthly panel, cannot be pooled or counted as a Freddie vintage. Codebook reviewed; payload awaits user authorization to accept the FHFA gate |
| HMDA national LAR | Loan/application records được sửa đổi nhằm bảo vệ privacy; application/origination decisions, product, applicant/property và lender dimensions | Dataset/API công khai | Phù hợp origination-market analysis riêng. Không có monthly post-booking payment/performance path, nên không tạo delinquency/vintage outcomes cho D01 |

## Kết luận acquisition

NSMO là microdata public-use hiếm có chứa mortgage performance ngoài GSE annual files, nhưng quan sát theo quý, sample/response process và state definitions khác; vì vậy là **candidate cho một case riêng**, không thay Freddie và không làm đủ R2/R3 theo plan hiện tại. Chưa tìm được nguồn thay thế có cùng grain monthly và cùng contract với Freddie. Ghép HMDA origination vào mortgage performance sẽ tạo linkage không có khóa chung/permission và gộp hai estimand khác nhau thành panel giả; không thực hiện. Sample files/layouts và aggregate statistical summaries hỗ trợ parser/reconciliation nhưng không tính là Freddie annual vintage.

**Trạng thái:** annual Freddie vintages bổ sung = 0; Fannie external loan panel = 0; không có data access credentials/session do user cung cấp. Code acquisition/registration sẵn sàng chạy sau authorized access. R2/R3 chờ input; R0/R1/R4 descriptive tiếp tục.

## Official references

- [Freddie Mac Single-Family Loan-Level Dataset](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
- [Fannie Mae Single-Family Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data)
- [Fannie Mae Data Dynamics access and FAQ](https://capitalmarkets.fanniemae.com/tools-applications/data-dynamics)
- [Fannie Mae Multifamily Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/multifamily-loan-performance-data)
- [FHFA/CFPB NSMO Public Use File](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included)
- [ICPSR/DataLumos NSMO V2 catalog record](https://www.datalumos.org/datalumos/project/219485/version/V2/view)
- [FFIEC/CFPB Dynamic National Loan-Level HMDA Dataset](https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset)
