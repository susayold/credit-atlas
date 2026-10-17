# CreditAtlas — phụ lục nghiên cứu quyền dữ liệu và kế hoạch N02/N03

Ngày rà soát: **18/10/2026 Asia/Bangkok**. Phụ lục này bổ sung cho [đánh giá hiện trạng và kế hoạch phát triển](PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md), dựa trên code checkout, source registry/crosswalk và điều khoản/trang nguồn chính thức được mở ngày 18/10. Đây là đánh giá kỹ thuật và kế hoạch kiểm soát nguồn; không phải ý kiến pháp lý hay bằng chứng đã được publisher cấp phép.

## 1. Trả lời về phạm vi đã rà soát

Đã có plan mới, chi tiết và có acceptance gates trong tài liệu chính, cùng phụ lục này. Tuy vậy, không nên nói đã đọc **từng dòng của toàn repo và từng raw row của mọi dataset**. Review là audit theo luồng nghiệp vụ và inventory: 27 dataset groups, 123 source records, 15 method cards, 50 capability rows; đã kiểm tra các source registries, acquisitions/receipts, route/service/UI/export chính và test families liên quan. Traceability report cũng nói rõ code review phần lớn static và raw rows không được đọc lại hết. Mọi số coverage/test phải hiểu đúng phạm vi stated trong receipt, không phải tổng nghiệm thu toàn hệ thống.

## 2. Phát hiện mới có ảnh hưởng trực tiếp đến app

### FRED/ALFRED: hiện trạng code

- `src/credit_atlas/public_sources.py` đăng ký bảy CSV endpoint `fredgraph.csv?id=...`: UNRATE, USSTHPI, MORTGAGE30US, DGS2, DGS10, DGS30 và BAMLC0A0CM; `acquire_public_suite` tải và lưu byte nguồn vào suite.
- `src/credit_atlas/market_data.py` nhận năm series DGS2/DGS10/DGS30/BAMLC0A0CM/MORTGAGE30US, lưu Parquet, ghép theo ngày gốc, tính slope và OAS summary. Chỉ DGS30 discontinuation interval được quarantine; mọi nguồn/output đang private và code tự đánh dấu chưa được phát hành.
- `src/credit_atlas/mortgage_macro_context.py` đọc UNRATE/USSTHPI/MORTGAGE30US để tạo macro context cho D01 và dùng bộ ALFRED vintage cho tính sẵn có theo thời điểm. API/UI có thể trả market observations và macro-context output; P5 được gắn nhãn nguồn FRED.
- Quyền hiện lưu trong `public_sources.catalog()` chưa phản ánh đủ yêu cầu chung của FRED và phân biệt chưa đầy đủ quyền của data owner với quyền truy cập qua distributor. `BAMLC0A0CM` đã được ghi internal-only, nhưng cần xác minh thêm cả quyền lưu/tính derived outputs; `MORTGAGE30US` được gắn copyright/citation; các chuỗi khác đang mô tả như public domain.

### Điều khoản chính thức cần thành gate

FRED API Terms nói rằng quyền truy cập qua FRED/ALFRED không ghi đè quyền của chủ sở hữu chuỗi; với chuỗi bên thứ ba, FRED yêu cầu người dùng liên hệ data owner trước khi dùng ngoài mục đích cá nhân. Nếu xây ứng dụng FRED API cho người khác, terms yêu cầu notice, liên kết terms và điều khoản dùng thể hiện người dùng đồng ý bị ràng buộc. Điều khoản dịch vụ FRED hiện cũng cấm lưu/cache/archive hoặc đưa FRED Content vào database/compilation/archive/cache; phần API bổ sung hạn chế dùng API để phát triển phần mềm/ML. Code hiện dùng `fredgraph.csv`, không dùng API endpoint `api.stlouisfed.org`, vì vậy cần xác nhận chính xác phạm vi điều khoản áp dụng cho từng route; không được giả định endpoint khác hostname/path tự động miễn khỏi điều khoản FRED Services. Cho đến khi được xác nhận, coi đây là **rights gate**, không phải chỉ thiếu attribution.

FRED ghi rõ series owner/restrictions riêng. Các điểm cần lưu:

| Chuỗi | Chủ dữ liệu / nguồn trực tiếp khả thi | Hướng sử dụng trong CreditAtlas | Gate cần đóng |
|---|---|---|---|
| UNRATE | BLS; BLS Public Data API là candidate trực tiếp. FRED tag/citation yêu cầu ghi nguồn. | P2/P4 macro context; không phải borrower-level PD. | Chuyển adapter sang BLS nếu định nghĩa, seasonal adjustment, kỳ và giá trị khớp; ghi attribution, lịch release/revision và quyền lưu snapshot. Không lấy revised series để dựng vintage lịch sử. |
| USSTHPI | FHFA; FHFA HPI có file tải chính thức và FAQ cho phép dùng miễn phí với attribution. | P2 home-price context. | Dùng đúng product (all-transactions/purchase-only, SA/NSA, geography, base), định nghĩa và kỳ. Cần đối soát series/units/vintages; direct current file không tự tạo as-of history. |
| MORTGAGE30US | Freddie Mac; trang FRED đánh dấu copyright, “reprinted with permission”. Freddie có PMMS archive/consolidated CSV. | P2 mortgage-rate context, P5 market context. | Đọc dataset/website terms và PMMS-specific notices trước automation/retention. Giữ discontinuity phương pháp ngày 17/11/2022; parity phải so từng release/date, không chỉ so latest. Freddie website terms hạn chế scraping/archiving trừ khi được cho phép bằng văn bản; không tự động chuyển crawler sang endpoint direct khi chưa xác nhận. |
| DGS2 / DGS10 / DGS30 | Federal Reserve Board H.15 công bố dữ liệu Treasury constant maturities; U.S. Treasury có Daily Treasury Par Yield Curve download/archive trực tiếp. | P5 descriptive rate/slope context. | Chuyển thử sang Treasury direct dataset hoặc Board route được phép; chứng minh series definition, observation date, value, historical revision behavior và overlap parity. Giữ DGS30 break 18/02/2002–08/02/2006 quarantine cho tới khi direct-source evidence giải quyết rõ. |
| BAMLC0A0CM | ICE Data Indices; FRED series notice nói Top Level Data internal-use only, không publish/distribute/furnish cho bên thứ ba nếu chưa có chấp thuận bằng văn bản. | OAS market context hiện là series P5 thứ tư; không phải issuer/deal quote. | Tắt acquisition/public-software path và không xuất/publish value/derived OAS trước khi có giấy phép phù hợp. Có thể bỏ series khỏi public demo; nếu giữ locally, phải xác định chính xác “internal use” áp dụng cho người dùng/tổ chức này và phạm vi derived outputs. |
| ALFRED UNRATE / USSTHPI / MORTGAGE30US vintages | ALFRED distributor; quyền từng vintage phụ thuộc chủ dữ liệu tương ứng và điều khoản FRED. | D01 historical availability/macro as-of; chống look-ahead. | Không dùng latest revised FRED series thay cho historical vintage. Tạm giữ dưới rights gate; chỉ dùng publisher archive/vintage có quyền lưu rõ ràng hoặc permission cụ thể. Nếu không có, D01 macro feature phải unavailable và phân tích giữ giới hạn. |

Nguồn chính thức được đọc: [FRED API Terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html), [FRED Services Terms](https://fred.stlouisfed.org/legal/fraud-awareness), [series UNRATE](https://fred.stlouisfed.org/series/UNRATE), [USSTHPI](https://fred.stlouisfed.org/series/USSTHPI), [MORTGAGE30US](https://fred.stlouisfed.org/series/MORTGAGE30US), [DGS2](https://fred.stlouisfed.org/series/DGS2), [DGS10](https://fred.stlouisfed.org/series/DGS10), [DGS30](https://fred.stlouisfed.org/series/DGS30), [BAMLC0A0CM](https://fred.stlouisfed.org/series/BAMLC0A0CM), [BLS API](https://www.bls.gov/developers/), [FHFA HPI datasets](https://www.fhfa.gov/data/hpi/datasets), [FHFA HPI FAQ](https://www.fhfa.gov/faqs/hpi), [Board H.15 download](https://www.federalreserve.gov/datadownload/Choose.aspx?rel=H15), [U.S. Treasury daily rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?page=0&type=daily_treasury_yield_curve), [Treasury rate archives](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives), [Freddie PMMS archive](https://www.freddiemac.com/pmms/pmms_archives), [Freddie Terms of Use](https://www.freddiemac.com/terms).

## 3. Kết luận thực tế: quyền truy cập, quyền cache và quyền dùng là ba việc khác nhau

HTTP 200 hoặc file local có receipt/hash chỉ chứng minh bytes đã tải/được giữ nguyên; nó không chứng minh rằng việc tải tự động, archive, đưa vào app, tính derived metrics hay phân phối cho người dùng là được phép. Tương tự, “public domain” của underlying BLS/FHFA/Fed data không mặc nhiên giải quyết mọi điều kiện của FRED intermediary, trademark/attribution, third-party data hoặc lịch sử vintage.

Vì FRED terms cần được giải thích theo endpoint và cách sử dụng thực tế, bước an toàn về kỹ thuật là giữ các receipt cũ làm provenance nội bộ, không chạy lại FRED acquisition trong workflow mới và chưa tạo bản phát hành công khai từ các series bị gate. Cần inventory nơi nào UI/API/export đang phục vụ dữ liệu đó; khi chuyển direct source hoặc có văn bản xác nhận, chỉ mở lại sau khi rights decision được ghi theo từng series và use case. Không được xóa/ghi đè receipt cũ để che lịch sử acquisition.

## 4. Plan N02/N03 cập nhật, có đầu ra nghiệm thu

| Ưu tiên | Thực hiện | File/code dự kiến | Điều kiện đóng |
|---|---|---|---|
| 0 — chặn rủi ro nguồn | Làm rights matrix cho bảy FRED + ba ALFRED source records; đánh dấu owner, distributor, endpoint/terms, data use, retention, derivative/export, required notice, date checked và decision/evidence. Tạo disposition cho nhóm macro-market để không còn orphan source IDs. | `docs/data/creditatlas-source-release-register-*.json`, `docs/data/n02-source-to-kpi-map-*.json`, `project_register.py`, report phụ lục này. | Tất cả record có group/disposition rõ; API register validate liên kết; status không ghi “cleared” khi chỉ có citation. Giữ 27 existing groups và 123 records làm historical baseline cho tới khi migration có receipt thực tế. |
| 1 — rà điểm phục vụ | Trace 7 latest series và 3 ALFRED panels từ ingestion tới Parquet/report/API/UI/JSON export; thêm matrix KPI → source field → formula → time alignment → page/endpoint/export. Tách “đang chạy private local”, “disabled”, “rights approved”. | `public_sources.py`, `public_suite.py`, `market_data.py`, `market_views.py`, `mortgage_macro_context.py`, `server.py`, UI modules và tests tương ứng. | Mọi output có documented source, frequency, unit, as-of/revision semantics, missing/quarantine, rights status; không còn label gây hiểu nhầm hoặc path kích hoạt từ catalog mặc định khi rights chưa rõ. |
| 2 — chọn direct replacement | Với UNRATE, FHFA HPI, Treasury par yields, PMMS: kiểm tra publisher terms/API, exact series definition, update/revision policy, dates, units, row counts và overlap values với local FRED extracts. ICE OAS giữ blocked cho tới license. | Adapter mới chỉ sau rights check; `data/private` receipts không public; source/KPI trace và migration memo. | Direct-series parity được lượng hóa (coverage, mismatches theo date, revision/as-of differences), mọi chênh lệch có nguyên nhân; không đổi historical PIT thành latest-revised. Publisher cho phép automated download/retention hoặc có văn bản cho phép cụ thể. |
| 3 — thay đổi app có kiểm soát | Chỉ sau khi gate/decision được ghi: chuyển series từng cái một. Giữ baseline/private historical receipts, thêm migration version, giữ old/new adapters song song trong QA, rồi cập nhật catalog/UI labels. BAMLC0A0CM bị loại khỏi public/software flows nếu không có license. | Source adapter/service/API/UI/export; static and focused route tests. | Adapter boundary fail-closed khi rights status not cleared; no-series state hiển thị lý do; public bundle không bao gồm raw provider data; API/UI/Excel/JSON cùng định nghĩa và provenance. |
| 4 — validation & publish | Chạy source-level checks, unit/integration, local UI browser smoke, download parity, stale-label scan, repo manifest/hash audit. | `tests/test_market_data.py`, `tests/test_mortgage_macro_context.py`, route-specific tests, acceptance receipts, docs/workbook if changed. | Không page errors; tests ghi số pass/fail/skip; report/export giữ parity và private flags; rights notice hiển thị khi required; manifest chỉ hash file public được phép. GitHub push chỉ sau khi kiểm tra bundle không chứa raw/private artifact. |

### KPI cụ thể phải truy vết cho N03

- P5: daily native date coverage; value/missing/quarantined counts per series; 2Y–10Y và 10Y–30Y slopes theo basis points; DGS30 known-date filter; monthly min/max/mean/last-known; corporate OAS conversion percent→bp và scope; weekly mortgage series chart native-only; no-forward-fill rule.
- D01 macro: monthly UNRATE alignment; quarterly USSTHPI; weekly PMMS; vintage date ≤ month-end; publication availability field/source; lag/availability join; null when an eligible vintage is absent. Tách latest revised from true historical point-in-time.
- Bond scenario: toàn bộ coupon/yield/face/maturity/frequency inputs do analyst khai báo; price/duration/convexity/DV01 là công thức scenario, không phải quote/market-calibrated result. Gắn assumption receipt và method version; không gán nguồn FRED như input bắt buộc nếu term/yield do người dùng tự nhập.

## 5. Thứ tự công việc dự kiến sau phụ lục

1. **N02.1 registry/disposition + rights review** — registry orphan fix, exact terms matrix, route-consumer inventory. Đây là ưu tiên trước khi mở rộng data acquisition.
2. **N03.1 output lineage** — khóa số KPI nào được phép hiển thị trong trạng thái hiện hành; ghi formula, dates, revisions, units và export route.
3. **N02.2 source replacement feasibility** — lần lượt BLS, FHFA, Treasury, Freddie/PMMS. Không cào lại bằng FRED trong giai đoạn này; không tự động crawl Freddie khi terms chưa cho phép.
4. **N03.2 N05/N06 parity remainder** — hoàn thiện các query/export còn lại trong kế hoạch hiện hành; chỉ sửa sau khi source-specific checks fail hoặc có scope mới.
5. **D01 R2/R3** — tiếp tục phụ thuộc Clarity access hợp lệ cho annual Freddie samples. Macro-context/source right remediation không thay điều kiện sample, label maturity, time split hay minimum-support gate.
6. **ICE OAS** — chờ written approval/license hoặc gỡ khỏi public path. Không nội suy/thay bằng proxy mà không có nghiên cứu/validation độc lập.

Ước lượng thời gian chưa chốt vì chưa có xác nhận terms/license cho từng publisher và chưa đo đầy đủ mọi route. Phần code migration chỉ estimate sau khi N02.1 và đối soát series direct-source đã xác định phạm vi; không dự phóng effort từ phần trăm completion 26/50.

## 6. Điều không được kết luận từ audit này

- Không được nói đã đọc line-by-line tất cả repo hoặc kiểm tra từng dòng của mọi source dataset.
- Không được nói 26/50 (52%) là completion của riêng D01; đó là ledger toàn CreditAtlas P1–P5.
- Không được coi source record/hash/API/Excel check là quyền sử dụng đã được cấp.
- Không được suy default/PD từ HMDA, aggregate HMDA/NMDB/HPI/macro, FHA flow, Bondora NULL hoặc ABS residual chưa phân loại.
- Không được tạo forecast/imputation để lấp missing. Nếu cần, phải nghiên cứu riêng biến, mục đích, nguồn, method, baseline, backtest, uncertainty và sensitivity trước khi hiển thị.
