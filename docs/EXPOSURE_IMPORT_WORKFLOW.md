# P4 — Typed exposure inventory và research EL

## 1. Mục đích và dữ liệu thật đã chạy

P4 nhận snapshot có schema rõ ràng, kiểm tra và đối chiếu số lượng/số dư,
phân nhóm concentration, rồi phục vụ aggregate trên UI/API. Không suy diễn
PD hoặc EAD từ tên cột score, loan amount hay outstanding principal.

Snapshot Freddie Mac 2012 sample tại **2026-03**, grain **month**, lấy từ
D01 `d01-a24484b21a21`, canonical `canonical-977e4d53f0d1`:

| Chỉ tiêu | Kết quả |
|---|---:|
| Loan-month source observations | 9.698 |
| Observations có UPB bằng 0 | 141 |
| Tổng reported UPB, USD | 915.208.989,12 |
| PD / LGD / EAD inputs | Không có |
| Research EL | Unavailable, không điền 0 |

Import receipt: `exposure-import-57b88e00bedb`.
Independent Fraction/SQL audit: `exposure-audit-230d6be37b3d`, **66 checks PASS**.
Đây là các observation còn xuất hiện trong sample ở tháng đó, không phải
danh mục tài sản thực sự sở hữu, toàn bộ cohort ban đầu hay borrower universe.
Pool key của adapter là sampling-cohort key, không phải securitization pool.
Không carry-forward các khoản không xuất hiện trong tháng. Không dùng HMDA
denial rate, SBA charge-off outcomes hay retail score làm PD cho mortgage.

## 2. Hợp đồng CSV

Header bắt buộc đúng thứ tự, không thêm cột:

```csv
position_id,pool_key,representation,as_of,currency,amount_unit,reported_amount,segment,region,source_state,pd,lgd,ead
```

| Field | Hợp đồng |
|---|---|
| position_id | Nonempty, unique trong snapshot; không chứng nhận borrower identity |
| pool_key | Key khai báo để kiểm tra overlap representation |
| representation | DIRECT_ASSET hoặc SECURITY_POSITION |
| as_of | Đồng nhất với metadata, ISO month hoặc day |
| currency | USD, EUR, GBP, VND hoặc TWD |
| amount_unit | major, thousand hoặc million; hệ số 1/1.000/1.000.000 |
| reported_amount | Decimal không âm, tối đa 24 digits integer và 18 fractional digits |
| segment / region / source_state | Nonempty, explicit source categories; không tự bổ sung missing bằng giả định |
| pd / lgd / ead | Để trống cả ba khi risk_contract null; nếu có contract thì bắt buộc đầy đủ |

Không nhận NaN, negative, scientific notation, duplicate IDs, mixed dates,
unknown currency/unit hoặc probability percentage 3 thay cho fraction 0.03.
CSV giới hạn 100 MiB và 500.000 rows. Decimal arithmetic precision 120,
lưu raw strings và converted exact strings; không round tiền về cent ngầm.
Mỗi currency có tổng riêng; global cross-currency total luôn null.
Zero balances vẫn giữ trong counts. Amount share null nếu denominator bằng 0.

Nếu cùng exact declared pool_key có cả DIRECT_ASSET và SECURITY_POSITION,
import bị reject. Guard này chỉ kiểm tra key khai báo; không tự phát hiện
quan hệ thực tế giữa các tài sản có khác key, chứng nhận ownership hoặc netting.

## 3. Metadata và giả định risk

JSON phải có đúng các keys: schema_version, dataset_kind, amount_kind,
as_of, date_grain, source_namespace, source_description, risk_contract,
source_lineage, visibility, public_release_approved.

- schema_version: 1; visibility: private; public_release_approved: false.
- dataset_kind: source_observation hoặc declared_portfolio.
- amount_kind: reported_outstanding_principal hoặc declared_position_amount.
- date_grain: month hoặc day, phù hợp as_of.
- source_lineage: list các object có path tương đối nằm trong project và sha256.
- risk_contract: null đối với snapshot thật hiện tại.

Muốn tính factorized research EL, dataset_kind phải là declared_portfolio;
risk_contract phải có đúng nội dung semantics dưới đây và horizon integer
1–1.200 months. Default definition cần viết rõ theo scenario:

```json
{
  "pd_semantics": "cumulative_default_probability",
  "lgd_semantics": "conditional_fraction_of_ead_on_default",
  "ead_semantics": "declared_exposure_at_default_major_currency",
  "basis": "declared_research_assumption",
  "default_definition": "Explicit scenario event definition",
  "horizon_months": 12
}
```

Mọi row phải DECLARED_PERFORMING, PD/LGD fractions trong [0,1], EAD không âm
và khai báo bằng major currency riêng, không scale theo amount_unit của
reported_amount. Công thức từng row: **PD × LGD × EAD**. Ví dụ giả định
PD 0,03, LGD 0,4 và EAD USD 1.250 cho EL USD 15, dù reported amount khác.
Đây là tính toán point assumptions; không coi tích các kỳ vọng riêng lẻ là
full stochastic expectation khi EAD/LGD/default có dependence chưa mô hình.

Basel mô tả các thành phần PD/LGD/EAD trong framework riêng; engine này không
chứng nhận IRB hoặc accounting ECL. Tham khảo primary source:
[BIS CRE35](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/35/inforce/2023-01-01/published/2020-03-27).
Monthly conditional hazard, denial probability, defaulted exposures và claims
validated_model bị reject; cần adapter/engine phù hợp trước khi hỗ trợ.

## 4. Chạy và kiểm tra lại

Chạy từ `local machine path omitted`, dùng Python trong .venv:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_mortgage_exposures.py --case d01-a24484b21a21 --month 2026-03
.\.venv\Scripts\python.exe -X utf8 scripts/import_exposures.py --csv private evidence omitted from public release --metadata private evidence omitted from public release
.\.venv\Scripts\python.exe -X utf8 scripts/import_exposures.py --verify exposure-import-57b88e00bedb
.\.venv\Scripts\python.exe -X utf8 scripts/audit_exposure_import.py --import-id exposure-import-57b88e00bedb
.\.venv\Scripts\python.exe -X utf8 scripts/browser_exposure_qa.py
.\scripts\test.ps1
```

Adapter tạo input mới; không overwrite receipt trước. Import gồm copied
source.csv/metadata.json, typed positions.parquet, report.json và completion
receipt có hashes của payload/methods. Verification đối chiếu schema, mọi row,
report rederived và upstream lineage. Independent audit dùng Fraction cho
unit conversion và EL, SQL đọc Parquet; đối chiếu currency/group counts,
exact amount và EL. Amount shares được primary verifier rederive; chưa có
separate Fraction share audit. Không chỉnh frozen import methods rồi sửa
receipt cũ để làm verification pass.

## 5. App/API và chức năng tiếp theo

URL: `http://127.0.0.1:8770/?view=exposure&exposure_import_id=exposure-import-57b88e00bedb`.
UI chọn import/currency/concentration dimension, đối chiếu reported amount,
hiển thị unavailable EL và private aggregate export. Source positions/raw
IDs/lineage paths không trả trong report API.

GET endpoints: /api/exposure-imports; /api/exposure-aggregates;
/api/exposure-report. Hai report endpoints chỉ nhận import_id/currency/dimension;
duplicate/unknown parameters bị reject, export giữ exact decimal strings.
Mỗi read kiểm tra hashes của frozen source/payload/upstream, kể cả khi sửa
file giữ nguyên timestamp. Intake hiện qua CLI, chưa có upload UI/API.

Snapshot tháng 02 và [movement bridge](EXPOSURE_MOVEMENT_WORKFLOW.md) tháng
02 → 03/2026 đã có ordered attribution/entries/exits/residual, source-bound
API/UI/private export. Tiếp tục P4: (1) thêm cash-flow evidence adapters;
(2) [scenario workbench](EXPOSURE_SCENARIO_WORKFLOW.md) đã có versioned
declared assumptions, clipping/eligibility/ordered EL attribution và exact
private export; calibrated risk/macro adapters còn thiếu;
(3) ECL engine sau khi có probability term structure, staging/SICR,
cash-flow/discount/recovery policies; (4) dependence/tail simulation và review.
FX, borrower linkage, ownership reconciliation và actual production PD
vẫn chưa qualified. Bank/country observatories là context riêng, chưa tự
biến macro/bank ratios thành PD của từng exposure.
