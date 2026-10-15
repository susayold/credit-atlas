# P3 Business credit — SBA FOIA canonical và descriptive marts

Ngày: 09/10/2026. Actual case: `business-sba-21c568f10f7d`.
Status: `SBA_SOURCE_RECORD_DESCRIPTIVE_PREPARED`. Chưa fit model và chưa
qualified fixed-horizon default target. Còn Polish ratio benchmark, SEC issuer
facts/memo và các workflow nghiệp vụ khác theo kế hoạch P3.

## 1. Nguồn, snapshot và phạm vi

Nguồn chính thức: [SBA 7(a) & 504 FOIA](https://data.sba.gov/dataset/7a-504-foia).
Batch `suite-619b1ee9aa8c` giữ sáu CSV as-of **2026-06-30** và dictionary XLSX.
Rights theo source: U.S. Government Works. Raw được giữ private trên D:.

| Chương trình | File segment | Source records |
|---|---|---:|
| 7(a) | FY1991–FY1999 | 337.033 |
| 7(a) | FY2000–FY2009 | 690.333 |
| 7(a) | FY2010–FY2019 | 545.751 |
| 7(a) | FY2020–Present | 388.338 |
| 504 | FY1991–FY2009 | 111.066 |
| 504 | FY2010–Present | 117.983 |
| Tổng source records | Sáu segments | **2.190.504** |

Năm tài khóa SBA theo tháng 10–tháng 9, dùng năm kết thúc;
[SBA loan program performance](https://legacy.sba.gov/document/report-small-business-administration-loan-program-performance)
mô tả quy ước này và approval dollar amounts. ApprovalFY của toàn bộ records
khớp quy tắc ngày này. FY2026 trong snapshot tháng 6 là năm chưa hoàn tất.
Ngày snapshot/extraction không chứng minh publication-time availability của
các features tại ngày approval trong quá khứ.

## 2. Dictionary đã đọc và lưu bằng chứng

Workbook gốc có hai sheets: `7(a) Data Dictionary` với **42 fields**, và
`504 Data Dictionary` với **39 fields**. Parser resolve workbook relationships
theo tên sheet; giữ field/definition và tọa độ cell. Styled blank cells được
bỏ qua; không sửa hoặc xuất lại workbook. Dictionary text trong `dictionary.json`
khớp chính xác thứ tự headers của sáu CSV.

Các định nghĩa cần giữ đúng:

| Field | 7(a) | 504 |
|---|---|---|
| LocationID | Mã lender của SBA | Mã lender của SBA |
| GrossApproval | Tổng khoản vay | Phần khoản vay SBA/CDC |
| SBAGuaranteedApproval | Phần SBA guaranty | Không có field này |
| ThirdPartyDollars | Không có field này | Phần third-party loan |
| GrossChargeOffAmount | Balance charged off gồm guaranteed và non-guaranteed | SBA/CDC balance charged off |
| BankName / CDC_Name | Lender hiện được assigned | CDC hiện được assigned |
| JobsSupported | Jobs created + retained do lender tự khai, SBA không audit/validate | Cùng giới hạn |

Không dùng `LocationID` làm loan key, không cộng hai chương trình như thể
approval amounts có cùng full-facility scope. Current assigned lender không
tự động là lender-at-origination feature cho approval-time backtest.

## 3. Grain và record keys

Nguồn không phát hành unique loan/entity ID trong schema hiện tại. Canonical
grain là **source CSV record**, không khẳng định số unique borrowers/loans.
Private record key = source ID + ordinal của data row, gắn với source SHA-256
trong receipt. CSV reader tắt parallel để giữ thứ tự input.

Có **1.987 excess rows** trong các nhóm trùng hoàn toàn theo toàn bộ source
fields. Adapter giữ đủ records và báo count; không tự xóa vì các khoản vay
khác nhau có thể có cùng toàn bộ released fields. Không fuzzy-match borrower
names với SEC hoặc coi lender ID là entity ID. Canonical không mang borrower
name, street, ZIP hoặc lender address; raw vẫn giữ nguyên private để audit.

## 4. Status contract

| Source code | Canonical status | Ý nghĩa dùng được |
|---|---|---|
| CANCLD | cancelled | Cancelled, không tự coi là default/non-default |
| CHGOFF | charged_off | Source current charge-off status |
| COMMIT (7a) / NOT FUNDED (504) | undisbursed | Undisbursed |
| EXEMPT | disbursed_status_withheld | Disbursed status exempt from disclosure theo FOIA Exemption 4 |
| P I F (7a) / PIF | paid_in_full | Paid in full |
| CLOSED (504) | closed_other_legacy | Closed ngoài cancelled/PIF/charge-off; legacy code |
| Code chưa biết | unmapped | Giữ và flag, không mặc định negative |

Raw spelling được giữ trong `status_raw`; Program ` 7A` được trim thành `7A`.
`EXEMPT` không được đổi thành performing/non-default label. `CLOSED` không
được gộp vào PIF. Snapshot status shares không là PD 12 tháng hoặc survival
estimate; cohort ages khác nhau, outcome reporting và identifiers chưa đáp
ứng study/model protocol.

## 5. Types, missingness và precision

Source dates chuyển thành DATE, money thành **DECIMAL(38,18)**; ApprovalFY,
TermInMonths và JobsSupported thành integer nếu không mất precision. Empty
source values thành nullable typed values; không điền zero cho absent fields.
Guaranty amount của 504 và third-party amount của 7(a) là not-applicable NULL.

**980 records** có source monetary values nhỏ hơn độ chính xác cent, chủ yếu
các decimal artifacts trong guaranty/charge-off amounts. Adapter giữ precision,
flag fractional-cent values và không silently round/clip. Ví dụ nguồn có
`203325.03999999998`; stored Decimal giữ đúng số này. Các scientific values
như `1.196E7` được đối chiếu với Python Decimal để chứng minh conversion exact.
Nonempty malformed values, fractional integer, unsupported precision hoặc
non-ISO date sẽ fail trước complete receipt thay vì biến thành NULL/zero.

Các sums trong aggregate JSON là decimal strings để giữ exactness. Display
có thể format cents, nhưng formatting không thay số underlying. Approval sums
bao gồm cancelled/undisbursed source records và không được gọi là funded
balance hoặc current EAD. Charge-off/approval ratio chưa được dùng làm LGD.

## 6. Quality findings thực tế

Các count dưới đây là cờ theo record, có thể overlap; không cộng chúng thành
số unique problematic loans. Không sửa source dates hoặc clip amounts.

| Check | Records |
|---|---:|
| Status chưa mapping | 0 |
| Thiếu approval date hoặc ApprovalFY | 0 |
| ApprovalFY không khớp ngày approval | 0 |
| Một event date sau snapshot | 33 |
| First disbursement trước approval | 944 |
| Charge-off hoặc payoff trước approval | 6 |
| CHGOFF thiếu ChargeOffDate | 58 |
| Status khác CHGOFF nhưng có ChargeOffDate | 0 |
| Negative approval hoặc charge-off amount | 1 |
| Reported charge-off lớn hơn reported approval | 6.984 |
| Excess rows trong nhóm source duplicate hoàn toàn | 1.987 |

These flags không được diễn giải thành fraud hoặc error xác định khi chưa
review source rules/revisions. Chúng làm rõ vì sao chưa fit fixed-horizon
default/LGD model trực tiếp từ snapshot. `quality.json` giữ counts từng segment
và từng field, bao gồm blank, precision và scientific-conversion checks.

## 7. Marts và đối chiếu

Đã tạo sáu typed Parquet files cùng bốn aggregate views:

- Program × status: **11 cells**.
- Program × approval fiscal year × status: **317 cells**.
- Program × project state × status: **603 cells**.
- Program × NAICS two-digit × status: **266 cells**.

Mỗi dimension cộng về 2.190.504 source records. NAICS thiếu/không phù hợp giữ
bucket `__unavailable__`, không suy ngành từ tên borrower. Monetary sums và
known-value counts được ghi rõ để missing không trộn với zero.

| Status | 7(a) records | 504 records |
|---|---:|---:|
| Cancelled | 242.790 | 32.314 |
| Charged off | 220.688 | 12.169 |
| Disbursed status withheld | 297.494 | 61.266 |
| Paid in full | 1.179.360 | 114.445 |
| Undisbursed | 21.123 | 8.516 |
| Closed other legacy | Không có | 339 |
| Tổng | **1.961.455** | **229.049** |

Saved facts đối chiếu độc lập với raw CSV bằng bidirectional SQL EXCEPT ALL
cho program/raw-status record counts, **tất cả money sums và known-value
counts** theo field tương ứng chương trình: **zero differing groups** cho cả
sáu nguồn. Source record keys unique trong/between source segments, snapshot
và Program counts đối chiếu, raw input hashes reverify trước completion.

`verify_sba` kiểm tra method hash, acquisition/dictionary lineage, output hashes,
metadata row counts, full expected source set, contract và aggregate denominators.
Actual verifier đã PASS trên case hiện tại. **536 tests pass** (375 engine,
161 application), trong đó 10 tests mới cover dictionary relationships,
status meanings, Decimal/scientific conversion, duplicate preservation,
not-applicable amount components, verifier tampering và failure-before-complete.

## 8. Commands và phần còn lại của P3

Từ `local machine path omitted`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_sba.py --suite suite-619b1ee9aa8c
.\scripts\test.ps1
```

Case hiện tại và receipts trong
`private evidence omitted from public release`. Các failed parse attempts và
case method cũ được giữ làm historical evidence, không gọi là current verified
case. Không cần đăng nhập Clarity cho nguồn SBA này.

Descriptive marts/quality đã tích hợp P3 UI và scoped aggregate report; xem
[BUSINESS_APP_WORKFLOW.md](BUSINESS_APP_WORKFLOW.md).
Tiếp theo: source-specific Polish horizon/ratio adapter; SEC issuer identity, filing
period/units và credit memo. Approval-time SBA model cần entity/grain,
historical availability, outcome timing/exclusions, supported labels và
independent validation protocol trước fit. Covenant/debt/pricing workflows
cần thêm facility terms hoặc scenarios gắn nhãn assumptions.
