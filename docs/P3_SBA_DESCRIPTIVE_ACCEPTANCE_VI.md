# P3 SBA — nghiệm thu scope descriptive hiện tại

Ba yêu cầu của plan: P3.01 SME source explorer, P3.05 SBA outcomes/cohorts và P3.09 sector/concentration. Scope vẫn là SBA source-program descriptive analysis; không đổi thành PD model, unique borrower registry hoặc EAD book.

## Bằng chứng dữ liệu và phép tính

- Case hiện tại: `business-sba-21c568f10f7d`, snapshot 30/06/2026, sáu source segments và 2.190.504 records.
- Audit độc lập `artifacts/private/sba-june-acceptance-audit-68fc1c9fc7f3/receipt.json`: PASS toàn bộ CSV → Parquet. Python CSV/Decimal/date parsing riêng, không gọi adapter/canonical SQL hoặc verifier để tạo kết quả mong đợi. So sánh 54.762.600 canonical cells trên 25 fields/record, bao gồm ordinal/key, status raw/mapped, dates, money, integers, lender/geography/sector và metadata đã chọn.
- Whole-source parse diagnostics và 11 flags mỗi segment khớp saved quality. Exact duplicate excess tổng 1.987 vẫn được giữ. Candidate fingerprints được giải quyết bằng raw tuples ở lần đọc thứ hai; hash collision không tự được tính là duplicate.
- Toàn bộ 1.197 aggregate cells của bốn dimensions program_status/approval_fiscal_year/project_state/naics_two_digit khớp độc lập về records, exact approval/chargeoff sums và known counts. Money được cộng bằng Decimal precision 60, không float/round/clipping; missing giữ riêng.
- Dictionary audit `artifacts/private/sba-dictionary-cells-audit-3a7a239b2dcc/receipt.json`: 81 fields/162 cells khớp XLSX gốc tại đúng sheet và coordinates, kiểm tra cả tập field đầy đủ.
- Inputs được SHA kiểm tra trước và sau audit; raw, receipt và saved artifacts được giữ nguyên. Không fit/inference hoặc mở predictor rows Retail/final holdout.

## API, app và export

`artifacts/private/sba-june-browser-acceptance-2aa48e282571/receipt.json` PASS sáu nhóm:

1. Toàn bộ 12 program/dimension combinations (all/7A/504 × bốn dimensions), UI counts/cells, private API và downloaded JSON khớp exact saved rows; thêm chín selected buckets.
2. Program/dimension/bucket giữ đúng qua URL reload.
3. Cả sáu source quality rows khớp retained/duplicate/date/outcome flags và vẫn whole-source khi cohort filters thay đổi.
4. Đã mở rộng app Dictionary từ một số field tiêu biểu thành đủ 81 definitions và 162 source coordinates. HTTP JSON sắp xếp program object keys; definitions/list order trong từng program không đổi.
5. Mobile không page overflow; archive March riêng tiếp tục mở được.
6. Invalid program/dimension/bucket/raw-loan query và cross-origin bị reject.

`artifacts/private/sba-status-support-browser-4751769c93c6/receipt.json`: PASS thêm selected status drill-down, source program/bucket denominator cho toàn bộ 1.197 snapshot-share cells qua tám scopes, filter change xóa detail cũ, mobile và ledger không đổi.

`artifacts/private/sba-june-acceptance-tests.xml`: 23 PASS (adapter/dictionary/source-quality/report guards và independent-audit boundary cases). Tests dùng synthetic fixtures, khác với audit/browser kiểm tra corpus thực.

Hai lần browser QA chưa hoàn tất được giữ làm checkpoint thất bại: lần đầu dừng vì report HTTP không phải 200; request kiểm tra sau đó trả 200. Không suy nguyên nhân của lỗi đầu khi thiếu response detail. Lần tiếp theo đã hoàn tất scope/export nhưng dừng ở assertion dictionary do program ordering; kiểm tra riêng chứng minh đủ 81 cells rows đúng nội dung, và test đã sửa để nhận HTTP key ordering. Chỉ receipt PASS đầy đủ sau sửa được dùng nghiệm thu.

## Điều kiện theo từng yêu cầu

| Mục | Bằng chứng đóng scope hiện tại |
|---|---|
| P3.01 | Sáu sources/counts/schema, 81 dictionary fields, raw/canonical parity và whole-source quality/duplicates; app thể hiện record grain, không unique borrower count |
| P3.05 | Status/FY cohorts và selected detail; source-aware program/amount definitions; denominator supports và decimal-preserving filtered reports; fixed-horizon default target và model fit flags luôn false |
| P3.09 | Sector/geography tables và scoped exports; unknown buckets giữ riêng, denominators đối soát; approval amounts có scope 7A/504 riêng và amounts_are_current_exposure=false |

Đóng ba mục này không đóng P3.02/.03/.04/.06/.07/.08/.10. Public SBA program records không đại diện toàn bộ SME economy; snapshot statuses không là fixed-horizon PD; post-outcome fields không trở thành application predictors. Chưa có loan/borrower identity, lịch sử publication availability, cross-snapshot transitions hoặc scoring intended-use qualification.

Snapshot March đã được acquisition/audit/API/UI riêng nhưng schema có thêm subprogram chưa được dictionary hiện tại qualify. Không trộn archive vào June case, không join borrower names với SEC để tạo labels.

Nghiệm thu này chỉ dùng cho ba yêu cầu descriptive hiện tại. Tổng suite sau khi recorder kiểm tra và ghi bằng chứng: 18/50 mục, 36%; scope gốc và checkpoint labels giữ nguyên.
