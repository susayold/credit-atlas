# D01 — dependency, resource, privacy và release readiness

Checkpoint: 15/10/2026. Đây là đánh giá package nội bộ trước nghiên cứu tiếp
theo, không phải quyết định phát hành công khai.

## Bằng chứng đã chạy

| Control | Kết quả hiện tại | Evidence |
|---|---|---|
| Python/runtime lock | Python 3.12.14; 19/19 distributions khớp `requirements-lock.txt` | `artifacts/private/d01-release-readiness-89b0c5945a8f/receipt.json` |
| Engine provenance | Pinned commit `8d9994cfcb91fe871d66a4238c3f56053d71e920`; SHA-256 khớp cả 164 file copy | Cùng receipt, `vendor/credit_risk_strategy_lab/UPSTREAM.json` |
| Storage boundary | Repo, vendor, raw/private data và derived/private artifacts đều ở D: | Cùng receipt |
| Private file exclusion | 0 private paths trong 969 Git candidates | Cùng receipt |
| Served-bundle privacy | 15 static assets, quét byte-level đối với đủ 50.000 source loan IDs; 0 matches; assets đúng explicit allowlist | `artifacts/private/package-audit-4dd8b231c83e/receipt.json` |
| Foundation resource | Clean descriptive rebuild 192,264 giây, peak working set 812.138.496 bytes (~774,5 MiB) | `artifacts/private/d01-a24484b21a21/foundation-complete.json` |

Lock ứng dụng gồm DuckDB 1.5.5/PyArrow 22.0.0; optional groups pin
scikit-learn 1.8.0, NumPy 2.5.3, SciPy 1.18.1, Playwright 1.56.0 và xlrd
2.0.2. Python runtime hiện khớp lock. Upstream lock dành cho model có
threadpoolctl 3.6.0, còn runtime app lock là 3.7.0; cần giữ rõ môi trường nào
được dùng khi tái tạo model workflow.

## Những gì còn chặn release

- Package metadata của colorama 0.4.6 và DuckDB 1.5.5 thiếu trường SPDX/license
  metadata trong runtime, nên cần kiểm tra notices/license files upstream.
- Bản copy engine không chứa LICENSE. Public fetch của URL upstream trả 404 ở
  lần rà soát này, vì vậy quyền redistribution chưa được xác nhận. URL commit
  trong provenance không phải giấy phép.
- Raw mortgage archive có receipt `user_supplied`; hash chứng minh byte lineage,
  không chứng minh publisher release identity, publication date hoặc điều khoản.
- Package scan kiểm tra explicit app bundle và path Git hiện tại; không tự
  duyệt legal rights cho mọi source-derived statement trong tài liệu, và cần
  chạy lại nếu có thay đổi assets hoặc trước khi external deploy.
- Benchmark là một clean rebuild đơn lẻ; chưa đo concurrent API load, full
  model training, multi-vintage footprint hoặc worst-case spill.

Vì vậy M01-004 vẫn **Partial**: storage, dependency pin, engine bytes và static
privacy có bằng chứng; expanded release/legal/resource sign-off chưa đạt.
Không đưa raw/source-derived private content lên external release.

## Acquisition decision theo plan

Không có annual Freddie loan-performance vintage mới được thêm. Trang chính
thức Freddie yêu cầu đăng nhập Clarity cho full/by-year downloads. Fannie Mae
cập nhật primary acquisition/performance qua Q1 2026 nhưng Data Dynamics cần
đăng ký và được duyệt. HMDA public LAR chứa application/origination outcomes,
không chứa monthly post-booking performance; workspace đã có module HMDA riêng,
nên không được ghép HMDA vào D01 hay tính như vintage bổ sung. Public Freddie
Release 47 examples/layout chỉ là parser reference và có ID disjoint.

Sources: [Freddie Mac SFLLD](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset),
[Fannie Mae Single-Family Loan Performance Data](https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data),
[Fannie Data Dynamics access](https://capitalmarkets.fanniemae.com/tools-applications/data-dynamics),
[FFIEC/CFPB HMDA data browser API](https://ffiec.cfpb.gov/documentation/api/data-browser/).
