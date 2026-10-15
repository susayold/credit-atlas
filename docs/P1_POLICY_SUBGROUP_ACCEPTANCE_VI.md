# P1.04 và P1.09 — policy/subgroup theo saved validation evidence

Đã chuyển đường phục vụ catalog/report/preview/save của Policy và subgroup sang verifier dùng saved predictions. Không gọi lại model inference/refit. Source/model bundles vẫn giữ nguyên; policy và subgroup QA lưu trong thư mục riêng dưới artifacts/private.

## P1.04 — decision policy

Inputs là boosting/raw scores đã lưu cho4.499 validation clients/995 events, hai thresholds, sáu action×outcome costs và declared capacity. Rule: accept p<lower, review lower≤p<upper, decline p≥upper; ties giữ cùng action. Vượt capacity chỉ flag overflow, không reassignment/drop records. Missing capacity là unavailable; empty action rate/mean là null.

Expected declared cost được tính từ probability và cost matrix; retrospective proxy dùng source labels. Cả hai dùng declared cost units, không tự thành cash loss, savings hoặc actual intervention outcomes. Validation đã dùng chọn model nên policy comparisons vẫn exploratory. Illustrative capacity600 và lower thresholds0,10/0,30 cho2.277 review clients, overflow1.677; capacity3000 chỉ đổi breach flag.

Nguồn evidence: `retail-policy-audit-8f505ca2f0ed.json` có184 exact Fraction checks PASS; `retail-policy-browser-qa-f6c67fc270d9/receipt.json` có9 nhóm PASS về preview, dirty/save, version/export, capacity, reload, invalid scopes và mobile. Probe đó chặn9 inference/deep-verifier entry points trên cả Policy/subgroup catalog, ghi forbidden_calls0, và kiểm tra4 subgroup dimensions thật.

## P1.09 — subgroup và monitoring scope

Study `retail-subgroups-3cf671cf3152` nối đúng validation IDs/saved probabilities với **demographics excluded from model**: SEX/EDUCATION/MARRIAGE/AGE. Không select LIMIT/BILL/PAY predictor columns hoặc final-test predictor rows. Source join, saved row snapshot và toàn bộ group report được replay, không bỏ kiểm tra numerical/source reconciliation.

Có17 group rows qua sex/education/marriage/age_band. Metrics gồm coverage, source event rate, mean probability, Brier, AUC, policy actions và high-risk capture/flag rate. Small groups giữ counts nhưng unsupported metrics là unavailable; one-class/insufficient-class groups không được gán AUC. Demographic exclusion không chứng minh fairness. Temporal monitoring/drift, causal effect, fairness certification và production approval đều chưa qualified.

`retail-subgroups-audit-5aa17c776d15.json`:314 independent checks PASS trên actual validation study. `retail-subgroups-browser-qa-0b36e96a972d/receipt.json`:5 nhóm PASS về categories, small support, selected-dimension aggregate export, desktop/mobile và holdout ledger. Unit/HTTP/source/replay/migration tests:35 PASS trong `policy-subgroup-saved-tests.xml`.

## Compatibility và persistence

Historical subgroup receipts pin serving adapter fingerprint `7d67bd852493776cfb1e3c758eb6bd0d720bd319b9a7cc07b48f1e25d86a448a`. Chỉ fingerprint đó hoặc current adapter được hỗ trợ; numerical engine fingerprints vẫn phải khớp. Unknown/missing methods hoặc changed engine bị từ chối. Không rewrite receipt cũ; nguồn, rows và group metrics tiếp tục được verify đầy đủ. New studies ghi saved-writer SHA và no-inference flag.

`subgroup-saved-persistence-3c6d001989f2/receipt.json` PASS: writer/save/reopen/catalog và4 dimensions trong QA storage riêng; full report khớp study gốc, source study/holdout ledger không đổi; forbidden inference calls0. Method/source hashes và các bản xuất được pin trong sổ requirements. Không dùng browser PASS riêng để suy ra source/model qualification.

## Phần chưa đạt ngoài current benchmark workflow

Actual operating costs, staffing/daily inflow, reject/treatment outcomes, temporal cohorts, deployment calibration, authenticated ownership/sign-off và production qualification vẫn mở. Không tự chuyển Taiwan booked-card benchmark thành application underwriting hoặc Vietnam PD. Mục tiêu100% toàn dự án chưa hoàn thành.
