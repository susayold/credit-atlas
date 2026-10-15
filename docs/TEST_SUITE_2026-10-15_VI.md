# Verification toàn repository — 15/10/2026

## Latest run after NSMO D02 aggregate workspace

After adding the separate NSMO page/API, hash-bound aggregate response,
quarterly status view and synthetic route/privacy checks, `scripts/test.ps1`
ran the full app and vendored-engine suite.

| Kết quả | Số lượng |
|---|---:|
| Collected/executed | 1,606 |
| Passed | 1,606 |
| Failures/errors/skips | 0 / 0 / 0 |
| Elapsed | 344.93 seconds |
| Focused NSMO tests | 16/16 passed |

The local D02 endpoint serves aggregate profile data only after the PUF hash,
release receipt, audit receipt and aggregate invariants reconcile. It exposes no
loan identifiers or row-level data. Public-mirror regression tests also pass
16/16 using synthetic private-data fixtures. No PD target or model is defined.

## Latest run after NSMO v7.0 private PUF acquisition and parser audit

After adding lowercase-header support and focused regressions, `scripts/test.ps1`
ran the full application and vendored-engine suite.

| Kết quả | Số lượng |
|---|---:|
| Collected/executed | 1,601 |
| Passed | 1,601 |
| Failures/errors/skips | 0 / 0 / 0 |
| Elapsed | 365.46 seconds |
| Receipt | `artifacts/private/test-suite-direct-20261015-nsmo-puf/receipt.json` |

The source-specific NSMO unit file passes 11/11, including lowercase FHFA PUF
headers and case-insensitive duplicate-header rejection. Separately, the actual
private PUF parser streamed 3,180,309 status observations through 51 quarter
columns without an unknown code; aggregate-only data checks are in
`artifacts/private/nsmo-puf-20261015/`. This does not qualify a target or model.

## Latest run after Ginnie LoanPerf audit gate and parser

`scripts/test.ps1` ran the full app and vendor suite after adding the Ginnie Mae
Loan Performance File source contract, terms-gated aggregate-only ZIP auditor,
and synthetic fixtures. This verifies code behavior against the documented
59-field pipe-delimited contract; no Ginnie production payload was downloaded
or used in these tests.

| Kết quả | Số lượng |
|---|---:|
| Collected/executed | 1.587 |
| Passed | 1.587 |
| Failures/errors/skips | 0 / 0 / 0 |
| Elapsed | 336.22 seconds |
| Receipt | `artifacts/private/ginnie-loanperf-source-review-20261015/receipt.json` |

## Latest run after FHFA NMDB standalone export and parser bounds

`scripts/test.ps1` ran the complete app and vendor suite after adding quarter-continuity and percentage-bound validation, the NMDB source JSON endpoint, and D01 download-error handling.

| Kết quả | Số lượng |
|---|---:|
| Collected/executed | 1.581 |
| Passed | 1.581 |
| Failures/errors/skips | 0 / 0 / 0 |
| Elapsed | 320.51 seconds |
| Receipt | `artifacts/private/test-suite-direct-20261015-nmdb-export/receipt.json` |

The previous direct run at 1,580 tests after initial NMDB context integration is preserved in `artifacts/private/test-suite-direct-20261015-nmdb-context/receipt.json`; previous runs at 1,577 and 1,574 are preserved in their receipts. The earlier batch receipt below preserves per-batch JUnit and logs for 1,568 tests.

## Earlier sequential-batch run

Toàn bộ test suite được thu thập một lần và chạy tuần tự qua 21 process mới
(tối đa 8 test files mỗi process). Receipt mới nhất:
`artifacts/private/test-batches-e8453a2adc33/receipt.json`.

| Kết quả | Số lượng |
|---|---:|
| Collected/executed | 1.568 |
| Passed | 1.568 |
| Failures/errors/skips | 0 / 0 / 0 |
| Batches passed | 21/21 |

Mỗi batch có JUnit XML và log riêng; runner xác nhận tổng executed bằng số
collected và không retry test lỗi. Chạy lại bằng:

```powershell
& .venv\Scripts\python.exe scripts\test_batches.py --batch-files 8
```

Runner tự cấu hình import paths cho app và pinned vendor engine; lần chạy này
cũng xác nhận subprocess test với optimized Python. Đây là bằng chứng kỹ thuật
trên runtime Windows hiện tại. Nó không chứng minh
source rights/release authenticity, multi-vintage qualification, model
performance, load dưới concurrent use hay production readiness.
