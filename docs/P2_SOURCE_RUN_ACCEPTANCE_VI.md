# P2.01 — Source & run explorer: nghiệm thu phạm vi hiện tại

Đã kiểm tra toàn bộ yêu cầu hiện tại của P2.01 trong `PLAN_WORKBENCH_DETAIL.md`: source/run context, years/release/coverage, rebuild lineage và data readiness; exports giữ phạm vi sample, không suy ra toàn thị trường hoặc ngày công bố từ extraction.

## Bằng chứng

| Phạm vi | Kết quả |
|---|---|
| ZIP cung cấp | SHA256 khớp workspace config, raw receipt, foundation và case |
| Hai member ZIP | Đọc toàn bộ để kiểm CRC: 50.000 origination records và 4.510.559 performance records; không blank record |
| Frozen lineage | 44 file entries khớp hash, gồm verified inputs và outputs; giữ nguyên entries lặp trong manifest |
| Pipeline | 8 stages PASS, pipeline receipt hash khớp foundation; case/snapshot cùng pipeline |
| Release | Receipt và source run/snapshot cùng khai báo 47; chưa xác thực publisher registry |
| Data readiness | Support, missing years, exclusions, blocking reasons khớp split audit; `not_qualified`, chưa fit actual mortgage model |
| Run catalog | Years/release/counts/completion time/model status khớp manifest và snapshot |
| Evidence UI/API | Toàn bộ 40 artifact entries được đối chiếu; case/pipeline/commit/target/raw hash khớp |
| Sources và exports | 4 segment scopes giữ coverage toàn sample và đúng lineage; phạm vi tháng chỉ áp vào bảng được quy định |
| Mobile | 390px không overflow; không sửa retail holdout |

Nguồn kiểm tra: `artifacts/private/source-run-acceptance-8d10b50dbedf/receipt.json`, `artifacts/private/source-run-browser-acceptance-c0e7b5549a22/receipt.json`. Kiểm tra provenance riêng: `mortgage-provenance-browser-06016d651e3a/receipt.json`; 25 tests trong `mortgage-provenance-tests.xml` PASS.

## Cách đọc phạm vi nghiệm thu

Nghiệm thu **explorer trên corpus được cung cấp** không xác thực rằng ZIP này là bản publisher phát hành. Giao diện ghi rõ receipt-declared release, publication date chưa biết, và ngày nhận/extraction/rebuild/case hoàn tất riêng. ZIP có member `sample_perf_2012.txt`; không suy ra authenticity từ convention tên file.

50.000 khoản vay và 4.510.559 loan-months là sample năm origination 2012 đang quan sát, không phải toàn thị trường và không phải số unique loans bằng loan-months. Các bản xuất aggregate ghi `derived_observed_sample`, limitation “not the Freddie Mac universe” và retrospective latest-release target; bản provenance riêng chứa declarations và thời điểm.

Readiness đang có 100 positives và 43.227 negatives ở train; calibration/validation/test chưa có support. Thiếu vintages 2006–2011, 2014, 2016, 2018; chưa hoàn tất protocol approval. Explorer hiển thị các gate này, không chứng minh mô hình đủ điều kiện.

Thêm authorized annual vintages và reconcile từng acquisition vẫn là phần phát triển tiếp theo trong plan. **P2.08 và mục tiêu 100% toàn dự án chưa hoàn thành.** Receipt-byte parity không là legal/licensing verification hoặc historical availability proof.
