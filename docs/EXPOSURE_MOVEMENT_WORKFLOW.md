# P4 — Observation movement bridge

## Kết quả thật và ý nghĩa

Bridge `exposure-movement-dbd1ecad612e` nối hai snapshot cùng Freddie Mac 2012
sample, cùng D01 case `d01-a24484b21a21`. Receipt/payload/source/methods được
pin hashes; verification rederive từ CSV gốc của cả hai typed imports.

| Chỉ tiêu | Tháng 02 → 03/2026 |
|---|---:|
| Opening import | exposure-import-facfbef3f419 |
| Closing import | exposure-import-57b88e00bedb |
| Opening observations | 9.804 |
| Closing observations | 9.698 |
| Matched same-currency positions | 9.698 |
| Opening-only observations | 106 |
| Closing-only observations | 0 |
| Currency migration | 0 |
| Opening reported UPB, USD | 928.246.113,34 |
| Removed opening UPB, USD | 0,00 |
| Continuing observed UPB change, USD | −13.037.124,22 |
| Added closing UPB, USD | 0,00 |
| Closing reported UPB, USD | 915.208.989,12 |
| Reconciliation residual, USD | 0,00 |

Cả 106 opening-only records có opening UPB bằng 0. Không suy diễn payoff,
default hoặc charge-off từ việc không còn xuất hiện. Continuing change
chưa có cash-flow evidence để tách principal payments, interest, charge-offs,
source corrections hoặc các nguyên nhân khác. Sample không chứng nhận
owned portfolio hay borrower concentration. Đây là observed movement,
không phải ECL movement, P&L hoặc default forecast.

Independent original-CSV/Fraction audit:
`exposure-movement-audit-a691cd413f63`, **500 checks PASS**. Audit kiểm tra
exact native-currency totals, mọi bucket, counts, identity partitions,
transition counts/amounts, group keyset và residual. Separate tests inject
incorrect aggregate để chứng minh audit phát hiện lỗi ngoài primary verifier.

Verification checkpoint: 15 focused tests PASS; toàn suite **950 tests PASS**
trong 167,76 giây; actual inventory/bridge browser **8 checks PASS**
`exposure-browser-qa-2aca99dbf228`. Kiểm tra desktop/mobile 390px, exact export,
scope/reload, invalid import và observed state transitions. Live server 8770
đã restart; actual bridge/report endpoints có JSON parity.

## Identity/scope và thứ tự attribution

Trước khi ghép, source_namespace, dataset_kind, amount_kind và date_grain
phải bằng nhau, opening as_of phải trước closing as_of. Position IDs unique
trong từng snapshot. Matched position thay pool_key hoặc representation bị
reject, cần identity adapter riêng. Different segment/region/source_state
được xử lý thành bucket transitions; units được normalize từ typed input.
Exact ID là declared continuity contract, không chứng nhận borrower identity.

Mỗi currency và mỗi bucket có các bước disjoint theo thứ tự:

1. **Remove:** bỏ opening-only và currency-migration-out theo opening amount.
2. **Amount change:** với matched same-currency positions, áp delta vào opening bucket.
3. **Transfer:** nếu đổi bucket, transfer **closing amount** từ old sang new bucket.
4. **Add:** cộng closing-only và currency-migration-in theo closing amount.
5. **Residual:** closing − kết quả bốn bước; giữ riêng, không redistribute.

Ví dụ một khoản ở bucket A có opening 100 và closing 80 ở B: amount change
−20 ở A, transfer-out 80 ở A, transfer-in 80 ở B. Không transfer 100 rồi
tiếp tục trừ 20 ở A vì sẽ sai bucket attribution. Từng dimension là một
view khác nhau; không cộng các dimension với nhau.

Currency migration giữ exact identity pair nhưng removal/addition ở từng
native currency, không tính FX gain/loss. Removed/added counts có thể gồm
migration; hai trường migration-in/out riêng giải thích. Whole-pair identity
counts không bị lọc currency; API ghi rõ scope. Không có cross-currency total.

Zero balances vẫn là positions và vẫn có thể đổi trạng thái; không tự xóa.
Numeric arithmetic dùng Decimal precision 120 với exact string output;
independent audit dùng Fraction và source CSV raw amounts/units.

## Chạy lại và app

Từ `D:\data\Codex\credit-atlas`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_mortgage_exposures.py --case d01-a24484b21a21 --month 2026-02
.\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_movement.py --opening exposure-import-facfbef3f419 --closing exposure-import-57b88e00bedb
.\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_movement.py --verify exposure-movement-dbd1ecad612e
.\.venv\Scripts\python.exe -X utf8 scripts/audit_exposure_movement.py --movement-id exposure-movement-dbd1ecad612e
.\.venv\Scripts\python.exe -X utf8 scripts/browser_exposure_qa.py
.\scripts\test.ps1
```

Commands build/create immutable receipts mới, không overwrite receipts cũ.
Page `?view=exposure&exposure_import_id=exposure-import-57b88e00bedb` có bridge
panel, bucket reconciliation, observed transitions và private JSON export.
Confirmed exposure currency/dimension cũng lọc bridge; pair selector chỉ
liệt kê các bridge có đúng closing import. Nếu nhiều pairs, mặc định pair
receipt mới nhất; pair selection hiện chưa được lưu vào URL. Không áp
currency filter để thay đổi whole-pair identities.

API GET `/api/exposure-movements?closing_import_id=...`;
`/api/exposure-movement` và `/api/exposure-movement-report` cần movement_id,
closing_import_id; optional currency/dimension. Sai binding, duplicate/unknown
parameters hoặc currencies/dimensions không hỗ trợ bị reject. Report không
phục vụ raw positions/private source paths. Cached reads kiểm tra toàn bộ
source/payload/receipt hashes kể cả thay bytes giữ nguyên timestamp.

Tiếp tục: cash-flow source adapters để phân rã change nếu có bằng chứng;
[versioned declared scenario workbench](EXPOSURE_SCENARIO_WORKFLOW.md) đã có;
calibrated source-compatible risk adapters và EL/staging movement khi có risk contracts
phù hợp; exceptions/review package. Không mở lại các frozen final holdouts
hoặc tự mượn PD giữa các datasets khác cohort/horizon/target.
