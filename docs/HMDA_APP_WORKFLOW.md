# P2 / D08 — HMDA Application Outcome Explorer

## Nationwide 2025 application snapshot (separate case)

The workspace now opens with a national 2025 public LAR panel above the
existing Maryland case. It reads the source-bound private aggregate view
`hmda-national-view-9a5e89600e3c`; it does not combine national data with the
Maryland pilot. The snapshot has 13,543,606 records, 4,782 reporting LEIs, and
the complete eight-action distribution. The descriptive denied share is action
3 divided by actions 1+2+3 (2,115,090 / 9,360,942 = 22.5948%). Actions 4–8
remain in the record totals but outside that denominator.

Choose one of 14 national breakdowns: state, county, LEI, loan type, purpose,
lien, occupancy, dwelling, public DTI, derived race/ethnicity/sex, applicant
score-model type, or primary denial reason. Denial-reason counts only include
action 3 and are not a model target. Source blanks are shown explicitly. The
table shows up to 100 rows; **Tải breakdown JSON** exports every category for
the selected dimension. **Tải Excel** downloads the separate 7-sheet audited
codebook/source/KPI workbook. The Excel file is a review workbook, not a
filtered loan-level export.

Current API routes are `/api/hmda-national-views`, `/api/hmda-national-view`,
`/api/hmda-national-aggregates`, and `/api/hmda-national-report`. The app
re-verifies source receipt and hashes before serving and keeps the aggregate
private. This source has applications and underwriting decisions, not monthly
repayment/default labels; denied share is not PD.

To rebuild the private aggregate after a deliberate re-acquisition, run:

```powershell
python scripts/prepare_hmda_national_view.py --root D:\data\Codex\credit-atlas --source-id hmda-national-snapshot-2025-9a5e89600e3c
```

Browser acceptance: `python scripts/browser_hmda_national_qa.py --root D:\data\Codex\credit-atlas`.

Current verified view `hmda-view-89499c7d1d02`, từ case
`hmda-case-94ca64da2e30` và source `hmda-source-979e0862af13`.
Nguồn Maryland/home-purchase/site-built, ba năm 2023–2025, 347.056
public records. [Source/canonical workflow](HMDA_APPLICATION_WORKFLOW.md)
giữ 99 fields, 7.477 mart rows và independent SQL audit 24 checks PASS.

The separate official nationwide 2025 snapshot has now been acquired and
aggregate-audited, but is not yet connected to this Maryland-only app case.
Keep the scopes separate until the national view has its own filters, privacy
qualification, denominators, export contract, and independent acceptance. See
[`HMDA_NATIONAL_SNAPSHOT_2025_REVIEW_VI.md`](HMDA_NATIONAL_SNAPSHOT_2025_REVIEW_VI.md).

## Quy trình đọc trên app

Mở `http://127.0.0.1:8770/?view=hmda&hmda_view_id=hmda-view-89499c7d1d02`.
Chọn **P2 · HMDA applications** trong navigation. Mortgage run/segment/basis
controls được tách khỏi HMDA, nên không cần một D01 run để đọc HMDA.

1. Chọn activity year, reporting lender LEI, county FIPS, loan type và public
   DTI category. Các options lấy từ source đã xác minh. Lender đang hiển thị
   LEI, county hiển thị FIPS; chưa có filer/county-name reference join.
2. Chọn breakdown dimension: county/lender/loan type/DTI/dwelling hoặc
   derived race/ethnicity/sex. Bấm **Đọc HMDA aggregates** để xác nhận bộ lọc.
3. Đọc records, decided denominator, denied numerator/share và public amount.
   Record counts gồm tất cả actions trong phạm vi; decided denominator chỉ
   **actions 1+2+3**. Public amount là sum of published interval midpoints,
   không phải số tiền thực giải ngân chính xác.
4. Bảng tám actions giữ originated, approved-not-accepted, denied, withdrawn,
   incomplete, purchased loan và hai preapproval outcomes riêng. Bảng
   breakdown luôn có numerator/denominator, không chỉ một tỷ lệ trần.
5. Timeline áp dụng cùng lender/county/product/DTI filters qua ba năm.
   Current static releases không chứng minh dữ liệu đã available tại năm đó;
   coverage/composition changes chưa được chuẩn hóa.
6. Quality theo filter có counts của VALUE/NOT_APPLICABLE/EXEMPT/SOURCE_BLANK
   cho income/property value/rate. Whole-case public duplicate quality có
   nhãn scope riêng, không giả vờ là duplicate count của filter đang chọn.
7. Export xuất **bộ lọc đã đọc và đang hiển thị**, gồm exact aggregate amounts,
   counts, timeline, quality, denominator/field contract và qualification.
   Điều chỉnh control nhưng chưa bấm đọc không đổi report đang hiển thị.

Filters được kết hợp trên canonical applications; không dùng các marginal
marts để suy ra giao của lender/county/product/DTI. Tổ hợp hợp lệ nhưng rỗng
trả NO_SOURCE_RECORDS_FOR_FILTERS, records 0, denied rate null và breakdown
rỗng. Không đổi lender/year hoặc điền một tỷ lệ giả bằng zero.

DTI/age bins giữ nguyên, không midpoint-impute. Numeric income 1111 giữ value;
exemption sentinel phụ thuộc field. LTV header mismatch vẫn unqualified;
không có source credit-score values, repayment/default labels hoặc borrower
ID linkage. Các bảng race/ethnicity/sex là descriptive scope aggregates,
không chứng nhận compliance, causal effects hay quyết định tín dụng.

## API và verification

| Endpoint | Filters | Response |
|---|---|---|
| `/api/hmda-views` | Không | Verified/unavailable catalog |
| `/api/hmda-view` | `view_id` | Source scope, year summaries, filter options, units/quality/qualification |
| `/api/hmda-aggregates` | `view_id`, optional `year/lei/county/loan_type/dti/dimension` | Private scoped aggregate report |
| `/api/hmda-report` | Như aggregates | JSON attachment; đúng scope đang đọc |

Omitted year dùng latest source year; omitted dimension dùng county;
omitted categorical filters dùng all. Explicit empty/unknown values bị từ
chối. Year phải có trong source; dimensions chỉ theo allowlist. Extra score,
PD hoặc arbitrary SQL fields và duplicated query parameters bị từ chối.
API chỉ local Host/Origin, responses no-store và public_release_approved=false.
Không export raw application rows, fingerprints hoặc filesystem paths.

Lần đọc đầu trong một service xác minh đầy đủ case từ original CSV và so
all raw/typed rows/evidence; có thể mất vài phút trên bộ 347.056 rows. Cache
chỉ được tạo sau đó, có lock chống verification đồng thời trùng lặp.
**Mỗi lần đọc tiếp vẫn hash tất cả source payloads, case/source receipts và
derived artifacts**, cùng method guards. Giữ nguyên timestamp không tránh
được kiểm tra. Source mutation làm view unavailable; restart không biến dữ
liệu bị sửa thành verified vì cold verification vẫn rederive từ source.

View snapshot cũng reproject từ verified case; thay snapshot và cập nhật
digest không được chấp nhận. Equality phân biệt qualification false với0.
Report kiểm tra source guard trước và sau SQL aggregation. Numeric sums dùng
DECIMAL, không float; UI monetary tables giữ cents, graph là presentation.

16 focused tests PASS: exact scoped aggregates, intersecting filters,
empty-combination unavailable, invalid filters, cold verification once/hot
hash guards, source mutation preserved timestamp, forged projections with
updated digest, private HTTP exports và origin/parameter guards.
Full regression **870 tests PASS** (375 engine + 495 application),152,99s.
Browser actual-data acceptance `hmda-browser-qa-e939cd411bc7`: **10 checks
PASS**, gồm2025 source records/decided denominator/rate,purchased category,
actual LEI/county/FHA/DTI intersection,exact aggregate export,empty combination
unavailable,URL reload,styled chart,390px mobile,independent mortgage runs và
P2/P3/P5 navigation. Không JS/console errors; desktop/mobile screenshots đã đọc.

Live server port8770 đã warm full source verification. API năm2025 trả
117.817 records/72.103 decided/7.246 denied/public_release_approved=false.
Warm query2024/county24031/FHA/public-DTI45 trả46 records/46 decided,
1.973ms trong lần kiểm tra này; đây là một measurement, không latency SLA.

## Việc còn lại

[Cohort comparison](HMDA_COHORT_WORKFLOW.md) đã thêm3presets,orderedattrition
và fixed2023mix/common-support analysis trong panel riêng toàn-source;
12focusedtests,independent70checks và finalbrowser17checksPASS. Không áp
top-panel lender/county/product/DTI filters ngầm lên comparison scope.

Filer names theo năm đã tải và raw CSV exact joins được kiểm tra độc lập;
[reference workflow](HMDA_REFERENCE_WORKFLOW.md) ghi độ phủ và unmatched keys.
Source-bound API/UI/labeled export đã tích hợp,6 tests và browser12checksPASS;
county download hiện HTTP403,
chưa có actual reference package. Coverage/product/occupancy standardization, historical
release-vintage archive, evidence/findings/review và broader geography/year
coverage còn tiếp tục. Application-outcome research cần intended-use/split/
leakage/subgroup protocols riêng; không dùng HMDA để huấn luyện default PD.
HMDA app không đóng các D01 R0–R4 gates hoặc full P2/50-capability suite.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_hmda_view.py hmda-case-94ca64da2e30
.\.venv\Scripts\python.exe -X utf8 scripts/browser_hmda_qa.py
```
