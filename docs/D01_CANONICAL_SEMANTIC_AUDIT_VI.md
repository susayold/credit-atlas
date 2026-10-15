# D01 — truy vết semantics canonical Release 47

Checkpoint ngày 15/10/2026. Audit chạy trên canonical output của case
`d01-a24484b21a21`, tương ứng 50.000 khoản vay và 4.510.559 loan-months của
corpus 2012 được cung cấp. Đây là kiểm tra transformation và regression trên
corpus đã pin; không xác thực nguồn phát hành của publisher, publication date,
quyền sử dụng hay semantics của vintage khác.

## Kết quả nghiệm thu

| Contract | Đối chiếu thực hiện | Kết quả |
|---|---|---|
| Missing/sentinel theo từng field | 17 token-field pair: raw blank/token so với canonical null; raw được giữ lại | 17/17 khớp; không thay token toàn cục |
| Categorical domain | 20 enum fields so observed raw categories với allowlist code | Không có giá trị ngoài contract; category không xuất hiện trong sample không được xem là đã kiểm chứng |
| Delinquency và terminal axes | Tính lại độc lập từ raw code cho mọi loan-month | 4.510.559 rows, 0 differences |
| Month/date conversion | So sánh sáu date fields với parse `YYYYMM` về ngày đầu tháng | 0 differences |
| HARP segmentation | Tính lại indicator Y và subset có original LTV >80 từ raw | 0 differences; unknown LTV không bị suy đoán thành subset |
| Percentage-point numeric values | Raw-to-canonical exact cast cho MI%, CLTV, DTI, interest rate, LTV | 0 differences; không chia 100 hoặc scale ngầm |
| Age, event, loss boundaries | Existing pinned tests cover t+12/t+13, censoring/gap/unknown, exit precedence, negative loss, missing values and duplicate terminals | Relevant engine tests pass; đây là semantic/unit evidence, không phải model qualification |

## Missingness và sample findings

Null sentinel chỉ áp dụng tại field được quy định: FICO/VantageScore `9999`;
DTI/LTV/CLTV/MI/ELTV `999`; units/borrowers/property type `99`; categorical
`9`; property valuation và MI cancellation `7`; postal code `000`. Các giá trị
khác như zero DTI/MI, dollar amount 999, actual loss 0 hoặc -10 không bị loại
bằng quy tắc chung. Cả 17 mapping được kiểm tra trên canonical table; trong
sample này VantageScore và valuation method đều null cả 50.000 khoản, ELTV
null 2.657.933 loan-months, MI cancellation null 4.510.559 loan-months.

Observed percentage-point ranges là MI 0–42 (43.786 zero), CLTV 3–684, DTI
1–57, interest rate 2.25–5.875 và LTV 3–684. Audit chứng minh giá trị được
cast không đổi đơn vị; các maximum CLTV/LTV cao cần được đọc theo source
contract và kiểm tra riêng khi phân tích, không tự động clipping hoặc gọi là
domain lỗi chỉ vì vượt 100.

Delinquency `00/01/02/03–99/RA/XX` giữ nghĩa CURRENT/D1/D2/D3+/REO/UNKNOWN;
không đổi code thành số ngày quá hạn. Terminal codes `01`, `02/03/09`,
`15/16/96` lần lượt là prepaid-or-matured, credit termination, other
termination. Hai trục được lưu độc lập; whole-loan sale không mặc định thành
default. Codes không quan sát được trong sample, chẳng hạn `XX`, vẫn được
giữ theo contract nhưng chưa có raw edge row trong vintage này để kiểm nghiệm.

## Trace từ nguồn sang code và test

| Nguồn / ý nghĩa | Triển khai | Regression/evidence |
|---|---|---|
| July 2026 General User Guide Release 47, pp. 4–17; file layout | `vendor/credit_risk_strategy_lab/docs/data_dictionary/canonical.md`, `src/crsl/canonical.py`, `src/crsl/contracts.py` | Official public example/layout review in `docs/FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md`; sample/layout files không phải annual source |
| Token, enums, raw preservation, numeric casts | `SENTINELS`, `ENUMS`, `clean_expr`, `assert_source` | `vendor/credit_risk_strategy_lab/tests/test_contracts.py`, `test_canonical.py`; audit receipt below |
| Target horizon, observed exits, loss sign/coverage | `src/crsl/labels.py`, `src/crsl/losses.py` | `test_labels.py`, `test_losses.py`, `test_vintage.py`; broader suite recorded in implementation status |
| Actual case trace | D01 frozen canonical parquets and source-receipt-linked case | `artifacts/private/d01-canonical-semantics-e2fe2cdc8cbf/receipt.json` and `audit.json` |

## Kết luận và phần còn mở

M01-003 được xác nhận cho semantics/transformation hiện có trên supplied 2012
corpus. Không có sai lệch cần sửa trong canonical output. Cross-vintage
compatibility, range/domain review theo source vintage, publisher authentication,
rights, PIT qualification, multi-vintage label maturity và actual model study
vẫn mở; checkpoint này không nâng các gate R2/R3.
