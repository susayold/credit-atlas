# P3.10 — nghiệm thu Business review/export

Checkpoint 15/10/2026. Phạm vi trong plan: private SEC/SBA reports, issuer financial memo/history, private JSON và filter-scoped SEC Excel Analysis/Facts. Hai nguồn giữ riêng reporting grains; owner/review chưa authenticated. Không nâng scope thành borrower underwriting, calibrated issuer PD hoặc accounting ECL.

## Private JSON và source quality

`business-review-export-audit-1d5eda8fb468/receipt.json` PASS 67 SEC statement exports, đúng CIK/accession/cutoff và toàn bộ statement projection từ canonical case đã được audit raw-source. Đối chiếu 536 financial fields và 268 ratios, giữ exact text/candidates/support status. Attachment/private/model/PIT flags đúng. Mỗi bản xuất được lưu kèm SHA.

SBA có 371 nonempty/whole-scope exports trên tất cả program/dimension/bucket được hỗ trợ. `business-export-quality-audit-630368d18d8e/receipt.json` bổ sung bảy giao điểm hợp lệ nhưng không có records, đưa coverage lên **378 scopes**. Empty intersection trả rows rỗng/count zero, vẫn giữ whole-source quality và các qualification false.

Mọi SBA export có selected-record count khớp rows, amount scope đúng program, whole-source six-segment quality, contract và business identity. SEC quality đúng issuer; annual options thuộc đúng CIK/cutoff. Fields của SEC và filters của SBA không được ghép thành một borrower dataset. Không fuzzy-match tên SBA với SEC hoặc tạo fixed-horizon PD labels/current EAD từ reported approvals.

Whole-source SBA numerical/source/dictionary audits đã đóng P3.01/P3.05/P3.09: 2.190.504 records, 54.762.600 canonical-cell comparisons và 1.197 aggregate cells. Các receipts/source hashes được giữ nguyên; lần này kiểm downstream exports, không tuyên bố đọc lại toàn bộ CSV source.

## UI và scope controls hiện tại

`sba-june-browser-acceptance-75fe6d2cd40f/receipt.json` PASS 12 program/dimension UI/API/download parities và chín selected buckets; all six quality rows, 81 dictionary definitions/162 cell coordinates; URL reload, mobile, invalid scope/raw-loan filter và cross-origin guards. Whole-source quality không bị trình bày như quality riêng của bucket.

`sec-workbook-qa-77226775fb35/receipt.json` PASS actual UI POST/download và exact source/cached formula audit, mobile và controlled export-error handling. Captured workbook được server tạo từ scope, không lấy financial facts do client tự gửi.

## SEC Excel — 36 phạm vi

`sec-workbook-scope-audit-09ac934bdc4e/receipt.json` PASS bốn issuers × ba windows 3/5/10 × ba explicit interest concepts. Workbook download SHA khớp immutable server capture; trend và coverage filter projections khớp query; XML formulas/caches/exact text/missing guards khớp source. Receipt pin method/builder hashes của bản server hiện tại.

`sec-excel-equivalence-17a3f1d744a8/receipt.json` PASS so sánh mọi populated cell coordinate/type/value/formula với baseline `sec-workbook-scope-audit-1133f2bb3c7b`. Đủ 36 scopes, **73.656 cells và 14.040 formula cells giống hoàn toàn**. Mỗi baseline workbook được nối với đúng source SHA trong native receipt `native-excel-qa-sec-1a75771ee189`, không có failures và không save bản QA.

Vì inputs/formulas và builder không thay đổi, bằng chứng native CalculateFullRebuild được tái sử dụng cho các ô tương đương. Không tuyên bố đã chạy native lần nữa. Full metadata, date, source-lineage audit và 216 native input cases thuộc bộ P3.03 đã nghiệm thu. Những receipts này vẫn giữ hash; nội dung Excel hiện tại được nối bằng equivalence proof.

## Financial memo và review

P3.06 đã đóng financial memo editor, issuer list, canonical evidence digest, atomic history và full private JSON. Tám capture scopes và hai real isolated UI/HTTP cases với bốn revisions: stale revision/injected capture bị từ chối; source outage không ghi đè capture cũ; list/export/revise cũ vẫn đọc được. Kho memo chính không nhận QA records. Dùng hồ sơ `P3_CORPORATE_MEMO_ACCEPTANCE_VI.md`, không tạo memo thử vào production store trong lần kiểm gói này.

Narrative là analyst input; Reviewed/Owner tự khai báo. Memo không tự trở thành credit approval, issuer PD, DSCR hay covenant compliance. Issuer filing metadata timeline đã có trong P3.06; full-text events và actual debt/covenant qualification vẫn thuộc phần phát triển tiếp theo.

## Kết luận phạm vi

Các private reports/JSON, memo history và filter-scoped Excel đáp ứng đầu ra P3.10 hiện tại. Giữ nguyên required inputs/private evidence omitted from public release trong sổ 50 yêu cầu. Scoped borrower handoff, reviewer authentication và actual risk-decision inputs không được suy ra từ gói research này.
