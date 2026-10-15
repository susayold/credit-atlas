# Ginnie Mae loan-level performance — đánh giá nguồn bổ sung

Ngày rà soát: 15/10/2026. Đây là một nguồn mortgage loan-level riêng, có tiềm năng cho một case MBS-credit độc lập. Nguồn này **không thay thế Freddie**, không được gộp vào case D01 hiện tại, và dữ liệu chưa được tải vì phải xác nhận điều khoản sử dụng trước khi truy cập loan-level payload.

## Nguồn có gì

Trang Disclosure Data Download của Ginnie Mae công bố các file daily, monthly, quarterly và annual. Snapshot catalog đang liệt kê:

| File | Kỳ gần nhất trong catalog | Quy mô nén được liệt kê | Grain / ý nghĩa |
|---|---:|---:|---|
| `LoanPerf_202606.zip` | 2026Q2 | 782,688,297 bytes | Loan-performance record theo kỳ, tối đa 3 kỳ/loan trong file quarterly |
| `LoanPerfAnn_202512.zip` | năm 2025 | 2,302,624,988 bytes | Loan-performance record theo kỳ, tối đa 12 kỳ/loan trong file annual |
| `llmon_202609.zip` | 2026-09 | 435,389,415 bytes | Monthly portfolio disclosure cho các loan đang active trong MBS Ginnie Mae |
| `llmonliq_202609.zip` | 2026-09 | 1,917,130 bytes | Loan-level monthly liquidation/payoff disclosures |
| `llmonforb_202609.zip` | 2026-09 | 1,245,711 bytes | Loan-level forbearance supplement; schema riêng |

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

Catalog production vẫn liệt kê `LoanPerf_202606.zip` khoảng 783 MB. Recheck giao diện Angular công khai của `https://bulk.ginniemae.gov/` cho thấy luồng download yêu cầu cookie phiên `gm_up_token`, gọi profile endpoint để xác thực token rồi chuyển đến download route của Disclosure WCF. Các URL ZIP trực tiếp và endpoint thử không kèm phiên chỉ trả HTML app shell, không phải payload. Vì thế 401 trước đó là auth gate; không dùng URL đoán, cookie giả hay cách bỏ qua đăng nhập.

User nói có thể tự đăng nhập và lưu cookie trên D:, nhưng chưa gửi đường dẫn file. Chỉ cần cung cấp **đường dẫn** Netscape cookie file; không gửi nội dung cookie/mật khẩu trong chat. Cookie sẽ được đọc tại chỗ cho request production, không được in log hay ghi vào receipt. Nếu phiên Ginnie không dùng cookie Netscape tương thích hoặc cookie hết hạn, dừng và yêu cầu người dùng xuất lại phiên qua giao diện chính thức.

## Kế hoạch tiếp tục sau khi có phiên đã đăng nhập

1. User đã xác nhận đọc và chấp nhận Terms of Use; chỉ truyền file cookie path, không đưa bí mật vào chat.
2. Dùng giao diện/route production chính thức `LoanPerf_202606.zip` cho quarterly pilot; giữ ZIP private và ghi hash/size trước khi đọc.
3. Lấy file layout/dictionary chính thức tương ứng, xác nhận file version, record widths/delimiters, HH/LP/TT totals và period coverage.
4. Stream parse theo record, chỉ ghi canonical source-specific tables; kiểm tra key/period uniqueness, row totals, date ranges, legal status codes, LTV/DTI/FICO bounds, UPB logic và missingness.
5. Profile active-survivor bias và exit coverage bằng liquidation/performance records; không gán non-event cho loan biến mất.
6. Tạo riêng Ginnie source card/case; nếu target hoặc event support không phù hợp, giữ descriptive-only và dừng model work.

## Nguồn chính thức

- [Ginnie Mae Disclosure Data Download](https://bulk.ginniemae.gov/)
- [Ginnie Mae Single-Family Loan-Level Terms of Use](https://tst.ginniemae.gov/investors/disclosures_and_reports/Pages/Single-Family-Loan-Level-Terms-of-Use.aspx)
- [Loan Performance File quarterly layout](https://bulk.ginniemae.gov/LayoutsSamples/471/LoanPerf_layout.pdf)
- [Loan Performance File annual layout](https://bulk.ginniemae.gov/LayoutsSamples/479/LoanPerfAnn_layout.pdf)
- [Single-family monthly loan-level layout v1.8](https://bulk.ginniemae.gov/LayoutsSamples/444/llmon1_layout.pdf)
- [Liquidation/payoff layout](https://bulk.ginniemae.gov/LayoutsSamples/363/llmonliq_layout.pdf)
- [Single-family loan-level dictionary](https://www.ginniemae.gov/doing_business_with_ginniemae/investor_resources/mbs_disclosure_data/Lists/LayoutsAndSamples/Attachments/54/mbsloanlevel_dictionary.pdf)
- [Ginnie Mae announcement of loan-level disclosures and Terms of Use](https://www.ginniemae.gov/newsroom/press-release/ginnie-mae-provide-loan-level-data-existing-single-family-mortgage-backed)

Source review is not a legal opinion or permission certificate. The live download catalog and terms must be rechecked at acquisition time.
