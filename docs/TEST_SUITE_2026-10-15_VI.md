# Verification toàn repository — 15/10/2026

## Latest run after NSMO CSV-streaming extension

`scripts/test.ps1` ran the complete app and vendor suite after adding the streaming NSMO status parser.

| Kết quả | Số lượng |
|---|---:|
| Collected/executed | 1.577 |
| Passed | 1.577 |
| Failures/errors/skips | 0 / 0 / 0 |
| Elapsed | 341.4 seconds |
| Receipt | `private evidence omitted from public release` |

The previous direct run at 1,574 tests is preserved in `private evidence omitted from public release`. The earlier batch receipt below preserves per-batch JUnit and logs for 1,568 tests.

## Earlier sequential-batch run

Toàn bộ test suite được thu thập một lần và chạy tuần tự qua 21 process mới
(tối đa 8 test files mỗi process). Receipt mới nhất:
`private evidence omitted from public release`.

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
