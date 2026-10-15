# P5 — Market Context & Bond Scenario Lab

09/10/2026. Current case `market-case-1f4a60893d6c`, snapshot
`market-view-171f41206767`; source batch `suite-619b1ee9aa8c`.
Đây là market-context/assumed-bond slice, chưa là actual ABS/deal/CDS system.

## Dữ liệu thật và units

**46.675 source-native observations**, **2.684 monthly summary rows**,
**16.908 aligned native dates**. Các series giữ riêng native frequency:

| Series | Native rows | Source known | Source missing | Quarantined | Usable |
|---|---:|---:|---:|---:|---:|
| DGS2 | 13.136 | 12.584 | 552 | 0 | 12.584 |
| DGS10 | 16.896 | 16.176 | 720 | 0 | 16.176 |
| DGS30 | 12.951 | 12.406 | 545 | 994 | 11.412 |
| BAMLC0A0CM | 794 | 785 | 9 | 0 | 785 |
| MORTGAGE30US | 2.898 | 2.898 | 0 | 0 | 2.898 |

Tất cả source values có unit percent. Percent ↔ basis points: nhân 100;
percent ↔ annual decimal: chia 100. Monetary bond face/price là USD riêng,
không đồng nhất với units của market observations.

Daily alignment ghép **đúng cùng native date** DGS2/DGS10/DGS30/OAS, không
forward-fill/interpolate. Weekly mortgage data giữ nguyên các ngày nguồn,
không resample thành daily. Sau quarantine có **11.412 ngày usable đủ ba kỳ
hạn**, **747 ngày đủ ba kỳ hạn + OAS**. Month summaries dùng available native
observations, không assert complete calendar months/historical publication.

Current frozen raw: Treasury tới 2026-10-06, OAS tới 2026-10-07, mortgage tới
2026-10-08. Không thay ngày của từng source thành cùng một ngày cập nhật.
Latest common Treasury: 2026-10-06, 2Y/10Y/30Y = 4,79/5,27/5,64 (%),
10Y−2Y = 48bp, 30Y−10Y = 37bp. Đây là constant-maturity par-yield context,
chưa bootstrapped zero/discount curve hoặc actual security quotes.

Nguồn chính thức: [DGS2](https://fred.stlouisfed.org/series/DGS2),
[DGS10](https://fred.stlouisfed.org/series/DGS10),
[DGS30](https://fred.stlouisfed.org/series/DGS30),
[Treasury methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology),
[H.15 current release](https://www.federalreserve.gov/releases/h15/default.htm).
OAS là [investment-grade corporate index spread](https://fred.stlouisfed.org/series/BAMLC0A0CM),
không issuer/bond/CDS/deal quote; FRED notes giới hạn lịch sử ba năm từ tháng
4/2026 và có thể có month-end weekend observations. ICE data/derivatives chỉ
internal use, không external redistribution/publication approval.
[Mortgage source](https://fred.stlouisfed.org/series/MORTGAGE30US) có PMMS
methodology change ngày 2022-11-17; historical native dates giữ nguyên.

## Phát hiện source/documentation conflict

FRED DGS30 notes ghi discontinued 2002-02-18, reintroduced 2006-02-09. Nhưng
downloaded CSV có **994 nonmissing values trong interval đó**. Fresh HTTP query
`DGS30&cosd=2002-01-01&coed=2006-03-01` cũng trả lại 994 values. Notes page
download bằng HTTP vẫn chứa cùng discontinuation definition. Không kết luận
CSV là corrected historical series, không tự giải thích unknown provenance.

Evidence lưu ở `artifacts/private/market-source-audit-6f228267b689/`:
filtered CSV, downloaded notes HTML và hai immutable URL/time/bytes/SHA receipts.
Đây là **high-severity historical semantic risk**; cause chưa xác định.

Quarantine policy rõ ràng:

- Raw files giữ nguyên; canonical `source_value` và `source_value_percent` giữ
  original quotes, kể cả 994 disputed values.
- `documented_discontinuation_conflict=true` cho nonmissing DGS30 trong interval.
- `value_percent` usable = NULL cho flagged values; nguồn thiếu và quarantine
  có flags/counts riêng. Không biến conflict thành zero hoặc tự điền từ tenor khác.
- Aligned context giữ native-present/raw-value/quarantine flags; derived slopes
  và three-tenor coverage chỉ dùng usable values.
- Month summaries có source-missing/quarantine/known counts; unusable rates
  không vào min/max/mean/last usable values.
- Snapshot `historical_treasury_semantics_qualified=false`. UI có amber badge,
  source coverage columns, selected-range quarantine counts và per-row quality.
- Chart dùng calendar positions và usable values; không nối qua quarantined
  interval. Đây là **reviewed exclusion gap**, không claim original CSV tự thiếu.

Native CSV→Parquet independent SQL projection đối chiếu cả raw values và
reviewed exclusion policy: **0 differing rows cho cả năm series**; typed
roundtrip cũng 0. Điều này chứng minh faithful storage/policy, không chứng minh
entire source lịch sử đúng. Cần secondary primary-source historical release hoặc
upstream clarification trước khi qualified full historical 30Y semantics.

Historical cases/views trước quarantine giữ audit và hiện unavailable theo
current method digests. Browser failure khi đòi raw gap là bằng chứng phát hiện
conflict, không được xóa hoặc đổi thành PASS.

## Canonical outputs và API

Trong `artifacts/private/market-case-1f4a60893d6c/`:

- `native-observations.parquet`: series/date/raw-decimal/usable-decimal/raw-string/quality flag.
- `aligned-daily-context.parquet`: exact-date outer join, source presence/value,
  quarantine flags, usable rates/slopes/OAS bp và three-tenor support.
- `monthly-context.parquet`: counts, source missing/quarantine và usable summaries.
- `contract.json`, `run-start.json`, `market-complete.json`: meaning, rights,
  selected-source lineage, independent checks và method/output hashes.

Market-view builder lưu private snapshot, case-receipt hash, snapshot hash và
method hashes. Serving rechecks selected sources/canonical outputs/current
methods, không dùng stale fallback khi evidence thay đổi. Không phải hash lại
SBA/UCI ~1GB để đọc một market series; full batch đã verify khi intake, sau đó
case pin selected sources cùng acquisition receipt. Source paths không trong UI.

| Route | Contract |
|---|---|
| `/api/market-views` | Verified/unavailable catalog, không filters |
| `/api/market-view?view_id=…` | Whole-source profiles/coverage/contract |
| `/api/market-report?view_id=…&series=…&from=…&to=…` | One native series, ordered date range ≤3.666 days; private attachment |
| `/api/market-daily?view_id=…&from=…&to=…` | Same-date aligned context, bounded range, no fill |
| `/api/bond-scenario?view_id=…&face_usd=…&coupon_percent=…&yield_percent=…&years=…&frequency=…` | Exactly five supported assumed terms |
| `/api/bond-report?…` | Same scenario as private attachment |

Unknown/duplicate params, unsupported series/terms, malformed/reversed/excessive
ranges bị từ chối. Outside-source dates trả empty observations, không zero.
Loopback origin/Host/CSP/no-store guards áp dụng. All exports private.

## Bond conventions và numerical proof

Only regular fixed coupons, coupon-date settlement, zero accrued interest,
bullet principal, USD face; nominal annual flat assumed yield compounded at
frequency 1/2/4. Maturity phải whole coupon periods, 0,25–60 năm; face $0,01–
$1e12; coupon 0–100%, yield −20–100%. Unsupported stubs/calls/floating/default/
recovery/day-count settlement không silently approximate.

PV = sum discounted coupons + bullet. Modified duration/convexity dùng
analytical first/second derivatives; Macaulay duration và DV01 ghi units rõ.
Reprice shocks −100/−50/−1/0/+1/+50/+100bp và duration/convexity approximation
giữ riêng. ±1bp central differences kiểm tra sensitivities.

`bond-numerics-0fb948a7d272`: **180 assumed instruments PASS**, combinations
freq1/2/4 × maturity1/5/10/30 × coupon0/3/5 × yield−1/0/2/5/8.
Independent closed-form annuity+bullet reference; worst relative price error
**1,44e−14**, duration bump error **1,69e−6**, convexity bump error **8,98e−7**.
Coupon/principal cash sums và shock-price monotonicity pass. Đây là mathematical
acceptance, không security-market calibration.

Actual browser example: $100 face, coupon5%, yield7%, 10 years, semiannual:
price **85,787597**, modified duration **7,533961**, convexity **69,943607**,
DV01 **$0,064632**. Export có full assumed terms/conventions/schedule/shocks,
`market_calibrated=false`, `source_market_series_used_for_pricing=false`.

## App, commands và phần còn thiếu

http://127.0.0.1:8770/?view=market&market_view_id=market-view-171f41206767

Series/date explorer, native-date chart, source quality, last60-row preview,
full selected-series export, bond workbench và separate scenario export.
URL giữ market snapshot/date/series và bond terms. Không phụ thuộc mortgage
case/retail freeze; P2 controls/findings bị isolated. Chọn series không tự thay
date range đã chọn; range và last usable source dates hiển thị rõ.

Full software suite: **602 tests PASS** (375 engine + 227 application),
65,56 giây. Final browser `market-browser-qa-d459f030ced9`: **13 checks PASS**,
gồm computed SVG fill/stroke và calendar gap sau chart-style refinement. Kiểm tra
source counts/same-date Treasury, OAS Sunday2026-05-31, raw CSV/export parity,
assumed-bond independent price, quarantine/raw retention/calendar gap,
URL/mobile/no mortgage dependency/navigation và browser errors. Screenshots
đã xem gồm desktop/mobile, native context, bond và reviewed DGS30 gap.

```powershell
.\.venv\Scripts\python.exe scripts/prepare_market.py --suite suite-619b1ee9aa8c
.\.venv\Scripts\python.exe scripts/build_market_view.py --case market-case-1f4a60893d6c
.\.venv\Scripts\python.exe scripts/audit_bond_numerics.py
.\.venv\Scripts\python.exe -X utf8 scripts/browser_market_qa.py
.\scripts\test.ps1
```

Full P5 còn actual ABS-EE/Ginnie data/terms adapters, collateral schedules,
cash/loss projection, fee/interest/principal waterfall, triggers/tranche loss,
position comparison, deal surveillance/findings và CDS quotes/reference-pricer
calibration. Không thay các phần này bằng Treasury/OAS context hoặc assumed bond.
