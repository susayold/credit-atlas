# Kiểm tra nguồn thay thế cho mortgage-performance data — 15/10/2026

Mục tiêu kiểm tra: có annual loan-level performance source nào có thể bổ sung D01 mà không dùng một tài khoản/điều khoản truy cập chưa được chủ sở hữu project cấp hay không. Kiểm tra dựa trên trang/tài liệu chính thức; không tự tạo tài khoản, không chấp nhận điều khoản thay người dùng và không thử vượt access controls.

| Nguồn | Nội dung và grain | Trạng thái access công bố | Quyết định cho D01 |
|---|---|---|---|
| Freddie Mac SFLLD | Khoảng 56 triệu mortgage, origination 1999 đến 31/03/2026; monthly performance đến cùng mốc, gồm prepay, foreclosure alternatives, REO và actual-loss components | Freddie yêu cầu register/sign in Clarity để tải full, annual-by-year, non-standard và sample files. Dữ liệu unaudited; commercial redistribution cần licensing agreement | Vẫn là nguồn chính, nhưng chưa có session/điều khoản được user thiết lập; không download annual ZIP mới |
| Fannie Mae Single-Family Loan Performance | Primary fixed-rate subset và HARP subset; release 31/07/2026 gồm acquisition/performance đến Q1 2026 | Data Dynamics yêu cầu account/registration và xác nhận email; điều khoản cấm redistribution và external commercial use nếu chưa có express written consent. Trang nhắc APIs nhưng cũng yêu cầu đăng ký để truy cập performance data | Có thể dùng làm external validation sau khi có authorized access; không thay thế hoặc ghép vào Freddie run hiện tại |
| Fannie Mae Multifamily Loan Performance | Gần 74.000 loans, acquired 2000 đến 30/06/2026; loan × reporting month, có annual historical DSCR file | Dataset/dashboard qua Data Dynamics; registration/terms áp dụng. Sample files chỉ để dựng database/schema | Nguồn tiềm năng cho P2 CRE/D09; không phải residential D01, chưa thể lấy full data khi thiếu authorized session |
| FHFA/CFPB NSMO Public Use File | 62.359 sample mortgages originated 2013–2024; quarterly credit score/performance through Q3 2025; survey + mortgage/borrower supplemental fields | User explicitly authorized the Notice of Monitoring and NMDB Terms acknowledgement; both steps were submitted on FHFA's official gate before fetching the CSV ZIP | Downloaded to private D: storage and passed structural/status-domain audit: 62.359 unique IDs, 587 columns, 51 quarters, no malformed rows or unknown performance states. Build as separate NSMO case only; not Freddie monthly panel, not pooled, not a Freddie vintage. PD target/model remains undefined |
| FHFA NMDB Aggregate Mortgage Performance Statistics | National, census areas, state and metro aggregates; quarterly 2002Q1–2026Q2; 4 published series across 4 mortgage markets | Directly downloadable official ZIP; no login, cookies, or monitoring acknowledgement used for this aggregate package | Downloaded and profiled as market context only. Aggregate denominator/population and quarterly timing differ from D01; cannot supply loan labels, annual vintages, or model qualification |
| FHFA Enterprise PUDB 2025 Single-Family Census Tract File | 2,093,767 mortgage-level Enterprise acquisitions; 66 acquisition/origination, borrower-demographic and tract fields; published 24/09/2026 | Official CSV ZIP, dictionary and record-count workbook directly downloadable; no login/cookies/acknowledgement observed | Downloaded and verified in a separate credit-access/acquisition track. Contains no monthly servicing/performance outcomes; not a D01 vintage, model input, or approval-denial sample. See `docs/FHFA_PUDB_CREDIT_ACCESS_REVIEW_VI.md` |
| Ginnie Mae MBS single-family loan-level performance | Loan-per-period records; quarterly file up to 3 records/loan and annual up to 12; includes current months-delinquent state (1–6+), up to 24 prior-month two-character delinquency statuses (`00`–`99`, `XX`), current UPB, loan age, original LTV/DTI, credit score and removal reason; catalog lists 2026Q2 quarterly (782,688,297 bytes) and 2025 annual (2,302,624,988 bytes) | Official bulk catalog is public, but Ginnie Mae's loan-level Terms of Use require affirmative agreement; conditions restrict use to analyzing Ginnie MBS performance and prohibit identifying/linking to identify individuals | Strong separate Ginnie MBS case candidate; not downloaded because this user has not accepted the terms. An aggregate-only local ZIP auditor is now prepared from the official pipe-delimited layout. Not Freddie data and does not qualify M01-005/R2 for Freddie |
| HMDA national LAR | Loan/application records được sửa đổi nhằm bảo vệ privacy; application/origination decisions, product, applicant/property và lender dimensions | Dataset/API công khai | Phù hợp origination-market analysis riêng. Không có monthly post-booking payment/performance path, nên không tạo delinquency/vintage outcomes cho D01 |

## Kết luận acquisition

NSMO là microdata public-use hiếm có chứa mortgage performance ngoài GSE annual files, nhưng quan sát theo quý, sample/response process và state definitions khác; vì vậy đã mở thành **case riêng đang profile**, không thay Freddie và không làm đủ R2/R3 theo plan hiện tại. Dữ liệu đã tải sau khi người dùng ủy quyền hoàn tất Notice of Monitoring và Terms; audit cấu trúc đạt 62.359 dòng/định danh duy nhất, 587 cột, 51 quý và trọng số đủ/dương. Còn đối chiếu 587 header với codebook, kiểm toán trạng thái/censoring, định nghĩa outcome riêng và trọng số/variance trước khi đưa KPI hay PD vào app. Chưa tìm được nguồn thay thế có cùng grain monthly và cùng contract với Freddie. Ghép HMDA origination vào mortgage performance sẽ tạo linkage không có khóa chung/permission và gộp hai estimand khác nhau thành panel giả; không thực hiện.

Một lựa chọn loan-level bổ sung đã được xác định là Ginnie Mae MBS Loan Performance File. Đây là panel disclosure riêng của các khoản vay trong MBS Ginnie Mae; quarterly/annual files có cadence và active-pool selection khác Freddie, cùng months-delinquent 1–6+ và removal codes riêng. Nguồn có giá trị cho một case parallel nếu đáp ứng câu hỏi credit-performance của Ginnie MBS. Ginnie Mae yêu cầu chấp nhận Terms of Use trước khi dùng loan-level data; do đó hiện chỉ rà soát catalog, điều khoản và layout, chưa tải payload. Không dùng Ginnie để thay annual Freddie samples, không gộp loan keys/populations và không tuyên bố đạt R2/R3 Freddie.

Đã tải thêm bộ FHFA NMDB aggregate performance chính thức, release 30/09/2026: 261.856 dòng, 13 cột, 98 quý (2002Q1–2026Q2), bốn series × bốn mortgage markets × sáu geography levels. Có 261.856 aggregate keys duy nhất; 764 dòng được đánh dấu suppressed và 48.028 VALUE1 trống/`.` trên toàn file. Bộ này cho bối cảnh quốc gia/regional/metro và đối chiếu xu hướng chung; nó không chứa loan IDs, không ghép được vào Freddie panel, không tạo target hoặc predictor ở cấp khoản vay và không được tính là annual vintage. Receipt/hash/profile bản end-to-end mới nhất ở `data/private/public-context/fhfa-nmdb-performance-e287056bb7cf/receipt.json`; card chỉ được hiển thị riêng trong D01 Sources với caveat rõ ràng.

**Trạng thái:** annual Freddie vintages bổ sung = 0; Fannie external loan panel = 0; NSMO microdata chưa tải vì acknowledgement FHFA chưa được người dùng xác nhận; Ginnie loan-level payload chưa tải vì chưa chấp nhận Terms of Use; NMDB aggregate context đã tải nhưng không thay đổi điều kiện R2/R3. R0/R1/R4 descriptive tiếp tục; Ginnie được theo dõi như extension tách biệt.

FHFA Enterprise PUDB 2025 đã được tải riêng và kiểm tra đủ 2,093,767 record keys. Đây là dữ liệu acquisition và credit-access composition; dù file chứa Fannie/Freddie records và borrower attributes, nó không chứa performance và không được đếm thành loan-performance panel hay annual vintage. Source review, field semantics, receipt và privacy boundary nằm ở `docs/FHFA_PUDB_CREDIT_ACCESS_REVIEW_VI.md`.

## Official references

- [Freddie Mac Single-Family Loan-Level Dataset](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
- [Fannie Mae Single-Family Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data)
- [Fannie Mae Data Dynamics access and FAQ](https://capitalmarkets.fanniemae.com/tools-applications/data-dynamics)
- [Fannie Mae Multifamily Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/multifamily-loan-performance-data)
- [FHFA/CFPB NSMO Public Use File](https://www.fhfa.gov/data/nsmo)
- [FHFA NMDB Aggregate Statistics and quarterly performance ZIPs](https://www.fhfa.gov/data/nmdb)
- [FHFA Enterprise Public Use Database](https://www.fhfa.gov/data/pudb), [2025 data dictionary](https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-data-dictionary.xlsx), and [2025 record-count workbook](https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-record-count.xlsx)
- [FHFA NMDB Aggregate Statistics Data Dictionary and Technical Notes, 26/06/2026](https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes-2026q1.pdf)
- [ICPSR/DataLumos NSMO V2 catalog record](https://www.datalumos.org/datalumos/project/219485/version/V2/view)
- [FFIEC/CFPB Dynamic National Loan-Level HMDA Dataset](https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset)
- [Ginnie Mae Disclosure Data Download](https://bulk.ginniemae.gov/)
- [Ginnie Mae Single-Family Loan-Level Terms of Use](https://tst.ginniemae.gov/investors/disclosures_and_reports/Pages/Single-Family-Loan-Level-Terms-of-Use.aspx)
- [Ginnie Mae Loan Performance File layouts](https://bulk.ginniemae.gov/LayoutsSamples/471/LoanPerf_layout.pdf), [annual layout](https://bulk.ginniemae.gov/LayoutsSamples/479/LoanPerfAnn_layout.pdf)

## Recheck 15/10/2026 — additional unrestricted loan-performance source

The current official Fannie Mae page confirms the 31/07/2026 release includes
primary acquisition/performance through Q1 2026, but its primary dataset is a
selected subset of fully documented conventional fixed-rate mortgages; it
excludes ARMs, government-insured loans, HARP from the primary file, certain
high-LTV/nonstandard loans, and other populations. Fannie requires account
registration, email confirmation, and acceptance of [Terms and Conditions](https://www.fanniemae.com/about-us/legal-disclosure). The
same page says its general site terms govern the content; those terms prohibit
automated scraping and use to train/test/benchmark AI applications absent
written authorization. The direct loan-level dataset itself additionally
restricts redistribution and external commercial use without written consent.
The page offers a sample CSV for schema setup, but it is still Fannie-hosted
content subject to those site terms; no sample or gated performance payload was
downloaded in this recheck. Do not treat a browser-visible link or a Data.gov
catalog entry as proof of unrestricted use.

The HUD Single-Family Portfolio Snapshot page describes monthly Excel records
with endorsement month, property/loan categories, ZIP, originating mortgagee,
interest rate and sponsorship fields, but no monthly payment-performance
history. The latest listed August 2026 workbook returned HTTP 403 via both the
web fetcher and direct HTTP with browser and research-client user agents. A
different official HUD ArcGIS source, FHA Insurance in Force by Tract, was
downloaded instead as a static aggregate exposure dataset; its unresolved
coverage-date and `-4` code caveats are documented in
`docs/HUD_FHA_IIF_TRACT_REVIEW_VI.md`.

This recheck did not locate a new unauthenticated, unrestricted loan-level
monthly performance panel with Freddie-compatible target semantics. The next
data-dependent step remains an authorized source: Freddie Clarity for the
target vintage schedule, or a separately authorized NSMO/Ginnie case after its
specific monitoring/Terms gate is satisfied.

## HUD FHA performance report recheck — 15/10/2026

The official [FHA Single-Family Loan Performance Trends](https://www.hud.gov/hud-partners/single-family-loan-performance)
index lists monthly reports through August 2026 and describes them as portfolio
performance reports. The August PDF (`FHALPT_AUG2026.pdf`) returned HTTP 403
from both the browser content fetcher and direct local HTTP request. No PDF was
downloaded or parsed. This is a separate FHA aggregate-report access issue; it
does not alter the prior finding that the FHA Portfolio Snapshot has no monthly
payment history, and it cannot stand in for Freddie loan-level vintages. The
unrestricted CFPB monthly delinquency CSVs have been acquired separately, with
NMDB/sample, suppression, imputation and revision caveats in
`docs/CFPB_MORTGAGE_PERFORMANCE_TRENDS_REVIEW_VI.md`.


## Recheck 15/10/2026 — HMDA scope and CFPB multi-product trend data

The bounded CFPB HMDA API was re-acquired for the existing Maryland home-purchase/site-built 2023–2025 scope. All three CSVs are byte/hash identical to the verified source received 09/10/2026, and yearly counts/amounts match; the recheck receipt is `artifacts/private/hmda-refresh-audit-13597103ed21/receipt.json`. No data revision was available in this scope, so the existing profiled canonical case remains the app source.

A separate CFPB Consumer Credit Trends source review found an official all-products CSV for mortgage, credit-card, auto, and student credit context. CFPB lists the dashboards as updated 17/09/2026 and describes the underlying inputs as a nationally representative sample from one nationwide credit bureau, with direct identifiers removed. The official `all_data.csv` URL returned HTTP 403 to standard Python and curl clients from this environment; no alternate identity or access workaround was used. This is aggregate market context, not individual loan performance, a borrower model-training file, or an independent panel. See `docs/CFPB_CONSUMER_CREDIT_TRENDS_REVIEW_VI.md`.
