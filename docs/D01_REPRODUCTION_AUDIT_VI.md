# D01 clean-reproduction audit

Date: 2026-10-15. Frozen case: `d01-a24484b21a21`.

The eight-stage foundation was rebuilt again from the case's registered source snapshot. All stages passed: canonical, labels, audit, portfolio, splits, attrition, metrics, and vintage. The independent upstream comparator reports the same code fingerprint and source manifest, zero differences in all 13 parquet artifacts and all four stable JSON summaries, including 4,510,559 loan-month rows and 4,902 episode rows. After fixing repeat-receipt handling, the CLI was run end-to-end again and exited PASS, creating a new pipeline-specific receipt. The reproduction remains descriptive and `research_ready=false`; it does not create model predictions or substitute for the final report/research release.

The first repeat run uncovered a receipt-lifecycle bug after the comparison had already passed: the command tried to create `reproduction.json` with exclusive-create semantics even though the original proof already existed. The original receipt was left intact. Repeat receipts are now written as `reproduction-<pipeline-id>.json`; two regression tests cover first and subsequent runs. The successful clean CLI rerun is saved as [versioned reproduction receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). The earlier primary proof remains [reproduction.json](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).

Re-run from the D: project root with `PYTHONPATH=src python -m credit_atlas.cli reproduce --case private evidence omitted from public release`. Test the immutable receipt writer with `PYTHONPATH=src python -m pytest -q --basetemp .tmp/pytest-reproduction tests/test_foundation_reproduction_receipts.py`.

This advances M01-029 from foundation-only reproduction to a byte-identical descriptive report, normalized snapshot parity, reproduced pre-fit model gate, and 39-check UI acceptance on a fresh valid case. M01-029 remains Partial because qualified multi-vintage model fitting, calibration, and final out-of-time release remain blocked.


## Tái lập descriptive report và model gate — 15/10/2026

Tạo case private hợp lệ `d01-202610150931` từ cùng foundation receipt đã xác minh. Snapshot mới chứa 50.000 khoản vay và 4.510.559 loan-month. `report.json` khớp từng byte với case gốc; `snapshot.json` có cùng JSON sau khi bỏ riêng `case_id`. Loan index không so byte vì mỗi case sinh secret HMAC mới cho pseudonymous loan keys. ResearchService xác minh case mới và xếp nó đầu danh sách completed cases.

Từ case mới, chạy lại `prepare-study`, `prepare-features` và `assess-study`: study `PREPARED_NOT_FIT_READY`, feature audit `FEATURE_AUDIT_NOT_MODEL_READY`, assessment `BLOCKED_BEFORE_FIT`; train có 100 positive / 43.227 negative, calibration/validation/test đều 0. Không fit model, không đọc/đưa ra score, không chọn champion. Browser QA mới nhất chạy 42/42 checks PASS trên đúng case mới. Receipt tổng hợp: [final reproduction receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included); browser evidence: [42-check receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).

Vì vậy M01-029 có bằng chứng cho descriptive report, UI và tái lập trạng thái model gate, nhưng vẫn Partial: chưa có nhiều annual vintages đủ chuẩn để chạy model study, calibration và final out-of-time.


### Mở rộng transport/error-state acceptance

Sau mốc 39 checks, browser QA tăng lên 42 checks và vẫn PASS trên case mới. Bổ sung tình huống snapshot trả HTTP 500 với JSON error, HTTP 502 với HTML không phải JSON và run catalog trả HTTP 503; cả ba đều hiện trạng thái unavailable và không giữ KPI cũ. Receipt hợp nhất mới nhất: [reproduction + 42-check browser QA](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included), [browser receipt](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included). M01-028 vẫn Partial cho tới khi các transport/serving failure trên những workspace API khác được cover ở phạm vi phù hợp.
