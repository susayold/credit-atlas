# Ginnie Mae loan-level performance — khả năng bổ sung dữ liệu

Cập nhật nguồn chính thức: 16/10/2026. Đây là review nguồn cho một case
mortgage/Ginnie riêng; chưa tải dữ liệu loan-level và chưa xác nhận Terms of Use.
Không gộp hồ sơ Ginnie với NSMO, Freddie Mac hoặc Fannie Mae.

## Kết luận nguồn

Ginnie Mae công bố bộ loan-level mortgage disclosure qua [Disclosure Data
Download](https://bulk.ginniemae.gov/). Danh sách production khi rà soát cho thấy:

| Tệp | Kỳ / lần đăng mới nhất thấy trên catalog | Quy mô tệp | Dùng để |
|---|---|---:|---|
| `LoanPerf_202606.zip` | Quarterly, đến 2026-06; đăng 16/07/2026 | 782,688,297 bytes | Active single-family loan performance, tối đa 3 monthly records mỗi loan trong quarterly file |
| `LoanPerfAnn_202512.zip` | Annual, đến 2025-12; đăng 20/01/2026 | 2,302,624,988 bytes | File annual lớn; chưa ưu tiên cho pilot |
| `llmon_202609.zip` | Monthly portfolio, đến 2026-09; đăng 07/10/2026 | 435,389,415 bytes | Tệp loan-level active portfolio tháng mới nhất trong catalog |
| `llmonliq_202609.zip` | Liquidations monthly, đến 2026-09; đăng 08/10/2026 | 1,917,130 bytes | Bằng chứng khoản vay rời active portfolio/liquidation; cần đối chiếu layout trước khi dùng làm competing exit |
| `llpaymhist_202608.zip` | Payment history, đến 2026-08; đăng 15/09/2026 | 67,187,930 bytes | Payment history riêng; có thể giúp phân tích kỳ trả, nhưng không thay định nghĩa status chính |
| `llmonforb_202609.zip` | Forbearance monthly, đến 2026-09; đăng 13/10/2026 | 1,245,711 bytes | Supplement chỉ có khoản vay được issuer báo có forbearance |

[Loan Performance File layout](https://bulk.ginniemae.gov/LayoutsSamples/471/LoanPerf_layout.pdf)
mô tả record `LP` là một loan-period cho mỗi loan đang active, tối đa ba kỳ
trong quarterly file. Field “Months Delinquent” ghi các mức 1–6, trong đó `6`
nghĩa là 6+ scheduled installments chưa trả; cách mã hóa current/blank phải
được xác nhận từ sample/layout đầy đủ trước khi parser gán trạng thái. Tệp có header/trailer record;
trailer ghi loan-record count, nên parser cần reconcile số record thực với
header/trailer và phân biệt từng kỳ tháng.

## Fit với mục tiêu credit-risk

Nguồn này có thể hỗ trợ một case chuyên về credit performance khoản vay được
Ginnie Mae securitize: trạng thái delinquency theo tháng, severity bands, cohort
pool/issuance, exposure/UPB, và đối chiếu khoản vay còn active với tệp
liquidation. Nếu định nghĩa event là `Months Delinquent >= 3`, đây là proxy
90+ theo kỳ báo cáo; vẫn cần xác minh cách Ginnie ghi nhận cure, reporting gap,
liquidation và loan removal từ layout/FAQ trước khi tạo outcome. File LoanPerf
chỉ bao gồm active single-family loans; nó không tự cho denominator của các
loan đã rời pool và không đại diện toàn bộ thị trường mortgage Hoa Kỳ.

Đây không phải cách để tăng sample NSMO: NSMO là survey-linked sample có trọng
số và 2013–2024 origination; Ginnie files là disclosure population của Ginnie
MBS, có grain/coverage khác, reporting theo kỳ và purpose giới hạn. Không join
qua borrower/loan identity, không tạo một target train chung, và không dùng
aggregate NMDB/FHFA để bù loan-level labels.

## Terms gate và trạng thái hiện tại

[Ginnie Mae Single-Family Loan-Level Terms of Use](https://tst.ginniemae.gov/investors/disclosures_and_reports/Pages/Single-Family-Loan-Level-Terms-of-Use.aspx)
nêu dữ liệu chỉ nhằm phân tích credit performance của Ginnie Mae mortgage
assets; cấm nhận diện cá nhân và cấm nối với nguồn khác để tìm danh tính. Terms
cũng cảnh báo dữ liệu do issuers gửi, có thể thiếu/sai và Ginnie không bảo đảm
tính chính xác/đầy đủ. Mục đích case nghiên cứu Ginnie có vẻ khớp phạm vi sử dụng,
nhưng người dùng phải tự đọc và chấp nhận Terms trước khi tải dữ liệu.

**Trạng thái:** `TERMS_ACCEPTANCE_REQUIRED — NO LOAN-LEVEL PAYLOAD DOWNLOADED`.
Catalog/layout và metadata công khai đã được rà soát; chưa tải data sample,
quarterly ZIP hay các monthly supplement. Việc dữ liệu có thể truy cập HTTP mà
không đăng nhập không thay thế việc người dùng chấp nhận điều khoản.

## Kế hoạch sau khi người dùng xác nhận Terms

1. Tải trước một quarterly production package và các layout cần thiết vào vùng
   private trên `D:`; lưu URL, thời điểm, byte count, SHA-256 và response headers.
2. Kiểm tra ZIP member/record format, header/trailer, counts và trường period;
   chưa đưa row-level files vào public Git hoặc Excel.
3. Xây parser fixed-width theo layout version, preserve raw codes/missing values,
   kiểm tra duplicate loan-periods, phạm vi delinquency, UPB và chronology.
4. Chỉ sau khi layout/liquidation concordance qua audit mới tạo aggregate
   dashboard riêng: current/1–2/3+/6+, vintage, pool characteristics, active
   exits và forbearance coverage.
5. Hash-bind receipts và acceptance tests; không xuất loan IDs, nối sang nguồn
   khác để suy danh tính, hay gọi tỷ lệ mô tả là PD đại diện dân số.

## Nguồn chính thức

- [Ginnie Mae Disclosure Data Download](https://bulk.ginniemae.gov/)
- [Loan Performance File layout — v1.0, 01/05/2023](https://bulk.ginniemae.gov/LayoutsSamples/471/LoanPerf_layout.pdf)
- [Monthly loan-level forbearance layout — v2.0, 01/06/2025](https://bulk.ginniemae.gov/LayoutsSamples/210/llmonforb_layout.pdf)
- [Single-Family Loan-Level Terms of Use](https://tst.ginniemae.gov/investors/disclosures_and_reports/Pages/Single-Family-Loan-Level-Terms-of-Use.aspx)
