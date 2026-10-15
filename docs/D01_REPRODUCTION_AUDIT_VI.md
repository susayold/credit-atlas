# D01 clean-reproduction audit

Date: 2026-10-15. Frozen case: `d01-a24484b21a21`.

The eight-stage foundation was rebuilt again from the case's registered source snapshot. All stages passed: canonical, labels, audit, portfolio, splits, attrition, metrics, and vintage. The independent upstream comparator reports the same code fingerprint and source manifest, zero differences in all 13 parquet artifacts and all four stable JSON summaries, including 4,510,559 loan-month rows and 4,902 episode rows. After fixing repeat-receipt handling, the CLI was run end-to-end again and exited PASS, creating a new pipeline-specific receipt. The reproduction remains descriptive and `research_ready=false`; it does not create model predictions or substitute for the final report/research release.

The first repeat run uncovered a receipt-lifecycle bug after the comparison had already passed: the command tried to create `reproduction.json` with exclusive-create semantics even though the original proof already existed. The original receipt was left intact. Repeat receipts are now written as `reproduction-<pipeline-id>.json`; two regression tests cover first and subsequent runs. The successful clean CLI rerun is saved as [versioned reproduction receipt](../artifacts/private/d01-a24484b21a21/reproduction-pipeline-0415306845cd.json). The earlier primary proof remains [reproduction.json](../artifacts/private/d01-a24484b21a21/reproduction.json).

Re-run from the D: project root with `PYTHONPATH=src python -m credit_atlas.cli reproduce --case artifacts/private/d01-a24484b21a21`. Test the immutable receipt writer with `PYTHONPATH=src python -m pytest -q --basetemp .tmp/pytest-reproduction tests/test_foundation_reproduction_receipts.py`.

This advances M01-029 from foundation-only reproduction to a byte-identical descriptive report, normalized snapshot parity, reproduced pre-fit model gate, and 39-check UI acceptance on a fresh valid case. M01-029 remains Partial because qualified multi-vintage model fitting, calibration, and final out-of-time release remain blocked.


## Tái lập descriptive report và model gate — 15/10/2026

Tạo case private hợp lệ `d01-202610150931` từ cùng foundation receipt đã xác minh. Snapshot mới chứa 50.000 khoản vay và 4.510.559 loan-month. `report.json` khớp từng byte với case gốc; `snapshot.json` có cùng JSON sau khi bỏ riêng `case_id`. Loan index không so byte vì mỗi case sinh secret HMAC mới cho pseudonymous loan keys. ResearchService xác minh case mới và xếp nó đầu danh sách completed cases.

Từ case mới, chạy lại `prepare-study`, `prepare-features` và `assess-study`: study `PREPARED_NOT_FIT_READY`, feature audit `FEATURE_AUDIT_NOT_MODEL_READY`, assessment `BLOCKED_BEFORE_FIT`; train có 100 positive / 43.227 negative, calibration/validation/test đều 0. Không fit model, không đọc/đưa ra score, không chọn champion. Browser QA mới nhất chạy 42/42 checks PASS trên đúng case mới. Receipt tổng hợp: [final reproduction receipt](../artifacts/private/d01-final-reproduction-qa42-20261015/receipt.json); browser evidence: [42-check receipt](../artifacts/private/browser-qa-8c77d535b638/receipt.json).

Vì vậy M01-029 có bằng chứng cho descriptive report, UI và tái lập trạng thái model gate, nhưng vẫn Partial: chưa có nhiều annual vintages đủ chuẩn để chạy model study, calibration và final out-of-time.


### Mở rộng transport/error-state acceptance

Sau mốc 39 checks, browser QA tăng lên 42 checks; standalone continuation tiếp tục lên **57 checks PASS** trên cùng fresh verified case. Các check bổ sung kiểm tra transition mart, episode follow-up, source monitoring, private loan search/timeline, provenance, prepared-study, loss diagnostics, findings/history/save APIs khi trả HTTP 500/502/503. Các check khác xác nhận FHFA NMDB aggregate context render kèm caveat population; standalone JSON export có đủ 98 quý/hash; lỗi report export và NMDB export đều hiển thị, không tạo file giả. Shared browser API reader trả thông báo rõ khi body lỗi không phải JSON hoặc JSON hỏng; không đưa nội dung HTML qua UI. Receipt reproduction ban đầu: [reproduction + 42-check browser QA](../artifacts/private/d01-final-reproduction-qa42-20261015/receipt.json), [42-check browser receipt](../artifacts/private/browser-qa-8c77d535b638/receipt.json). Latest standalone: [57-check browser receipt](../artifacts/private/browser-qa-2d25ed161db0/receipt.json). M01-028 vẫn Partial vì các workspace API/delivery flows ngoài D01 còn cần kiểm tra theo scope phù hợp.
