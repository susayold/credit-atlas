# FHFA House Price Index theo bang — source review

Rà soát và snapshot tải ngày 16/10/2026. Nguồn này bổ sung bối cảnh giá nhà
theo địa lý cho mortgage-risk monitoring; nó không thay thế loan-level collateral
value, valuation, AVM hay target credit risk.

## Đã tải

| Asset | Ý nghĩa | Đường dẫn nguồn chính thức |
|---|---|---|
| `hpi_at_state.csv` | FHFA All-Transactions HPI, state/DC, quarterly, not seasonally adjusted | [FHFA state HPI CSV](https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv) |
| `hpi_dictionary.xlsx` | Từ điển 12 trường cho master HPI schema | [FHFA dictionary](https://www.fhfa.gov/document/d/hpi/hpi_dictionary.xlsx) |
| `hpi_specifications.xlsx` | Layout từng file download; xác nhận state All-Transactions là 4 cột không header | [FHFA specifications](https://www.fhfa.gov/document/d/hpi/hpi_specifications.xlsx) |

Raw files và receipt SHA-256 được giữ ở `D:\data\Codex\credit-atlas\data\private\fhfa-hpi\source\`.
Public normalized table `docs/data/fhfa-state-all-transactions-hpi-quarterly-2026q2.csv`
thêm column names và không thay đổi data values.

## Scope và kết quả kiểm tra

FHFA mô tả HPI là thước đo chuyển động giá nhà đơn gia đình dựa trên phương
pháp repeat-sales weighted. `All-Transactions` bổ sung appraisals vào sales
prices; series theo state ở file này là **không điều chỉnh mùa vụ**, với base
1980Q1=100 theo specification. Không đọc index level như median dollar price.

Tại snapshot hiện tại có 10.506 quarterly rows, 51 geography codes (50 bang và
DC), balanced từ 1975Q1 đến 2026Q2: 206 quý cho mỗi geography. Không có key
trùng, thiếu kỳ, giá trị rỗng hoặc non-positive index. Quarterly state CSV gốc
không có header và mỗi dòng có bốn giá trị: state postal code, year, quarter,
index NSA. `scripts/ingest_fhfa_state_hpi.py` kiểm tra contract rồi tạo CSV có
header; synthetic contract tests kiểm tra duplicates, missing periods, mã địa
lý và giá trị không hợp lệ.

## Credit-risk use và giới hạn

Phù hợp cho portfolio-level collateral-market context: state HPI quarterly
change, YoY change, multi-year appreciation/decline, state-cycle comparison, và
cohort breakdown nếu case có geography hợp lệ. Có thể contextualize severity,
recovery/collateral cycles, nhưng không thể tính LTV hay property value từ HPI
chung.

Snapshot hiện hành là retrospective revised series, không cung cấp các release
vintages lịch sử. Không đưa nó làm predictor as-of-feature cho loan-level model
trước khi xác định ngày publish/availability, release revision policy, geography
mapping, observation lag và leakage treatment. Không join state index vào loan
records nếu source loan không có state ở grain phù hợp. HPI không đo borrower
payment behavior, delinquency, default hoặc loss ở từng loan.

FHFA cũng công bố Purchase-Only, Expanded-Data, metropolitan, county, ZIP và
census-tract families. Chưa tải các geography micro-level hoặc developmental
variants: bắt đầu với state All-Transactions để giữ scope, tránh trộn index
family/base/geography. Nếu D01/02 cần map chi tiết hơn, trước tiên kiểm tra
license/terms, geography vintage, small-area release noise và khả năng merge
với source loan; county/ZIP/tract coverage không tự động bằng nhau.

## Vai trò trong plan

Đánh dấu FHFA HPI source task S26 là **public state-level reference acquired**,
nhưng integration vào D01 macro features vẫn chưa được qualify. Hiện tại chỉ
được dùng trong descriptive/context workbook và portfolio-level analysis sau
khi nguồn mortgage cung cấp denominator/geography tương thích. Nó không làm
tăng Freddie vintage count hay D01 model-ready support.
