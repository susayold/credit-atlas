# Ginnie Mae loan-level performance — đánh giá nguồn bổ sung

Ngày rà soát: 15–16/10/2026. Đây là một nguồn mortgage loan-level riêng, có tiềm năng cho một case MBS-credit độc lập. Nguồn này **không thay thế Freddie**, không được gộp vào case D01 hiện tại. Người dùng đã xác nhận chấp nhận Terms of Use; layout/sample công khai đã được tải, còn production loan-level payload vẫn chờ phiên đăng nhập.

## Nguồn có gì

Trang Disclosure Data Download của Ginnie Mae công bố các file daily, monthly, quarterly và annual. Snapshot catalog tại lần rà soát 16/10/2026 liệt kê:

| File | Kỳ gần nhất trong catalog | Quy mô nén được liệt kê | Grain / ý nghĩa |
|---|---:|---:|---|
| `LoanPerf_202606.zip` | 2026Q2 | 782,688,297 bytes | Loan-performance record theo kỳ, tối đa 3 kỳ/loan trong file quarterly |
| `LoanPerfAnn_202512.zip` | năm 2025 | 2,302,624,988 bytes | Loan-performance record theo kỳ, tối đa 12 kỳ/loan trong file annual |
| `llmon_202609.zip` | 2026-09 | 435,389,415 bytes | Monthly portfolio disclosure cho các loan đang active trong MBS Ginnie Mae |
| `llmonliq_202609.zip` | 2026-09 | 1,917,130 bytes | Loan-level monthly liquidation/payoff disclosures |
| `llmonforb_202609.zip` | 2026-09 | 1,245,711 bytes | Loan-level forbearance supplement; schema riêng |
| `llpaymhist_202609.zip` | 2026-09 | 67,497,851 bytes | Monthly payment-history file cho loan active; tối đa 24 trạng thái delinquency |

Các file đầu là disclosure về tài sản MBS Ginnie Mae, không phải toàn bộ mortgage origination của Mỹ. Loan performance quarterly/annual có record header `HH`, performance `LP`, và trailer `TT`, dùng pipe delimiter. Một LP record đại diện một khoản vay trong một reporting period; performance record có trường `As of Date`, origination date, loan age, current UPB và `Months Delinquent` mức 1–6 (6 nghĩa là 6 kỳ trả góp trở lên chưa trả). Ngoài state hiện tại, `LP-59` chứa tới 24 kỳ `Months Delinquent` history, hai ký tự/kỳ: `00` current, `01`–`99` delinquency count, `XX` không có dữ liệu; độ dài ngắn hơn 48 ký tự có thể là khoản vay chưa đủ 24 tháng lịch sử. Không suy thứ tự kỳ, coverage hoặc semantics missing chỉ từ chuỗi trước khi kiểm chứng với production file.

Các trường hồ sơ còn gồm original principal balance, term, LTV, total debt expense ratio (DTI proxy), credit score và loan purpose. `LP-39` là removal reason; mã 1–6 lần lượt gồm mortgagor payoff, repurchase of delinquent loan, foreclosure with claim payment, loss mitigation, substitution và other removal. Bộ active monthly loan-level có schema/version riêng. File liquidation có layout riêng và có coverage lịch sử được tài liệu mô tả từ 2009/2010 trở đi.

Vì vậy, nguồn có khả năng hỗ trợ descriptive lifecycle, delinquency state/history, competing exits, cohorting theo origination/loan age và một candidate model target cho chính population Ginnie Mae. Trước khi lập target phải kiểm tra dictionary/version của đúng file, độ trễ quan sát, cách loan rời panel, missing/suppressed values, và liệu annual/quarterly snapshots có đủ chuỗi lịch sử cho protocol dự định hay không. Không diễn giải `months delinquent=6` như số ngày DPD chính xác hoặc mặc định nó tương đương Freddie D3.

## Khác với Freddie và cách sử dụng trong CreditAtlas

| Khía cạnh | Freddie D01 hiện tại | Ginnie candidate |
|---|---|---|
| Population | Freddie Mac mortgage loan-level sample | Loan nằm trong Ginnie Mae MBS disclosure universe |
| Kỳ quan sát | Monthly loan history trong nguồn Freddie hiện có | File performance quarterly/annual và monthly active disclosure; cadence/selection khác nhau |
| Delinquency | Freddie state definitions/mapping đã được audit cho snapshot hiện có | Months delinquent 1–6+; mapping phải viết riêng và không suy thành cùng target |
| Exit | Freddie terminal / loss components đã được audit một phần | Ginnie removal reason và liquidation file; semantics/coverage phải audit riêng |
| Vai trò | Nguồn chính cho M01-005…021 | Parallel source case / external robustness sau khi được phép lấy và profile |

Không nối borrower/loan identities giữa Ginnie, Freddie, Fannie, HMDA, NSMO hay nguồn bên ngoài khác. Có thể so sánh aggregate/methodology nếu denominator, cadence, target và selection được trình bày riêng. Kết quả từ Ginnie không tăng số Freddie vintages và không mở gate R2/R3 cho Freddie.

## Điều khoản và quyền truy cập

Ginnie Mae nêu rõ single-family loan-level data chỉ dành cho phân tích Ginnie Mae MBS; cấm cố nhận diện cá nhân hoặc liên kết dữ liệu với thông tin khác nhằm suy ra danh tính. Thông cáo gốc nêu người dùng cần đồng ý Terms of Use trước khi sử dụng loan-level files. Người dùng đã xác nhận trong chat rằng họ đã đọc và chấp nhận Terms of Use. Xác nhận này không tạo ra hay thay thế một phiên đăng nhập; chưa tải production data.

Sau khi chủ tài khoản/người dùng xác nhận điều khoản trực tiếp, pilot hợp lý là một quarterly performance file nhỏ hơn annual file (catalog hiện liệt kê gần 783 MB nén), cùng liquidation file ở kỳ phù hợp nếu được phép. Trước khi tải toàn bộ history 2.3 GB/year cần pilot định dạng, tỷ lệ nén, row counts, memory/disk, schema và duplicate keys. Giữ nguyên raw package private ở D:, receipt có URL/timestamp/hash/source release, không đưa raw data hoặc source-derived loan rows lên GitHub.

## Trạng thái truy cập production — 16/10/2026

Catalog production kiểm tra trực tiếp qua API công khai `https://www.ginniemae.gov/bulk-content/api/disclosure-data` và hiện liệt kê `LoanPerf_202606.zip`, 782,688,297 bytes, sửa lần cuối 16/07/2026. Cấu hình client chính thức dùng profile endpoint `https://www.ginniemae.gov/user-profiles/api/profile`; giao diện yêu cầu cookie phiên `gm_up_token`, xác thực profile rồi gọi `https://www.ginniemae.gov/disclosure-api/api/download?dlfile=data_bulk%2FLoanPerf_202606.zip`. URL ZIP tự đoán trả HTML app shell. Một request thử trước đây dùng query `file`; đó không phải tham số mà giao diện chính thức dùng. Không dùng cookie giả hay tìm cách bỏ qua đăng nhập.

Các file production liên quan trong catalog cùng lần kiểm tra:

| File | Bytes nén | Cập nhật catalog | Vai trò dự kiến |
|---|---:|---|---|
| `LoanPerf_202606.zip` | 782,688,297 | 16/07/2026 | Quarterly performance pilot; hồ sơ hoạt động và lịch sử hiệu suất |
| `LoanPerfAnn_202512.zip` | 2,302,624,988 | 20/01/2026 | Annual performance; vượt giới hạn pilot 1 GiB, chưa chọn để tải đầu tiên |
| `llpaymhist_202609.zip` | 67,497,851 | 15/10/2026 | MBS loan payment history; cần review layout/key trước khi xét ghép |
| `liqloanqtr_202609.txt` | 218,846 | 13/10/2026 | MBS terminated-loan quarterly; exit/removal context, cần audit schema riêng |
| `llmonforb_202609.zip` | 1,245,711 | 13/10/2026 | Loan-level forbearance supplemental; cần kiểm tra coverage và join key |

Ưu tiên tải `LoanPerf_202606.zip` làm pilot với parser đã có. Sau khi schema/key và phạm vi permission được xác nhận, audit riêng `liqloanqtr` và `llpaymhist` làm nguồn bổ sung; chỉ ghép nếu layout và key chứng minh đúng grain/period. Forbearance không được tự động coi là outcome hay predictor. Không tải annual 2.3 GB trước khi pilot xác nhận dung lượng expanded, parser throughput và cách bảo quản.

User nói có thể tự đăng nhập và lưu cookie trên D:, nhưng chưa gửi đường dẫn file. Chỉ cần cung cấp **đường dẫn** Netscape cookie file; không gửi nội dung cookie/mật khẩu trong chat. Cookie sẽ được đọc tại chỗ cho request production, không được in log hay ghi vào receipt. Nếu phiên Ginnie không dùng cookie Netscape tương thích hoặc cookie hết hạn, dừng và yêu cầu người dùng xuất lại phiên qua giao diện chính thức.

## Payment-history layout và sample audit — 16/10/2026

Layout chính thức v1.0 (01/06/2021) áp dụng cho single-family loans đang active
trong Ginnie Mae pools và issuer-reported data. Mỗi file monthly gồm một HH và
TT toàn file, cùng một cặp PH/PT cho mỗi pool; giữa chúng là các LL, mỗi loan
một record. LL-3 Disclosure Sequence Number là key disclosure chung được tài
liệu cho phép dùng để nối record với một số disclosure files Ginnie khác; không
được suy rộng thành quyền/linkage sang Freddie, NSMO, HMDA hay danh tính bên
ngoài. LL-5 là tối đa 24 mã delinquency, hai ký tự mỗi kỳ, thứ tự mới nhất ở
bên trái; `00` current, `01`–`99` số tháng delinquent, `XX` unavailable. Lịch sử
có thể ngắn hơn 24 kỳ. Đây là một panel active-pool có chọn lọc, không phải
toàn bộ mortgage origination hay lịch sử của loan đã rời pool.

### Module phù hợp và KPI có thể xây

Tách thành **Ginnie MBS Payment Trajectory / Portfolio Monitoring**, một
performance-monitoring case, không phải origination credit-scoring model. Các
KPI hữu ích gồm active-loan denominator theo kỳ; phân phối current delinquency
`00/01/02/03+`; số lần/độ dài history khả dụng; roll-rate/transition theo cặp
tháng liền kề; cure, worsening và persistent delinquency theo trạng thái được
định nghĩa riêng; segmentation theo pool/issuer nếu cho phép và có denominator
đúng. Vì LL-5 lưu mức tháng delinquent chứ không phải ngày quá hạn, không gọi
đây là DPD chính xác. `XX` phải ở nhóm unavailable, không được xem là current.

Nguồn phù hợp để nghiên cứu chuyển trạng thái và giám sát risk trong panel
active của Ginnie Mae; nó không có application-time income, debt, property
features trong layout này nên không đủ riêng để huấn luyện underwriting PD.
`llpaymhist` cũng là trạng thái hiện tại cộng lịch sử cuộn, không có monthly
originations/full-risk-set hay khoản vay đã rời pool; tỷ lệ 90+ trên tập này sẽ
có active-survivor/selection bias và không phải cumulative default rate.
Potential join chỉ với Ginnie disclosure products khi cùng loan key, report
period, definition/version và grain đã xác minh; ưu tiên giữ raw source tables
tách biệt, tạo explicit source-specific adapter, và lưu match/unmatched counts.

Layout PDF và file sample chính thức đã lưu riêng trong private D:. Sample gồm
20 pool, 53 LL loan records và 95 records tổng; HH/TT và từng PT count khớp.
Audit aggregate-only cho thấy 498 status occurrences, độ dài lịch sử 1/2/3/24
kỳ và 0 `XX` trong sample này. Đây chỉ là kiểm tra parser/layout trên sample,
không phải thống kê population hay bằng chứng event rate. Sample có loan/pool
identifiers nên không được đưa lên GitHub.

Đã thêm `src/credit_atlas/ginnie_payment_history.py`,
`scripts/audit_ginnie_payment_history.py` và synthetic contract tests. Auditor
kiểm tra HH/PH/LL/PT/TT widths, thứ tự pool/loan, key trùng, report period,
pool và file totals, miền status code và độ dài history; kết quả chỉ giữ số
tổng hợp, độ dài file và SHA-256, không trả ra identifiers. Parser hỗ trợ TXT
và ZIP một-member; chạy trên TXT mẫu đã reconcile tất cả trailer totals.
Production ZIP vẫn cần phiên xác thực và
sẽ được profile riêng sau khi tải; không gộp với LoanPerf/liqloanqtr trước khi
đối chiếu period và grain.

## Kế hoạch tiếp tục sau khi có phiên đã đăng nhập

1. User đã xác nhận đọc và chấp nhận Terms of Use; chỉ truyền file cookie path, không đưa bí mật vào chat.
2. Dùng catalog API để xác thực metadata, rồi route download chính thức với `dlfile=data_bulk/LoanPerf_202606.zip`; giữ ZIP private và ghi hash/size trước khi đọc. Payment-history download cũng phải theo đúng catalog path và access flow hiện hành.
3. Lấy file layout/dictionary chính thức tương ứng, xác nhận file version, record widths/delimiters, HH/LP/TT totals và period coverage.
4. Stream parse theo record, chỉ ghi canonical source-specific tables; kiểm tra key/period uniqueness, row totals, date ranges, legal status codes, LTV/DTI/FICO bounds, UPB logic và missingness.
5. Profile active-survivor bias và exit coverage bằng liquidation/performance records; không gán non-event cho loan biến mất.
6. Tạo riêng Ginnie source card/case; nếu target hoặc event support không phù hợp, giữ descriptive-only và dừng model work.

Runner đã chuẩn bị: `scripts/download_ginnie_loanperf.py`. Sau khi user cung cấp
đường dẫn Netscape cookie file trên D:, lệnh sẽ validate profile, chỉ gửi
`gm_up_token` tới host Ginnie Mae chính thức, lấy size từ catalog API, giới hạn
ZIP ở 1 GiB, giữ raw ZIP trong private D:, rồi ghi receipt không chứa cookie.
Profile/auth failure dừng trước khi gọi download. Chạy audit aggregate-only kế
tiếp bằng `scripts/audit_ginnie_loanperf.py <ZIP> --terms-accepted-by-user`.

## Nguồn chính thức

- [Ginnie Mae Disclosure Data Download](https://bulk.ginniemae.gov/)
- [Ginnie Mae Single-Family Loan-Level Terms of Use](https://tst.ginniemae.gov/investors/disclosures_and_reports/Pages/Single-Family-Loan-Level-Terms-of-Use.aspx)
- [Loan Performance File quarterly layout](https://bulk.ginniemae.gov/LayoutsSamples/471/LoanPerf_layout.pdf)
- [Loan Performance File annual layout](https://bulk.ginniemae.gov/LayoutsSamples/479/LoanPerfAnn_layout.pdf)
- [Single-family monthly loan-level layout v1.8](https://bulk.ginniemae.gov/LayoutsSamples/444/llmon1_layout.pdf)
- [Liquidation/payoff layout](https://bulk.ginniemae.gov/LayoutsSamples/363/llmonliq_layout.pdf)
- [MBS Single-Family Loan Payment History layout v1.0](https://www.ginniemae.gov/s3/sites/default/files/disclosure_data_files/llpaymhist_layout.pdf)
- [Single-family loan-level dictionary](https://www.ginniemae.gov/doing_business_with_ginniemae/investor_resources/mbs_disclosure_data/Lists/LayoutsAndSamples/Attachments/54/mbsloanlevel_dictionary.pdf)
- [Ginnie Mae announcement of loan-level disclosures and Terms of Use](https://www.ginniemae.gov/newsroom/press-release/ginnie-mae-provide-loan-level-data-existing-single-family-mortgage-backed)

Source review is not a legal opinion or permission certificate. The live download catalog and terms must be rechecked at acquisition time.
