# FHFA U.S. All-Transactions HPI — direct source and parity review

Rà soát: **18/10/2026 Asia/Bangkok**. Đây là source snapshot mới cho D01 macro context; nó bổ sung national/census geography vào HPI theo bang đã đăng ký ở [FHFA state HPI review](FHFA_STATE_HPI_SOURCE_REVIEW_VI.md). Không dùng HPI để thay mortgage performance/default labels.

## Nguồn, quyền dùng và định nghĩa

FHFA liệt kê file CSV **U.S. and Census Divisions — All-Transactions Indexes, Not Seasonally Adjusted** trong trang HPI datasets. File gốc headerless có bốn trường: geography, year, quarter, index. Mã `USA` là U.S. national; chín `DV_*` là Census divisions. FHFA mô tả All-Transactions HPI dùng sales-price và appraisal data. FAQ nói dữ liệu HPI được tải và sử dụng miễn phí, đồng thời khuyến nghị ghi nguồn rõ loại chỉ số và điều chỉnh mùa vụ; app vì vậy hiển thị attribution riêng.

- [FHFA HPI datasets](https://www.fhfa.gov/data/hpi/datasets?tab=master-hpi-data)
- [Direct quarterly U.S./Census CSV](https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_us_and_census.csv)
- [FHFA HPI FAQ — use and attribution](https://www.fhfa.gov/document/hpi-faqs)
- [FHFA HPI description and methodology links](https://www.fhfa.gov/data/hpi)

Receipt retrieval: **17/10/2026 20:20:58 UTC**. Raw release có **2.060 rows**, 10 geography codes × 206 quý/quốc gia, từ **1975Q1 đến 2026Q2**. Parser kiểm tra đủ 10 mã geography, đủ quý liên tục, không trùng key, index finite/dương và panel cân bằng. Raw source và full receipt hashes được giữ trong private D: data; public repo chỉ lưu parser, receipt summary và source attribution.

## Đối soát với FRED USSTHPI

Đã so raw direct FHFA national `USA` với snapshot FRED `USSTHPI` được tải ngày **08/10/2026 18:26:18 UTC**. Hai nguồn có **206/206 quý trùng nhau từ 1975Q1–2026Q2**, không có direct-only/FRED-only quarter, missing-value disagreement hay value mismatch. So sánh dùng exact Decimal equality; không nội suy hoặc làm tròn để tạo match. Machine-readable crosswalk và script ở [source-to-KPI map](data/n02-source-to-kpi-map-2026-10-17.json) và `scripts/compare_fhfa_us_hpi_to_fred.py`; receipt đầy đủ vẫn ở private evidence.

Đây là overlap parity giữa hai snapshot được lấy ở hai thời điểm khác nhau. Nó **không** chứng minh chúng cùng revision vintage, publication timestamp, quyền sử dụng FRED/ALFRED, hay khả năng tạo lịch sử point-in-time. Không dùng snapshot hiện nay để dựng lại HPI từng được công bố vào underwriting/event dates trong quá khứ.

## Tích hợp vào D01 context

`scripts/acquire_public_mortgage_context.py` tải HPI trực tiếp từ FHFA, giữ raw file và SHA-256 trong private run, xác thực source schema rồi chuẩn hóa riêng geography `USA` thành `USSTHPI.csv` với kỳ quý được mã hóa bằng ngày đầu quý. `src/credit_atlas/mortgage_macro_context.py` giữ series ở grain quarterly, trả source URL, citation, rights status và snapshot quarter qua `/api/mortgage-macro-context`. D01 monthly alignment không nội suy HPI xuống tháng; API vẫn đánh dấu macro context là retrospective descriptive, không qualified model predictor.

UNRATE và MORTGAGE30US hiện vẫn theo FRED trong cùng pipeline; quyền/retention còn phải rà theo BLS và Freddie/FRED. ALFRED point-in-time HPI vẫn là product riêng có rights gate; HPI direct hiện tại không thay ALFRED vintage. Public checkout không chứa private D01 run nên lần này đã kiểm tra parser, acquisition adapter bằng fixture, macro report/API với fixture trực tiếp và direct/FRED file parity, nhưng chưa chạy acquisition end-to-end trên D01 private case. Browser smoke ở localhost là exploratory; process revision chưa được ràng buộc với commit này.
