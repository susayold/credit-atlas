# NSMO — rà soát tương đương câu hỏi qua các wave

Ngày rà soát: 16/10/2026. Đây là phần bổ sung cho audit coverage 319 survey
fields × 46 waves và pilot sáu item. Mục tiêu là phân biệt câu hỏi có wording
được tìm thấy ở mọi questionnaire với câu hỏi có thể gộp câu trả lời như cùng
một phép đo. Không dùng câu hỏi hồi cứu trong đây làm predictor tại origination.

## Phương pháp và phạm vi

- Dùng 22 questionnaire package chính thức bao phủ waves 1–46; SHA-256 khớp
  acquisition receipt riêng tư.
- Dò sáu item credit-relevant trong text PDF, đối chiếu scope wave của SAS
  formats với coverage trong PUF, rồi kiểm tra trực quan questionnaire page 9
  (PDF page 11) của waves 1–2 và 11–12 cho item X94A.
- Phân biệt option wording, response scale, wave/question numbering và dữ liệu
  not-asked. Đây là kiểm tra wording/scale; không chứng minh measurement
  invariance, respondent equivalence, mode equivalence hay population
  representativeness.

## Kết quả

| PUF item | Nội dung ngắn | SAS scale | Kết quả wording | Kết luận dùng |
|---|---|---|---|---|
| X05F | Mức độ quen thuộc với lịch sử/tín dụng của người vay | PVERYFM: Very / Somewhat / Not at all | Cụm response item xuất hiện trong cả 22 packages; intro wording thay đổi giữa questionnaire versions | Candidate cho descriptive wave trend; giữ caveat hồi cứu và chưa dùng làm origination predictor |
| X88D | Late payments will lower my credit rating | PAGREEFM: Agree / Disagree | Item wording ổn định trong 22 packages; ma trận attitude có thêm/bớt item khác và số câu thay đổi | Candidate trend riêng; không gộp numeric code ngoài đúng SAS mapping |
| X88E | Lenders shouldn't care about late payments if loans are repaid | PAGREEFM | Item wording ổn định trong 22 packages; context quanh ma trận thay đổi | Candidate trend riêng, không diễn giải thành hành vi tín dụng thực tế |
| X88F | Có thể ngừng trả mortgage nếu có lợi cho người vay | PAGREEFM | Item wording ổn định trong 22 packages; context quanh ma trận thay đổi | Candidate trend riêng; là thái độ tự khai, không phải default label |
| X93B | Khả năng gặp khó khăn trả mortgage trong vài năm tới | PVERYFM | Response item xuất hiện trong cả 22 packages; stem và question number có phiên bản theo wave | Candidate descriptive trend; không phải forecast đã kiểm định |
| X94A | Có thể trả hóa đơn 3 tháng mà không vay khi gặp khủng hoảng | PVERYFM | Item vẫn có trong 22 packages; option khác đổi wording: waves 1–10 “Borrow enough money from a bank or credit union”; bắt đầu package waves 11–12 là “Borrow a significant amount from a bank or credit union”. Ba option còn lại và nhãn Very / Somewhat / Not at all giữ nguyên ở hai bản đã kiểm tra trực quan | Giữ nguyên mã SAS nhưng ghi version break; khi so trend phải sensitivity/stratify theo wording version, không khẳng định bất biến |

Questionnaire pages được xem trực quan xác nhận hai cách diễn đạt của X94A và
cùng ma trận ba mức trả lời. Thay đổi “enough” → “a significant amount” có thể
đổi ngưỡng tự đánh giá dù mã hóa và nhãn đáp án không đổi. Vì vậy PUF raw
response không nên được coi tự động là thang đo đồng nhất qua toàn bộ 2014–2025.

## Hệ quả với D02

1. Giữ sáu item trong descriptive workspace, nhưng chỉ gắn nhãn “candidate
   wording reviewed”; chưa bật làm feature/model predictor.
2. Với X94A tạo hai version group: waves 1–10 và waves 11–46. Nếu trình bày
   trend dài hạn, cho thấy break, chạy sensitivity tách hai nhóm, và không quy
   thay đổi tỷ lệ cho người vay nếu không xử lý version effect.
3. Giữ survey wave, questionnaire version, response scope và not-asked codes
   trong metadata. Không biến `-3`/`-2` thành một đáp án thái độ.
4. Các item attitude/expectation là câu trả lời sau khi mortgage bắt đầu. Không
   dùng làm đặc tính origination hay claim dự báo rủi ro tại thời điểm cấp vay.
5. Tiếp tục manual routing/population/mode review và đánh giá survey design/
   variance trước suy luận. Text hoặc scale giống nhau không thay thế các gate
   này.

## Nguồn

- [FHFA NSMO PUF, codebook, SAS formats và questionnaire catalog](https://www.fhfa.gov/data/nsmo)
- [Questionnaire waves 1–2](https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-1-and-2)
- [Questionnaire waves 11–12](https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-11-and-12)
- Local source validation: `artifacts/private/nsmo-questionnaire-acquisition-20261015/receipt.json` and `artifacts/private/nsmo-key-item-version-audit-20261015/receipt.json` (private, not committed).
