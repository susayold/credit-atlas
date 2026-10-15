# P3 — SEC Issuer Financial Statement Evidence

Ngày 09/10/2026. Mở `http://127.0.0.1:8770/?view=sec` hoặc **P3 · Issuer financials**.
Scope: source-native SEC facts, filing-specific USD fields/ratios, inspectable
period/concept evidence. Đây là nền cho credit memo; chưa phải issuer rating,
PD, complete financial-statement parser, covenant hoặc maturity system.

## 1. Nguồn đã tải và cách dùng

Official [SEC data API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
cung cấp companyfacts và submissions/history JSON không cần API key.
Requests sequential, khai báo `CreditAtlas/1.0 local financial research`,
minimum .35s giữa requests, không retry/bypass khi bị chặn.
[SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).

| Issuer | Explicit CIK | Source fact entries | Concepts | Unique filings |
|---|---|---:|---:|---:|
| AAPL | 0000320193 | 25.135 | 505 | 2.265 |
| MSFT | 0000789019 | 32.671 | 565 | 4.525 |
| Ford (F) | 0000037996 | 24.139 | 592 | 4.446 |
| GM | 0001467858 | 23.496 | 632 | 2.138 |

Four issuers là bounded initial source track, không phải representative
corporate-default population. Tech/automotive consolidated scope khác nhau;
captive finance subsidiaries làm sector comparisons cần đọc filing thực tế.
Companyfacts name khác submissions name ở một số issuer; CIK là identity,
không dùng fuzzy name join hoặc ghép sang SBA để tạo label.

API facts chỉ phản ánh whole-entity/non-custom concepts mà endpoint trả về,
không phải toàn bộ XBRL instance, custom tags, dimensions hoặc footnotes.
Không gọi API fact entries là từng doanh nghiệp độc lập.

## 2. Artifacts và kiểm chứng

Source `sec-source-13cf03606e0c`: **14 HTTP JSON files / 18.105.032 bytes**,
gồm 4 submissions, 6 older-history files và 4 companyfacts. Full source arrays,
additional-file manifests, URL/hash/bytes/retrieved time giữ private trên D:.

Canonical `sec-case-33077fe45722`:

- **105.441 fact entries**, exact values lưu numeric decimal strings; không
  ép các fact EUR/shares/pure/USD per share thành USD.
- **13.374 unique filings / 13.374 source occurrences**; recent và toàn bộ
  history files của bốn issuer đã đọc, accession prefix không cần là issuer CIK.
- **67 annual research statements**, chỉ source filings 10-K/10-K/A có report
  date và facts tương ứng. Mỗi statement giữ accession, filed date, report date
  và link SEC filing index.
- Các fact raw lặp/comparative khác filing/fiscal label giữ riêng; source
  ordinal chỉ nhận diện entry trong CIK/taxonomy/concept/unit array.

Independent audit `sec-audit-b3f7c79ffc11`: **PASS**, raw JSON ↔ Parquet
bidirectional SQL EXCEPT ALL **0 differing facts / 0 differing filings**.
**201 supported ratios** kiểm tra exact Decimal arithmetic (precision60);
**67 ratios unavailable** giữ NULL. Actual source quality: 0 unlinked facts,
0 fact-vs-manifest date/form mismatches, 0 filed-before-period-end facts.
Audit có `source-quality.ipynb` chứa SQL và code rerun; là companion chưa chạy
bằng một notebook kernel riêng. Receipt audit là evidence đã thực thi.

Verified view: `sec-view-b92d9914f1dc`. Canonical schema is verified alongside source rows. Snapshot and reports rederive từ canonical
và source; thay summaries/ratios rồi cập nhật digest không qua verifier.

## 3. Financial normalization contract

Giữ taxonomy, concept, unit, source ordinal, start/end, value_exact, accession,
source FY/FP/form/filed date/frame. FY/FP và frame là annotations nguồn,
không tự dùng thay period start/end. Parse số JSON decimal trực tiếp để giữ
precision; không convert qua binary float hoặc round trong storage.

Statement view hỗ trợ eight fields:
assets, liabilities, current assets, current liabilities, cash/equivalents,
revenue, net income và operating cashflow. Whitelist là us-gaap/USD;
unit khác vẫn nằm trong canonical facts nhưng không được FX-convert ở đây.

Instant fields yêu cầu end đúng filing report date và không start.
Duration fields yêu cầu cùng end và **330–400 inclusive days**; filter này
chỉ xác định annual candidates, không chứng minh complete accounting equivalence.
Candidates phải cùng accession/form/filed date. Không lấy comparative ở filing
mới hơn để âm thầm thay giá trị của filing được chọn.

Revenue candidates:
RevenueFromContractWithCustomerExcludingAssessedTax, SalesRevenueNet, Revenues.
Không chọn tag đầu tiên chỉ vì có dữ liệu. Nếu khác value hoặc start/end:
**ambiguous**. Nếu cùng exact value và period, giữ mọi evidence entry và chỉ
cho phép phép tính đó; vẫn ghi rõ concept candidates, không tạo universal taxonomy.

Các ratio:

| Ratio | Numerator / denominator | Gate |
|---|---|---|
| Current ratio | AssetsCurrent / LiabilitiesCurrent | Cùng instant date, denominator>0 |
| Liabilities/assets | Liabilities / Assets | Cùng instant date, denominator>0; không phải debt/assets |
| Net income margin | NetIncomeLoss / supported revenue | Cùng annual start/end, denominator>0 |
| Operating cashflow/revenue | CFO / supported revenue | Cùng annual start/end, denominator>0 |

Missing/ambiguous inputs, period mismatch và nonpositive denominator tạo
unavailable + reason. Không zero-fill, clip ratio, tính average của conflicts
hoặc silently substitute a different profit/debt concept.

Actual examples: Ford latest filing thiếu supported NetIncomeLoss candidate,
margin unavailable; GM latest filing có conflicting revenue candidates,
net-income/CFO margins unavailable. Source evidence vẫn hiển thị các con số.
Đây là coverage/semantic gaps, không phải bằng chứng issuer có default.

## 4. App, cutoff và export

Chọn issuer theo CIK, filing-date cutoff và annual accession. Default chọn
latest supported filing **within cutoff**. Explicit accession khác issuer
hoặc sau cutoff bị từ chối. Nếu không có filing đủ điều kiện, không fallback
đến tương lai. Mỗi issuer có fiscal calendar riêng.

Đây là filter trên current API snapshot, **không phải PIT qualification**:
SEC corrections/deletions/API aggregation chưa được chứng minh reconstruct
đúng lịch sử available-at. Filing date cũng không thay acceptance/publication
timezone. API facts không cung cấp historical signed source snapshot tại mọi cutoff.

UI hiển thị exact USD fields, ratio statuses, source period, selected filing
index và expandable candidate evidence. Display ratios/currency có làm tròn;
private JSON export giữ exact numeric strings và mọi selected candidate.

Routes: `/api/sec-views`, `/api/sec-view?view_id=...`,
`/api/sec-report?view_id=...&cik=0000320193&asof=2026-10-09&accession=...`.
Filters bounded/known, duplicate query và cross-origin/Host bị chặn; no-store,
CSP và private export. Không phục vụ raw directory; public_release_approved=false.

## 5. Acceptance

**732 software tests PASS** (375 engine + 357 application), 132,86 giây.
Actual browser **10 checks PASS**, `sec-browser-qa-a44fd5141a8a`:
source counts/AAPL period and ratio, cutoff and export parity, no future
fallback, actual Ford missing tag/GM conflicting revenue, URL persistence,
390px mobile, independent P2/P3/P4 contexts, no mortgage-run dependency và
zero JavaScript/console errors. Desktop/mobile screenshots inspected.
Live HTTP report verified for GM: revenue ambiguous, net margin NULL,
historical availability qualified=false.

Tests include exact sub-18-decimal precision, repeated candidate retention,
conflicting concepts/periods, nonpositive denominators, units/annual cutoff,
forged ratios/snapshot/raw bytes, changed Parquet schema even with updated
digest, unaligned filing arrays, invalid download paths, duplicate/unknown
filters và origin guard. No actual risk-model fitting/selection/final scoring.

Source bytes remain the original immutable acquisition. Initial case/view/audit
were retained as historical artifacts after adding schema verification; the
current IDs above were rebuilt and verified with the strengthened methods.

## 6. Rerun và phần còn thiếu

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/acquire_sec_source.py
.\.venv\Scripts\python.exe -X utf8 scripts/prepare_sec_financials.py --source sec-source-13cf03606e0c
.\.venv\Scripts\python.exe -X utf8 scripts/audit_sec_financials.py --case sec-case-33077fe45722
.\.venv\Scripts\python.exe -X utf8 scripts/build_sec_view.py --case sec-case-33077fe45722
.\.venv\Scripts\python.exe -X utf8 scripts/browser_sec_qa.py
.\scripts\test.ps1
.\scripts\run.ps1
```

Next: raw filing/custom-dimension parsing; issuer/concept-specific mappings
reviewed explicitly; full debt/maturity/covenant terms; source-backed memo
narrative and findings/review/version exports. Default labels/model/economic
policy/production qualification chưa có từ nguồn này. Original 50-function
scope tiếp tục trong [PLAN_FIVE_WORKSPACES.md](PLAN_FIVE_WORKSPACES.md).
