# P2.04 — nghiệm thu Private Loan Lifecycle

Ngày12/10/2026. Đối chiếu P2.04 với case `d01-a24484b21a21`, annual sample2012. Chức năng đọc observed history và confirmed events bằng run-scoped pseudonymous key; không dự báo hoặc quyết định tín dụng.

## Yêu cầu và bằng chứng

| Yêu cầu gốc | Đối soát | Kết quả |
|---|---|---|
|Run-scoped pseudonymous loan key|Toàn index đối chiếu dim_loan/labels; uniqueness/format và case-bound queries|50.000rows/50.000unique keys,0source differences|
|Observed states/UPB|Timeline probes so toàn monthly fields với canonical source; static/label fields kiểm tra riêng|10timeline cases PASS|
|Confirmed events|So dates/types với episodes Parquet; bao phủ event/exit representatives|PASS|
|Timeline và UPB chart|Browser đối chiếu row/event counts và từng confirmation date/type; chart ghi observed principal|10cases PASS|
|Không lộ raw loan ID|Quét source-ID membership trong15static assets và JSON danh sách/timeline; allowlisted response fields|Không tìm thấy raw IDs|
|Không coi observed timeline là forecast|UI/API limitation và chart labels xác nhận observed retrospective/no prediction|PASS|
|Không backdate confirmation|Nguồn confirmed events đã nghiệm thu P2.06; timeline và browser giữ nguyên dates|PASS|

## Defect phát hiện và đã sửa

Tìm một key không có kết quả trước đây làm danh sách trống nhưng giữ timeline cũ ở bên phải. Browser acceptance ghi nhận lỗi và screenshot trước sửa. App hiện xóa timeline/loan context khi bắt đầu tìm kiếm, chỉ đặt loanKey sau khi timeline request thành công; empty list, invalid input hoặc API lỗi giữ pane unavailable. Preferred previous key chỉ được chọn lại nếu vẫn có trong response mới.

Generation/request guards tiếp tục chặn late responses. QA dùng hai response thật trả về đảo thứ tự: response cũ không thể dựng lại timeline sau empty search mới. Khi timeline API503, loanKey giữ trống; retry valid key phục hồi. Không thay backend source,raw files hoặc model.

## Receipts

- `private evidence omitted from public release`: full index,16list scopes,10timelines,static/label/monthly/event fields,prefix search và15static asset checks PASS. Source input/index/case/method hashes được lưu.
- `private evidence omitted from public release`: **19 PASS** gồm cross-run token rejection,private queries không trả sourceID,foreign loan finding không ghi được,frozen integrity và filters.
- `private evidence omitted from public release`: **10timeline cases PASS**, empty/pending/invalid/outage context clearing,late-list-response discard,recovery và mobile. Không page errors; frozen retail ledger unchanged. Timeline và empty/error mobile đã visual-review.
- Lượt browser trước sửa không PASS ở empty search và được giữ riêng; không lấy nó làm evidence nghiệm thu.

## Hồi quy sau thay đổi frontend

Đã chạy lại các workspace dùng cùng app.js:

- P2.05: `transition-browser-acceptance-269c134a5dc0/receipt.json`,6scopes PASS.
- P2.06: `cure-browser-acceptance-fb399d21b288/receipt.json`,8follow-up scopes/4timeline types/4exports PASS.
- P2.07: `competing-browser-acceptance-84a581a3cd33/receipt.json`,12segment×horizon scopes PASS.

Chúng được append làm current frontend regression evidence; giữ original numerical/source acceptance receipts.

## Giới hạn và kết luận

Keys là pseudonymous trong một run, không chứng minh borrower identity liên kết qua nhiều khoản vay. Display amounts làm tròn; JSON dùng existing numeric representation, không là accounting ledger. API list bị chặn ở50records; UI hiện20records và prefix search. Paging/search mở rộng và formal loan-linked review là bước tiếp theo của plan.

Đủ evidence cho toàn bộ yêu cầu hiện tại P2.04. P2.03 monthly portfolio/profile đang được rà riêng; không nâng trạng thái từ lifecycle audit. Multi-vintage/model/governance và goal100% vẫn mở.
