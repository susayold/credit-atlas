# P2 / D08 — HMDA Origination & Application Evidence

## Dữ liệu và contract hiện tại

Source `hmda-source-979e0862af13`: **13 files, 133.468.928 bytes**, gồm ba
CSV, aggregate JSON trước/sau mỗi CSV và bốn trang tài liệu chính thức.
Scope cố định: Maryland (`states=MD`), home purchase (`loan_purposes=1`),
site-built (`construction_methods=1`), activity years **2023, 2024, 2025**.
Không có restriction theo action, loan type, occupancy hay total units:
site-built không tự có nghĩa chỉ single-family hoặc owner-occupied.

[Data Browser API](https://ffiec.cfpb.gov/documentation/api/data-browser/)
cung cấp streamed CSV và aggregate JSON. Downloader giữ original URL,
served URL và HTTP trace; chỉ theo một redirect do API trả về tới matching-year
cache CSV trên `files.ffiec.cfpb.gov`. Không dùng browser, cookies hoặc login.
Header đủ 99 unique public fields; mọi dòng phải cùng year/state/purpose/
construction, LEI đủ 20 ký tự và action thuộc 1–8. Truncated/extra-width rows,
invalid amounts hoặc count/sum lệch aggregate trước/sau sẽ không tạo receipt
hoàn tất. Các request chạy tuần tự, size cap 64 MiB/file.

Data Browser dùng release static mới nhất của từng năm. Theo
[dataset FAQ](https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq),
2023 dùng one-year release freeze 19/05/2025; 2024 dùng one-year freeze
02/06/2026; 2025 dùng snapshot freeze 02/06/2026. Đây là downloaded current
release, chưa có evidence chứng minh historical availability vào năm observation.

| Activity year | Source records | Lenders/LEIs | Decided denominator 1+2+3 | Denied (3) | Descriptive denied share |
|---|---:|---:|---:|---:|---:|
| 2023 | 113.089 | 704 | 71.956 | 7.497 | 10,4189% |
| 2024 | 116.150 | 667 | 74.390 | 7.223 | 9,7096% |
| 2025 | 117.817 | 663 | 72.103 | 7.246 | 10,0495% |

Tổng **347.056 source records**. Đây là một geographic/product pilot,
không đại diện toàn Hoa Kỳ. Bảng trên mô tả outcome share của scope đã chọn,
không phải PD, causal effect hoặc compliance finding.

## Canonical và phép tính đã có

Case `hmda-case-94ca64da2e30` có:

- `source_rows.parquet`: toàn bộ 99 raw fields dạng string, thêm source file
  và data-row ordinal. Raw blanks, NA và Exempt giữ nguyên.
- `applications.parquet`: selected typed fields, exact numeric strings,
  statuses, action names, decision-denominator eligibility và provenance.
- `evidence.json`: ba annual summaries, **7.477 mart rows** trên tám dimensions:
  county, LEI, loan type, derived race/ethnicity/sex, DTI và dwelling category.
- Receipt có source/implementation/output hashes. Verifier đọc lại original
  CSV để so toàn bộ raw/typed rows và rederive evidence; không chỉ tin hash.

Source file + row là provenance, không phải application ID. Fingerprint chỉ
kiểm tra equality của public rows. **450 groups / 682 rows beyond first** có
99 trường giống nhau; giữ tất cả. Privacy modification có thể làm các khoản
vay khác nhau trở thành public rows giống nhau; không deduplicate như loans.

[Public LAR fields](https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/lar-data-fields)
và [Modified LAR schema](https://ffiec.cfpb.gov/documentation/publications/modified-lar/modified-lar-schema)
là căn cứ units/codes. Public loan amount và property value là interval
midpoints; tổng chúng không phải số tiền thực cấp vốn chính xác. Income dùng
thousands of USD; zero, negative và numeric `1111` là values. NA/Exempt/blank
có statuses riêng. Rate giữ percent units. DTI/age bins không bị thay bằng
midpoint hoặc số cá nhân chính xác.

Header CSV thực tế là `loan_to_value_ratio`, trong khi dictionary hiện tại
ghi `combined_loan_to_value_ratio`. Adapter giữ raw field với qualification
chưa xác nhận; không silently rename hoặc tự tính leverage.

Denominator cho bảng descriptive denial: **actions 1+2+3**, numerator 3.
Withdrawn/incomplete, purchased loans và preapproval actions 7/8 được giữ
nhưng không vào mẫu số này. Zero denominator trả unavailable, không zero.
Các rate theo dimensions phải kèm support; không dùng protected attributes
để suy ra causality, fairness compliance hoặc quyết định tín dụng.

23 source tests và 12 canonical tests đã PASS: filter/header/row width,
count/amount trước–sau, field-specific sentinel, public duplicate retention,
exact units, denominator exclusions/zero, forged output dù cập nhật digest.
Independent auditor test cũng PASS. Actual audit `hmda-audit-983042fc2736`
đã PASS **24 kiểm tra**, 0 failures: DuckDB đọc lại CSV, đối chiếu hai chiều
toàn bộ 99 fields + ordinals, typed amounts/statuses/units, annual counts/sums,
8 dimension marts, decision denominators và public duplicate counts.
Full software regression: **870 tests PASS** (375 engine + 495 application),
152,99 giây. Không có raw-row hoặc mart differences. SQL cùng audit-script/case-receipt
hashes được lưu trong receipt. Audit này không chứng nhận PD/compliance.

Source prototype `hmda-source-f33ec2213116` giữ lịch sử: profile ban đầu
coi numeric income `1111` là exempt ở một dòng 2024. Current source tạo lại
với code đúng theo field và profile đã xác minh, không sửa receipt cũ.
Lần acquisition trước redirect support thất bại ở HTTP301; không coi partial
response đó là completed dataset.

## Kế hoạch tiếp theo cho D08

| Bước | Deliverable | Acceptance |
|---|---|---|
| 1. Source acquisition | Pilot 2023–2025 + docs + before/after aggregates | Đã có; count/amount/scope/schema verified |
| 2. Canonical contracts | All raw fields, selected typed application facts, marts | Đã có; source-row rederivation và 35 focused tests PASS |
| 3. Independent audit | SQL CSV reader, exact sums, bidirectional differences, denominators | Đã PASS24 checks trên347.056 records;0 differences/failures |
| 4. App/API/export | [HMDA app](HMDA_APP_WORKFLOW.md): intersecting filters/actions/breakdowns/timeline/quality/scoped reports | Đã có;16 API/view tests và10 actual browser checks PASS; exact export/URL reload/mobile |
| 5. Coverage & comparison | [Three cohort presets, ordered attrition và fixed2023mix](HMDA_COHORT_WORKFLOW.md); multiyear institution coverage | Actual826joint-martrows,independent70checksPASS; incomplete full support giữ unavailable, common support tách scope; broader lender/rare-cell work còn tiếp tục |
| 6. Evidence/review | Comparisons có numerator/denominator/scope và private findings | Review giữ source vintage, units, exclusions và limitations |
| 7. Expand scope | Additional lender/geography/year extracts theo source contract | Schema/release/rights checked; pilot không được relabel thành toàn HMDA |
| 8. Qualified research | Application outcome study nếu có intended use và split protocol | Không training default PD; no borrower identity linkage; leakage and subgroup gates riêng |

D08 không thay các gates R0–R4 của D01. Freddie mortgage lifecycle vẫn cần
additional annual vintages với access; HMDA không bổ sung repayment outcomes.
Full P2 còn HMDA reference joins/coverage/review, CRE/DSCR/maturity và model qualification; full
50-capability suite tiếp tục theo `PLAN_FIVE_WORKSPACES.md`.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/acquire_hmda_source.py
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_hmda_applications.py hmda-source-979e0862af13
.\.venv\Scripts\python.exe -X utf8 scripts/audit_hmda_applications.py hmda-case-94ca64da2e30
```
