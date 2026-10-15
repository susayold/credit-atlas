# CreditAtlas — đối chiếu chi tiết với plan ngày 12/10/2026

Bản kiểm kê đọc từ sổ 50 yêu cầu, plan KPI và các receipt đã lưu. Không chạy lại toàn bộ hệ thống trong lần kiểm kê này. Không thay đổi trạng thái nghiệm thu hoặc mở lại frozen holdout.

## 1. Tỷ lệ có thể báo cáo

| Cách đo | Số mục | Tỷ lệ |
|---|---:|---:|
| Trạng thái Đã có trong checkpoint |21/50|42%|
| Đã có và Có điều kiện |30/50|60%|
| Có triển khai theo ba trạng thái đầu |42/50|84%|
| Một phần |12/50|24%|
| Cần dữ liệu để đạt scope đầy đủ |8/50|16%|

Các tỷ lệ tính đều từng capability, không theo giờ công. 60% và 84% là coverage, không phải tỷ lệ hoàn thành hoàn toàn. Nghiệm thu theo toàn bộ yêu cầu hiện tại: 26/50 mục có full_completion_proven. Đây là số mục đã đóng bằng evidence, không phải tỷ lệ giờ công hoặc production readiness. Một số mục Cần dữ liệu đã có thêm sub-workflow nhưng chưa đủ điều kiện nâng trạng thái.

## 2. Theo domain

| Domain | Đã có | Có điều kiện | Một phần | Cần dữ liệu | Đã có | Có workflow gồm điều kiện |
|---|---:|---:|---:|---:|---:|---:|
|P1 Retail|3|1|2|4|30%|40%|
|P2 Mortgage|7|1|1|1|70%|80%|
|P3 Business|6|0|3|1|60%|60%|
|P4 Portfolio & observatory|5|4|1|0|50%|90%|
|P5 Structured & market|0|3|5|2|0%|30%|

## 3. Bổ sung mới và giới hạn còn lại

- **P1.02 LendingClub:** đã tải nguồn công khai gồm 2.260.701 accepted và 27.648.741 rejected records, profile 151/9 cột, dictionary và temporal evidence. API, app, lọc cohort, quality tables, JSON export đã có. Receipt browser `lendingclub-full-source-qa-b7ce59b0f371/receipt.json`: PASS 4 nhóm, ledger không đổi. Chưa chứng minh application-time feature availability, cutoff quan sát, mature PD12 labels, borrower identity và intended-use/OOT; không tính approval rate từ hai population chưa đối sánh.
- **P1.05 Affordability:** đã có schema, engine, API và form nhập trong app; quy đổi kỳ thu nhập/nghĩa vụ, total DTI, residual income, policy khai báo và sensitivity; private JSON export. Bổ sung XLSX adapter/API/file picker, source cell lineage, form hydration và blank guided template/download: 53 adapter/engine/HTTP tests PASS, browser `affordability-excel-qa-5db4d5f8f7f8/receipt.json` PASS 5 nhóm; form regression `affordability-qa-560a56b59b5a` PASS 4; native Excel 38 cells/2workbooks PASS. Ledger không đổi. Hồ sơ QA là synthetic. Chưa có verified income, chứng từ nghĩa vụ thực, source-document verification và người chịu trách nhiệm xác minh; chưa trả quyết định tín dụng.
- **P2.01/P2.02 public Fannie samples:** thêm7files/1217459bytes,Single-Family8loans/757monthly rows108positions,Multifamily4loans/241monthly rows62fields và17annual DSCR rows. Independent96749positions/173fields PASS,27backend/HTTP tests và4browsergroups PASS. Source/API/UI/export đã có,không thêm Freddie annual vintage hoặc qualify PD12;sample được cung cấp để thiết lập database.
- **P3.03/P3.07/P3.08 DSCR và covenant:** đã có EBMUD actual historical debt-service/DSCR và driver bridge; Ford facility versions, Apple nominal note schedules, nguồn clause/covenant. Actual historical DSCR không tự đóng toàn bộ covenant workbench: còn effective amendment chain, adjusted definitions, actual balances và supported headroom/compliance.
- **P4.09 Sovereign:** thêm 4 editions 2023–2026, 42.519 entity-year rows; có archive/API/app/export và audit. Chưa là calibrated sovereign PD/LGD hoặc validated macro stress model.
- **P5 dữ liệu collateral:** thêm mirror ABS-EE 488.219 asset-period rows, field definitions, static-pool 21 cohorts, managed-pool 7 kỳ và SOFR benchmark 443 observations. Còn source fidelity, loan-level targets, full legal waterfall, forecast và independent valuation benchmark.
- **Excel/KPI:** catalogue 88 KPI và 22 quality controls; 6 workbooks, 9.264 cells/746 formulas đã có native baseline checks và 18 ca đại diện/59 checks PASS. Chưa chứng minh mọi KPI có actual đủ đầu vào hoặc full native/production qualification.

## 4. Chi tiết 50 yêu cầu

Cột đầu ra dưới đây là **đích yêu cầu trong plan**, không khẳng định mọi đầu ra đã nghiệm thu. Trạng thái là checkpoint hiện ghi; partial evidence và các cập nhật trên giải thích phần đã bổ sung. “Bước tiếp theo” trong sổ có thể là câu cũ, cần đọc cùng remaining của checkpoint mới nhất.

### P1 — Retail

#### P1.01 — Dữ liệu & target

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** UCI350: khách hàng thẻ Taiwan; bill/payment/status sáu tháng; target tháng kế tiếp.

**Đầu ra đích của plan:** Source profile, target card, split support và giới hạn population.

**Điều kiện nghiệm thu:** Client/history counts reconcile; source ID không là predictor; tháng và missing sentinels có nghĩa rõ.

**Bước tiếp theo ghi trong sổ:** Thêm cohort theo thời gian và nguồn phù hợp thị trường muốn triển khai.

- Nghiệm thu: p1-data-target-full-current-requirement. Current source/target/month/missing-category/split/population contract;hash-verified pre-freeze full-row parity,current footers and aggregate consistency;no new final predictor read or model change;temporal/Vietnam/intended-use qualification remains open
  Báo cáo: [P1_DATA_TARGET_ACCEPTANCE_VI.md](P1_DATA_TARGET_ACCEPTANCE_VI.md).
- Evidence: 2026-10-11. Verified acquisition aggregate source-quality projection into monitor/review/Excel; not full semantic/OOT acceptance

#### P1.02 — Application underwriting

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Application-time income, bureau, requested amount, decision date; booked performance và reject population.

**Đầu ra đích của plan:** Application score, decision rationale, cutoff/capacity analysis và model card.

**Điều kiện nghiệm thu:** Không dùng bill/status sau booking làm approval-time feature; có OOT và intended-use review.

**Bước tiếp theo ghi trong sổ:** Thiết kế application schema và lấy nguồn có quyền truy cập trước khi fit.

- Evidence: lendingclub-published-source-20261012. Public API/publisher hash396562202bytes;1055054rows/90columns/94954860positions,90missingness/11numeric profiles,105monthly status cells,terminal label encoding and joint/individual coverage
  Phần còn thiếu tại checkpoint: API/UI,dictionary/preprocessing provenance,application availability,full booked/reject population,event horizon/maturity and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_SOURCE_PROFILE_VI.md](LENDINGCLUB_SOURCE_PROFILE_VI.md).
- Evidence: lendingclub-source-explorer-20261012. Publisher-hash checked privateAPI/UI/export,booking-month/status/field filters,source-cohort chart,whole-source90column missingness/numeric profiles,label encoding,URL reload,mobile,outage/guard
  Phần còn thiếu tại checkpoint: Original fidelity/dictionary/preprocessing,application decision chronology,reject/full-booked population,event horizon/maturity and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_SOURCE_PROFILE_VI.md](LENDINGCLUB_SOURCE_PROFILE_VI.md).
- Evidence: lendingclub-issuer-dictionary-20261012. Issuer-hosted XLSX280definitions/560cells;90prepared columns86exact/2proposedaliases/2undefined;DTI/income/amount caveats,cell-source references,privateAPI/UI/export and exclusions pending review
  Phần còn thiếu tại checkpoint: Contributor preprocessing/unit/time provenance,application decision dates,reject/full-booked population,event horizon/maturity,intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_DICTIONARY_REVIEW_VI.md](LENDINGCLUB_DICTIONARY_REVIEW_VI.md).
- Evidence: lendingclub-full-publisher-source-20261012. Public publisher version3,GZIPsize/CRC,2260701accepted/27648741rejected rows,160column missingness,830monthly category cells,active/late/terminal states and separate funded/application grains;publisher helper code captured not executed
  Phần còn thiếu tại checkpoint: API/UI,snapshot/feature availability,original issuer fidelity/rights,application decision dates,comparable eligible populations,event horizon/maturity,borrower grouping and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_FULL_SOURCE_VI.md](LENDINGCLUB_FULL_SOURCE_VI.md).
- Evidence: lendingclub-full-source-explorer-20261012. Separate accepted funded-month/rejected application-day privateAPI/UI/export;category windows,151/9whole-source quality tables,active/missing statuses,URL/reset/mobile/outage and raw/dated/missing denominators
  Phần còn thiếu tại checkpoint: Snapshot/feature availability,original issuer fidelity/rights,application decision dates,comparable eligible populations,event horizon/maturity,borrower grouping and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_FULL_SOURCE_VI.md](LENDINGCLUB_FULL_SOURCE_VI.md).
- Evidence: lendingclub-temporal-evidence-20261012. Four source date roles/min/max,1024cohort/term groups5120metrics,payment-span/chronology counts,source-scoped privateAPI/UI/export and rejected-not-applicable handling
  Phần còn thiếu tại checkpoint: Certified observation cutoff,event/exits/censoring history,application-time features,borrower identity,mature support and intended-use/entity-safe OOT protocol;payment span not maturity proof
  Tài liệu: [LENDINGCLUB_TEMPORAL_READINESS_VI.md](LENDINGCLUB_TEMPORAL_READINESS_VI.md).

#### P1.03 — Behavioral model & validation

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Train/calibration/validation/final-test client splits; history features; saved constant/logistic/boosting results.

**Đầu ra đích của plan:** AUC/AP/Brier/log loss, reliability bins, paired uncertainty và selected model.

**Điều kiện nghiệm thu:** Không tune trên final test; random split được ghi rõ; bin rỗng không vẽ thành zero.

**Bước tiếp theo ghi trong sổ:** Thêm cohort ngoài thời gian; kiểm tra calibration theo population triển khai.

- Nghiệm thu: p1-behavioral-validation-full-current-requirement. Current historical random-cohort benchmark validation,independent six-variant metrics/bins/bootstrap/selection evidence,private suite export;no actual refit/rescore/final predictor reads;temporal/deployment/production qualification remains open
  Báo cáo: [P1_BEHAVIORAL_VALIDATION_ACCEPTANCE_VI.md](P1_BEHAVIORAL_VALIDATION_ACCEPTANCE_VI.md).

#### P1.04 — Decision policy

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Validation scores; lower/upper thresholds; sáu action×outcome costs; review capacity.

**Đầu ra đích của plan:** Action counts, expected declared cost, retrospective proxy, capacity overflow; preview/version/export.

**Điều kiện nghiệm thu:** Không tự reassignment khi vượt capacity; cost units không tự gọi là cash loss; validation comparisons là exploratory.

**Bước tiếp theo ghi trong sổ:** Đo chi phí vận hành thật, daily inflow và reject outcomes trước policy production.

- Nghiệm thu: p1-04-saved-policy-subgroup-full-current-requirement. Current historical validation policy/subgroup workflow,source/numerical reconciliation,immutable QA persistence and scoped export;all serving paths avoid inference;actual economics,temporal monitoring,fairness/production qualification remain open
  Báo cáo: [P1_POLICY_SUBGROUP_ACCEPTANCE_VI.md](P1_POLICY_SUBGROUP_ACCEPTANCE_VI.md).
- Evidence: policy-saved-score-serving-no-inference. Policy APIs verify saved freeze graph and replay Fraction costs without model inference;isolated QA persistence;source/model unchanged
  Phần còn thiếu tại checkpoint: Subgroup catalog on same screen still follows legacy deep verification;full-screen no-inference probe and serving reconciliation remain required;real economic/treatment qualification unavailable
  Tài liệu: [P1_POLICY_SAVED_SERVING_CHECKPOINT_VI.md](P1_POLICY_SAVED_SERVING_CHECKPOINT_VI.md).

#### P1.05 — Affordability

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Verified income, recurring expenses, debt payments, household scope và loan schedule.

**Đầu ra đích của plan:** Affordability assessment và phần thiếu chứng từ.

**Điều kiện nghiệm thu:** Không suy income từ credit limit; DTI phải ghi denominator, kỳ và policy threshold.

**Bước tiếp theo ghi trong sổ:** Thêm intake income/cash-flow và debt-obligation schema.

- Evidence: lendingclub-published-source-20261012. Public API/publisher hash396562202bytes;1055054rows/90columns/94954860positions,90missingness/11numeric profiles,105monthly status cells,terminal label encoding and joint/individual coverage
  Phần còn thiếu tại checkpoint: API/UI,dictionary/preprocessing provenance,application availability,full booked/reject population,event horizon/maturity and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_SOURCE_PROFILE_VI.md](LENDINGCLUB_SOURCE_PROFILE_VI.md).
- Evidence: lendingclub-source-explorer-20261012. Publisher-hash checked privateAPI/UI/export,booking-month/status/field filters,source-cohort chart,whole-source90column missingness/numeric profiles,label encoding,URL reload,mobile,outage/guard
  Phần còn thiếu tại checkpoint: Original fidelity/dictionary/preprocessing,application decision chronology,reject/full-booked population,event horizon/maturity and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_SOURCE_PROFILE_VI.md](LENDINGCLUB_SOURCE_PROFILE_VI.md).
- Evidence: lendingclub-issuer-dictionary-20261012. Issuer-hosted XLSX280definitions/560cells;90prepared columns86exact/2proposedaliases/2undefined;DTI/income/amount caveats,cell-source references,privateAPI/UI/export and exclusions pending review
  Phần còn thiếu tại checkpoint: Contributor preprocessing/unit/time provenance,application decision dates,reject/full-booked population,event horizon/maturity,intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_DICTIONARY_REVIEW_VI.md](LENDINGCLUB_DICTIONARY_REVIEW_VI.md).
- Evidence: lendingclub-full-publisher-source-20261012. Public publisher version3,GZIPsize/CRC,2260701accepted/27648741rejected rows,160column missingness,830monthly category cells,active/late/terminal states and separate funded/application grains;publisher helper code captured not executed
  Phần còn thiếu tại checkpoint: API/UI,snapshot/feature availability,original issuer fidelity/rights,application decision dates,comparable eligible populations,event horizon/maturity,borrower grouping and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_FULL_SOURCE_VI.md](LENDINGCLUB_FULL_SOURCE_VI.md).
- Evidence: lendingclub-full-source-explorer-20261012. Separate accepted funded-month/rejected application-day privateAPI/UI/export;category windows,151/9whole-source quality tables,active/missing statuses,URL/reset/mobile/outage and raw/dated/missing denominators
  Phần còn thiếu tại checkpoint: Snapshot/feature availability,original issuer fidelity/rights,application decision dates,comparable eligible populations,event horizon/maturity,borrower grouping and intended-use/OOT qualification
  Tài liệu: [LENDINGCLUB_FULL_SOURCE_VI.md](LENDINGCLUB_FULL_SOURCE_VI.md).
- Evidence: affordability-intake-engine-api-20261012. Explicit gross/net/expenses/debt/proposed/household/currency/date intake,exact period normalization,DTI/residual/declared policy/sensitivity,missing-zero-expiry/coverage/duplicate guards and private same-originPOST/export
  Phần còn thiếu tại checkpoint: UI and source-document/Excel intake,verified income/debt/expense evidence,coverage/overlap review,policy ownership and intended-use qualification;no credit decision or actual verification from declared references
  Tài liệu: [AFFORDABILITY_INTAKE_VI.md](AFFORDABILITY_INTAKE_VI.md).
- Evidence: affordability-excel-intake-20261012. Bounded value-only XLSX intake,cell lineage/hash,private API,form hydration and exact DTI/residual reassessment;zero/missing/expiry/formula/precision/HTTP/browser guards
  Phần còn thiếu tại checkpoint: Template workbook,actual income/obligation source documents,verification ownership,household completeness and semantic overlap review;no credit decision
  Tài liệu: [AFFORDABILITY_EXCEL_INTAKE_VI.md](AFFORDABILITY_EXCEL_INTAKE_VI.md).
- Evidence: affordability-excel-template-20261012. Blank guided XLSX template,native validation definitions,hash-guarded download route,Artifact Tool roundtrip,source-cell/form/export parity and native Excel read-only 38-cell checks
  Phần còn thiếu tại checkpoint: Actual income/debt documents,verification ownership,household completeness and semantic obligation overlap review;full native dropdown interaction not exercised
  Tài liệu: [AFFORDABILITY_EXCEL_INTAKE_VI.md](AFFORDABILITY_EXCEL_INTAKE_VI.md).

#### P1.06 — Limit & pricing

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Contract rate/fees, PD horizon, LGD/EAD, funding/capital costs, take-up và affordability.

**Đầu ra đích của plan:** Scenario economics, break-even và constraints.

**Điều kiện nghiệm thu:** Không gọi price tối ưu khi thiếu cost/take-up evidence; không mượn PD khác target.

**Bước tiếp theo ghi trong sổ:** Thu thập contract economics và thiết kế policy experiments.


#### P1.07 — Giải thích từng hồ sơ

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Frozen model, training reference, bốn feature groups và toàn bộ4499 validation clients.

**Đầu ra đích của plan:** Global contribution distributions, token search/paging, signed local contributions và private export.

**Điều kiện nghiệm thu:** Contributions cộng về prediction đúng tolerance; references/source pinned; không gọi là nguyên nhân hoặc adverse-action reason.

**Bước tiếp theo ghi trong sổ:** Kiểm tra reference sensitivity và qualification trước scoring hồ sơ mới.

- Nghiệm thu: p1-complete-cohort-audited-saved-explanations. Current4499-client historical benchmark explanation workflow;exact audit receipt/source bindings and fresh saved arithmetic/rank/token/distribution checks;no fresh model/coalition inference;reference sensitivity/intended-use/adverse-action/production qualification remain open
  Báo cáo: [P1_EXPLANATIONS_SAVED_ACCEPTANCE_VI.md](P1_EXPLANATIONS_SAVED_ACCEPTANCE_VI.md).

#### P1.08 — Collections workflow

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Delinquency/contact/actions/promises/payments, treatment timestamps và costs.

**Đầu ra đích của plan:** Work queue, cure/recovery outcomes và treatment economics.

**Điều kiện nghiệm thu:** Behavioral score không chứng minh uplift; không tạo SLA/contact events giả.

**Bước tiếp theo ghi trong sổ:** Thêm event-level collections data và analyst case ownership.


#### P1.09 — Subgroup & monitoring

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Validation demographics, predictions, labels; source-bound subgroup study.

**Đầu ra đích của plan:** Coverage, calibration/AUC/policy capture theo nhóm và exact export.

**Điều kiện nghiệm thu:** Bỏ demographic predictors không chứng minh fairness; small groups không được gán ranking metrics; chưa có temporal drift.

**Bước tiếp theo ghi trong sổ:** Thu thập monitoring cohorts theo thời gian và định nghĩa escalation thresholds.

- Nghiệm thu: p1-09-saved-policy-subgroup-full-current-requirement. Current historical validation policy/subgroup workflow,source/numerical reconciliation,immutable QA persistence and scoped export;all serving paths avoid inference;actual economics,temporal monitoring,fairness/production qualification remain open
  Báo cáo: [P1_POLICY_SUBGROUP_ACCEPTANCE_VI.md](P1_POLICY_SUBGROUP_ACCEPTANCE_VI.md).

#### P1.10 — Model evidence & governance

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Source contract, split support, saved model selection/holdout, uncertainty và limitations.

**Đầu ra đích của plan:** Model dossier, audit trail và reporting package; app đọc saved artifacts.

**Điều kiện nghiệm thu:** Không refit/rescore khi mở màn; benchmark Taiwan không trở thành Vietnam PD; chưa có authenticated sign-off.

**Bước tiếp theo ghi trong sổ:** Thêm model-review ownership, monitoring protocol và intended-use approval ngoài benchmark.

- Nghiệm thu: p1-model-dossier-full-current-requirement. Current source/target/split/selection/freeze/saved-evaluation dossier and audit-trail/reporting package;no inference/refit/rescore;owner/authenticated sign-off/monitoring/production intended-use qualification remain open
  Báo cáo: [P1_MODEL_DOSSIER_ACCEPTANCE_VI.md](P1_MODEL_DOSSIER_ACCEPTANCE_VI.md).


### P2 — Mortgage

#### P2.01 — Source & run explorer

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Freddie annual sample2012, raw receipt và run lineage.

**Đầu ra đích của plan:** Source/run context, lineage và data readiness.

**Điều kiện nghiệm thu:** Không gọi sample50k là toàn thị trường; không thay extraction time bằng publication time.

**Bước tiếp theo ghi trong sổ:** Thêm authorized annual vintages và reconcile từng acquisition.

- Nghiệm thu: p2-source-run-full-current-requirement. All current source/run explorer supplied-corpus lineage/coverage/readiness/sample/time requirements;publisher authentication and additional annual vintages remain unproven
  Báo cáo: [P2_SOURCE_RUN_ACCEPTANCE_VI.md](P2_SOURCE_RUN_ACCEPTANCE_VI.md).
- Evidence: fannie-public-samples-20261012. Official public SF8loans/757monthly rows108positions,MF4loans/241monthly rows62fields and17annual DSCR rows;7source files,historical/current schema caution,private API/UI/export and173field quality checks
  Phần còn thiếu tại checkpoint: Full authorized dataset/schema/representative multi-vintage support,horizon maturity and entity-safe OOT protocol;sample provides no additional Freddie vintage or qualified PD12 model
  Tài liệu: [FANNIE_PUBLIC_SAMPLES_VI.md](FANNIE_PUBLIC_SAMPLES_VI.md).
- Evidence: raw-receipt-release-provenance-finding. Supplied release47 declaration is not authenticated by publisher hash registry;byte consistency is not publication time or publisher release identity
  Tài liệu: [P2_PANEL_QUALITY_ACCEPTANCE_VI.md](P2_PANEL_QUALITY_ACCEPTANCE_VI.md).
- Evidence: receipt-backed-mortgage-provenance. Receipt declarations, publication unknown, distinct received/extraction/rebuild/case timestamps;fail-closed metadata API and scoped JSON;no source/model promotion
  Tài liệu: [P2_SOURCE_PROVENANCE_VI.md](P2_SOURCE_PROVENANCE_VI.md).

#### P2.02 — Panel quality

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Origination/performance panel, keys/months, sentinels và quality findings.

**Đầu ra đích của plan:** Quality issues, affected counts, source investigation evidence.

**Điều kiện nghiệm thu:** Unknown/gap không trở thành current; không nối qua khoảng thiếu dữ liệu.

**Bước tiếp theo ghi trong sổ:** Thêm cross-vintage quality checks và source reconciliation mới.

- Nghiệm thu: p2-panel-quality-full-current-requirement. All current P2.02 supplied-corpus quality/readout/unknown/gap requirements;publisher release/PIT authentication not claimed
  Báo cáo: [P2_PANEL_QUALITY_ACCEPTANCE_VI.md](P2_PANEL_QUALITY_ACCEPTANCE_VI.md).
- Evidence: fannie-public-samples-20261012. Official public SF8loans/757monthly rows108positions,MF4loans/241monthly rows62fields and17annual DSCR rows;7source files,historical/current schema caution,private API/UI/export and173field quality checks
  Phần còn thiếu tại checkpoint: Full authorized dataset/schema/representative multi-vintage support,horizon maturity and entity-safe OOT protocol;sample provides no additional Freddie vintage or qualified PD12 model
  Tài liệu: [FANNIE_PUBLIC_SAMPLES_VI.md](FANNIE_PUBLIC_SAMPLES_VI.md).

#### P2.03 — Portfolio & cohorts

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Observed loan-month states/UPB; segment, reporting-month filters và vintage labels.

**Đầu ra đích của plan:** Monthly charts, profile, selected-scope aggregate export.

**Điều kiện nghiệm thu:** Zero UPB giữ riêng; count và balance có denominator khác; không cộng duplicate loan-months thành unique loans.

**Bước tiếp theo ghi trong sổ:** Bổ sung nhiều origination vintages và standardize composition comparisons.

- Nghiệm thu: p2-portfolio-full-current-requirement. All current P2.03 monthly/profile/filter/zero/denominator requirements;ledger basis display corrected;multi-vintage composition remains next-stage work
  Báo cáo: [P2_PORTFOLIO_ACCEPTANCE_VI.md](P2_PORTFOLIO_ACCEPTANCE_VI.md).

#### P2.04 — Private loan lifecycle

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Run-scoped pseudonymous loan key, observed states/UPB và confirmed events.

**Đầu ra đích của plan:** Timeline, observed UPB chart và source-backed event detail.

**Điều kiện nghiệm thu:** Không lộ raw loan ID; không coi observed timeline là forecast; không backdate confirmation.

**Bước tiếp theo ghi trong sổ:** Thêm search/paging lớn hơn và review gắn loan khi contract được chốt.

- Nghiệm thu: p2-lifecycle-full-current-requirement-20261012. All current P2.04 source-backed/private/observed timeline requirements;stale context defect fixed;extended paging/loan-review remains next-stage work
  Báo cáo: [P2_LIFECYCLE_ACCEPTANCE_VI.md](P2_LIFECYCLE_ACCEPTANCE_VI.md).

#### P2.05 — Transition matrix

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Adjacent loan-month pairs; opening UPB; selected reporting year/segment.

**Đầu ra đích của plan:** Matrix, selected-cell detail và year-scoped export.

**Điều kiện nghiệm thu:** Không nối gaps/terminal pairs sai; năm không có pairs giữ unavailable; lifetime comparator ghi rõ scope.

**Bước tiếp theo ghi trong sổ:** Thêm temporal comparison và confidence intervals khi có đủ vintages.

- Nghiệm thu: p2-transition-full-current-requirement-20261012. All explicit current P2.05 inputs/outputs/acceptance on official2012 descriptive case;next-stage CI/multi-vintage/OOT requirements remain open
  Báo cáo: [P2_TRANSITION_ACCEPTANCE_VI.md](P2_TRANSITION_ACCEPTANCE_VI.md).

#### P2.06 — Cure & redefault

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** D3 episodes, CURRENT nonterminal consecutive months, gaps và follow-up windows.

**Đầu ra đích của plan:** Episode events, follow-up support và loan timeline.

**Điều kiện nghiệm thu:** Gap/unknown phá linkage; terminal CURRENT không thành cure; follow-up thiếu không thành no-event.

**Bước tiếp theo ghi trong sổ:** Đánh giá time-to-cure/redefault trên nhiều cohorts với censoring protocol.

- Nghiệm thu: p2-cure-full-current-requirement-20261012. All current P2.06 episode/follow-up/timeline requirements on official2012 panel;multi-cohort time-to-event/censoring extension remains open
  Báo cáo: [P2_CURE_ACCEPTANCE_VI.md](P2_CURE_ACCEPTANCE_VI.md).

#### P2.07 — Competing outcomes

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Early-entry eligible loans, horizon6/12/24m, endpoint observations và censoring.

**Đầu ra đích của plan:** Cohort support, incidence/exits charts và target exclusions.

**Điều kiện nghiệm thu:** Không gọi horizon connector là monthly prediction; censored/unknown không thành negative.

**Bước tiếp theo ghi trong sổ:** Thêm survival/competing-risk model khi temporal cohorts đạt gate.

- Nghiệm thu: p2-competing-full-current-requirement-20261012. All current P2.07 cohort/incidence/exits/exclusion and unavailable semantics on official2012 panel;next-stage temporal survival/model work remains open
  Báo cáo: [P2_COMPETING_ACCEPTANCE_VI.md](P2_COMPETING_ACCEPTANCE_VI.md).

#### P2.08 — Horizon risk models

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Nhiều origination vintages, macro availability, frozen temporal splits và final OOT.

**Đầu ra đích của plan:** Prepared study, gate reasons; model metrics chỉ sau khi gate đạt.

**Điều kiện nghiệm thu:** Một vintage2012 chưa đủ temporal evaluation; readiness screen không là qualified score.

**Bước tiếp theo ghi trong sổ:** Tải thêm authorized vintages và chốt R2–R3 trong PLAN_MODULE_01.

- Evidence: fannie-public-samples-20261012. Official public SF8loans/757monthly rows108positions,MF4loans/241monthly rows62fields and17annual DSCR rows;7source files,historical/current schema caution,private API/UI/export and173field quality checks
  Phần còn thiếu tại checkpoint: Full authorized dataset/schema/representative multi-vintage support,horizon maturity and entity-safe OOT protocol;sample provides no additional Freddie vintage or qualified PD12 model
  Tài liệu: [FANNIE_PUBLIC_SAMPLES_VI.md](FANNIE_PUBLIC_SAMPLES_VI.md).

#### P2.09 — Observed loss bridge

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Source loss/recovery/cost fields, observation periods và terminal information.

**Đầu ra đích của plan:** Loss components/coverage, reconciliation và selected-scope export.

**Điều kiện nghiệm thu:** Không fill missing bằng zero; sample không representative LGD calibration; UPB không tự là economic loss.

**Bước tiếp theo ghi trong sổ:** Thêm recovery timing/contract data và mature loss cohorts.

- Nghiệm thu: p2-observed-loss-full-current-requirement. Current supplied-corpus observed loss bridge,exact component/expense reconciliation,coverage,signs and scoped exports;legacy magnitude clarified,signed diagnostic added;qualified LGD/ECL and recovery timing remain open
  Báo cáo: [P2_OBSERVED_LOSS_ACCEPTANCE_VI.md](P2_OBSERVED_LOSS_ACCEPTANCE_VI.md).
- Evidence: freddie-public-loss-reference. Official 23-page January2026 guide and Clarity acquisition announcement;loss sign/revision/modification cautions;no annual vintage or model added
  Phần còn thiếu tại checkpoint: Whole-corpus source/formula/coverage/terminal reconciliation and UI/export audit;recovery timing and mature loss cohorts
  Tài liệu: [FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md](FREDDIE_PUBLIC_REFERENCE_REVIEW_VI.md).

#### P2.10 — Evidence & review

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Current run/view/filters, quality/target/numerical evidence và reviewer text.

**Đầu ra đích của plan:** Private findings, review history và evidence reports.

**Điều kiện nghiệm thu:** Không sửa source bằng memo; reviewed không là authenticated bank approval.

**Bước tiếp theo ghi trong sổ:** Thêm identity/roles và formal review policy khi triển khai nhóm.

- Nghiệm thu: p2-private-finding-review-full-current-requirement. All current local draft/revision/reopen/history/evidence-report requirements;modal context preserved;no source mutation or authenticated bank approval;identity/roles/team policy remain open
  Báo cáo: [P2_FINDING_REVIEW_ACCEPTANCE_VI.md](P2_FINDING_REVIEW_ACCEPTANCE_VI.md).


### P3 — Business

#### P3.01 — SME source explorer

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Sáu SBA FOIA files, dictionary, program/status/date fields.

**Đầu ra đích của plan:** Source dictionary, counts và quality evidence.

**Điều kiện nghiệm thu:** Không cộng files thành unique borrowers nếu chưa có identity; giữ EXEMPT/unknown/cancelled.

**Bước tiếp theo ghi trong sổ:** Thêm historical snapshots và documented loan key qualification.

- Nghiệm thu: p3-sba-descriptive-full-current-requirements. Current June six-source dictionary/quality/status/FY/sector/geography descriptive workflow;whole raw-to-canonical and all1197marts cells parity;81fields162dictionarycells,12scope downloads and1197share denominators;not unique borrowers,EAD,fixed-horizon PD or whole SME market
  Báo cáo: [P3_SBA_DESCRIPTIVE_ACCEPTANCE_VI.md](P3_SBA_DESCRIPTIVE_ACCEPTANCE_VI.md).
- Evidence: sba-march-historical-archive-20261014. Six separately acquired March CSVs,885226430bytes,2174502source records;whole-file independent CSV/Decimal audit;hash-verified aggregate-only program/status/exact-amount report;no frozen-case change
  Phần còn thiếu tại checkpoint: Archive API/UI/export parity,current June requirement-level audit;historical schema/subprogram semantics,identity,transitions,publication timing and fixed-horizon PD remain unqualified
  Tài liệu: [SBA_HISTORICAL_ARCHIVE_VI.md](SBA_HISTORICAL_ARCHIVE_VI.md).
- Evidence: sba-march-historical-archive-api-ui-20261014. Six March CSVs,2174502source records;independent CSV/Decimal audit;hash-verified API/UI/program-status/exact-amount report/export;21backend/HTTP tests and5actual-browser groups PASS;reload/mobile/outage-retry;frozen June case unchanged
  Phần còn thiếu tại checkpoint: Current June requirement-level source/numerical/browser/export audit;historical schema/subprogram semantics,identity,transitions,publication timing and fixed-horizon PD remain unqualified
  Tài liệu: [SBA_HISTORICAL_ARCHIVE_VI.md](SBA_HISTORICAL_ARCHIVE_VI.md).

#### P3.02 — Financial normalization

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Companyfacts/submissions, concepts/units/start/end/accession/filing date.

**Đầu ra đích của plan:** Field values/status, source units/periods và concept evidence.

**Điều kiện nghiệm thu:** Không ghép quarterly/YTD thành annual theo fiscal-year label; conflicts không chọn alias đẹp hơn.

**Bước tiếp theo ghi trong sổ:** Mở rộng issuer/taxonomy mapping và kiểm tra historical availability.

- Nghiệm thu: p3-sec-normalization-full-current-requirement. Current four-issuer source-native SEC normalization;105441facts13374filings/occurrences,67annual536fields,allcandidate evidence;native units/periods/conflicts preserved;original full verification plus hash-guarded serialized cache;67actual HTTP reports32UIfields/export/reload/mobile/cutoff;no PIT,complete custom taxonomy,issuerPD or production qualification
  Báo cáo: [P3_SEC_NORMALIZATION_ACCEPTANCE_VI.md](P3_SEC_NORMALIZATION_ACCEPTANCE_VI.md).
- Evidence: sec-normalization-whole-source-independent-audit-20261014. Independent raw JSON/Decimal full105441facts13374filings and occurrences,definitions/quality,67annual statements536fields;468supported48missing20ambiguous;batch512 exact parity,not sampling;33testsPASS;source/canonical/code unchanged
  Phần còn thiếu tại checkpoint: 67statement actual API/browser/export acceptance;initial runtime503 not yet diagnosed;historical publication availability and corporate scoring qualification remain open
  Tài liệu: [P3_SEC_NORMALIZATION_AUDIT_VI.md](P3_SEC_NORMALIZATION_AUDIT_VI.md).

#### P3.03 — Financial ratio analysis

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Normalized SEC fields/filings, explicit expense concept, exact units/durations và original 10-K selection.

**Đầu ra đích của plan:** Ratio cards, actual/delta tables, numerator-first driver bridge với exact source inputs/counterfactual/effects/residual, baseline statements, Interest coverage tab với candidate evidence và private trend/coverage JSON và Analysis/Facts Excel với server-derived inputs/formulas/source evidence.

**Điều kiện nghiệm thu:** Amendments giữ riêng; không skip gaps/concept changes; không đổi cash interest thành expense; operating-income/OCF proxies chưa là EBIT ICR, DSCR hoặc covenant.

**Bước tiếp theo ghi trong sổ:** Thêm borrower debt-service/covenant inputs và peer/sector comparisons có consistent accounting scope.

- Nghiệm thu: p3-financial-ratio-analysis-full-current-requirement. Fourissuer filing-specific ratios/trends/ordered driver bridge/explicit interest-coverage proxies;source/gates and actual API/UI/JSON;all36 Analysis/Facts Excel scopes exact metadata+native73656cells14040formulas;216native cases432reads;native visual+UIexport/outage;no EBITICR/DSCR/covenant/issuerPD/PIT qualification
  Báo cáo: [P3_RATIO_ANALYSIS_ACCEPTANCE_VI.md](P3_RATIO_ANALYSIS_ACCEPTANCE_VI.md).
- Evidence: utility-debt-source-api-20261011. EBMUD two systems,20 continuing records/260 positions,60 rounded ACFR records/300 positions,40 rational DSCR checks,source/profile integrity and private API/export
  Phần còn thiếu tại checkpoint: UI/browser,full indenture/amendment/applicable covenant qualification; does not replace corporate/mortgage debt-service inputs
  Tài liệu: [UTILITY_DEBT_SERVICE_VI.md](UTILITY_DEBT_SERVICE_VI.md).
- Evidence: utility-debt-ui-20261011. Dedicated EBMUD pane,edition/system/year/lien filters,source input/timeline/bridges/rounded-source mismatch,private exact export,URL reload,mobile,outage recovery and unchanged holdout ledger
  Phần còn thiếu tại checkpoint: Full indenture/amendment/applicable covenant qualification;actual corporate/mortgage debt-service inputs remain missing
  Tài liệu: [UTILITY_DEBT_SERVICE_VI.md](UTILITY_DEBT_SERVICE_VI.md).
- Evidence: utility-covenant-description-20261011. Two dated official statements590pages,22selected evidence pages,reported1.1x covenant vs1.6xpolicy,definition continuations,proposed amendment/certificate/default caveats,privateAPI/UI/export
  Phần còn thiếu tại checkpoint: Executed full indenture chain,trustee certificate/effective date,historical applicability and test reconciliation;legal threshold/headroom/compliance remain null
  Tài liệu: [UTILITY_COVENANT_EVIDENCE_VI.md](UTILITY_COVENANT_EVIDENCE_VI.md).
- Evidence: utility-dscr-driver-20261011. 32exact adjacent-year DSCR accounting bridges,8unavailable priors,revenue/O&M/source-residual/debt-service effects,counterfactual/input evidence,privateAPI/export and five-year reported DSCR chart
  Phần còn thiếu tại checkpoint: Causal/economic drivers,qualified historical legal scope/headroom/compliance and actual corporate/mortgage debt-service inputs
  Tài liệu: [UTILITY_DSCR_DRIVERS_VI.md](UTILITY_DSCR_DRIVERS_VI.md).
- Evidence: p3-ratio-trend-coverage-source-runtime-audit-20261015. All268saved ratios201supported67unavailable;48trendHTTPscopes552comparisons360exact/rationalbridges;60explicit-expensecoverageHTTPscopes/rawcandidates;4issuer trend/coverage browser,exports/mobile/outage/reload and36testsPASS;no source/model change
  Phần còn thiếu tại checkpoint: Current complete Analysis/Facts Excel source/formula/filter/precision/missing qualification and final original requirement audit;ICR/DSCR/covenant/issuerPD/PIT qualifications remain unavailable
  Tài liệu: [P3_RATIO_TREND_AUDIT_VI.md](P3_RATIO_TREND_AUDIT_VI.md).
- Evidence: p3-sec-excel-36-scope-native-baseline-20261015. 36issuer/window/expense API captures,XLSX/JSON scope+SHA parity,independent XML/Fraction arithmetic/missing guards;native Excel16 fullrebuild73656cells14040formulas on36unsaved copies;43testsPASS;source/builder unchanged
  Phần còn thiếu tại checkpoint: Full Facts metadata/date/summary audit,current-copy native input perturbations,current render and browser download/outage scope acceptance
  Tài liệu: [P3_SEC_EXCEL_SCOPE_AUDIT_VI.md](P3_SEC_EXCEL_SCOPE_AUDIT_VI.md).
- Evidence: 2026-10-11. Six saved workbook native baselines and18representative memory-input cases; SEC blank-to-zero fixed; not full capability qualification

#### P3.04 — Bankruptcy benchmark

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** UCI365 original ARFF; subset5 one-year label; frozen splits/model/calibration.

**Đầu ra đích của plan:** Saved validation/holdout metrics, uncertainty và model card.

**Điều kiện nghiệm thu:** Không pool five horizons thành một PD; thiếu firm IDs/publication dates nên chưa entity-disjoint/OOT.

**Bước tiếp theo ghi trong sổ:** Thu thập identified dated statements cho deployed corporate-risk study.

- Nghiệm thu: p3-bankruptcy-benchmark-full-current-requirement. Original UCI365 one-year source-statement benchmark; frozen source/split/selection/ledger graph, five validation candidates and one saved final, independent 24000 bootstrap metric cells/180 paired interval cells, actual aggregate UI/export and model card. No new final predictor reads, refit or inference; entity/OOT/production qualification remains false.
  Báo cáo: [P3_BANKRUPTCY_BENCHMARK_ACCEPTANCE_VI.md](P3_BANKRUPTCY_BENCHMARK_ACCEPTANCE_VI.md).

#### P3.05 — SBA outcomes & cohorts

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Program,status,approval fiscal year,NAICS/geography và reported amounts.

**Đầu ra đích của plan:** Status explorer, selected cohort/detail và decimal-preserving export.

**Điều kiện nghiệm thu:** Terminal snapshot không là fixed-horizon PD; post-outcome fields không làm approval predictors.

**Bước tiếp theo ghi trong sổ:** Thêm longitudinal status dates/coverage trước survival or default modeling.

- Nghiệm thu: p3-sba-descriptive-full-current-requirements. Current June six-source dictionary/quality/status/FY/sector/geography descriptive workflow;whole raw-to-canonical and all1197marts cells parity;81fields162dictionarycells,12scope downloads and1197share denominators;not unique borrowers,EAD,fixed-horizon PD or whole SME market
  Báo cáo: [P3_SBA_DESCRIPTIVE_ACCEPTANCE_VI.md](P3_SBA_DESCRIPTIVE_ACCEPTANCE_VI.md).
- Evidence: sba-march-historical-archive-20261014. Six separately acquired March CSVs,885226430bytes,2174502source records;whole-file independent CSV/Decimal audit;hash-verified aggregate-only program/status/exact-amount report;no frozen-case change
  Phần còn thiếu tại checkpoint: Archive API/UI/export parity,current June requirement-level audit;historical schema/subprogram semantics,identity,transitions,publication timing and fixed-horizon PD remain unqualified
  Tài liệu: [SBA_HISTORICAL_ARCHIVE_VI.md](SBA_HISTORICAL_ARCHIVE_VI.md).
- Evidence: sba-march-historical-archive-api-ui-20261014. Six March CSVs,2174502source records;independent CSV/Decimal audit;hash-verified API/UI/program-status/exact-amount report/export;21backend/HTTP tests and5actual-browser groups PASS;reload/mobile/outage-retry;frozen June case unchanged
  Phần còn thiếu tại checkpoint: Current June requirement-level source/numerical/browser/export audit;historical schema/subprogram semantics,identity,transitions,publication timing and fixed-horizon PD remain unqualified
  Tài liệu: [SBA_HISTORICAL_ARCHIVE_VI.md](SBA_HISTORICAL_ARCHIVE_VI.md).

#### P3.06 — Corporate credit memo

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Verified SEC filing facts/annual trend; issuer-event/debt/covenant sources còn cần bổ sung.

**Đầu ra đích của plan:** Financial memo editor, issuer-scoped list, original evidence digest, atomic history và private full JSON export.

**Điều kiện nghiệm thu:** Reviewed là self-declared analyst status; không issuer PD hoặc credit approval; thiếu source mới không ghi đè capture cũ.

**Bước tiếp theo ghi trong sổ:** Thêm issuer-event sources và borrower debt/covenant inputs cho complete credit memo.

- Nghiệm thu: p3-corporate-financial-memo-full-current-requirement. Verified financial memo editor/list/immutable source digest/atomic history/full private JSON; eight capture scopes and two real isolated UI/HTTP four-revision/outage/conflict/boundary cases; issuer metadata timeline2147rows48calls and browser;50tests. Self-declared owner/review; no issuerPD/approval/DSCR/covenant or full-text event qualification.
  Báo cáo: [P3_CORPORATE_MEMO_ACCEPTANCE_VI.md](P3_CORPORATE_MEMO_ACCEPTANCE_VI.md).

#### P3.07 — Covenant workbench

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Signed facility/covenant terms, definitions, test dates và permitted adjustments.

**Đầu ra đích của plan:** Headroom, supported breach assessment và supporting calculations.

**Điều kiện nghiệm thu:** Thiếu terms thì không gắn actual breach badge; SEC generic ratios không thay contract definitions.

**Bước tiếp theo ghi trong sổ:** Tạo covenant-term intake và source-backed adjustment ledger.

- Evidence: utility-debt-source-api-20261011. EBMUD two systems,20 continuing records/260 positions,60 rounded ACFR records/300 positions,40 rational DSCR checks,source/profile integrity and private API/export
  Phần còn thiếu tại checkpoint: UI/browser,full indenture/amendment/applicable covenant qualification; does not replace corporate/mortgage debt-service inputs
  Tài liệu: [UTILITY_DEBT_SERVICE_VI.md](UTILITY_DEBT_SERVICE_VI.md).
- Evidence: utility-debt-ui-20261011. Dedicated EBMUD pane,edition/system/year/lien filters,source input/timeline/bridges/rounded-source mismatch,private exact export,URL reload,mobile,outage recovery and unchanged holdout ledger
  Phần còn thiếu tại checkpoint: Full indenture/amendment/applicable covenant qualification;actual corporate/mortgage debt-service inputs remain missing
  Tài liệu: [UTILITY_DEBT_SERVICE_VI.md](UTILITY_DEBT_SERVICE_VI.md).
- Evidence: utility-covenant-description-20261011. Two dated official statements590pages,22selected evidence pages,reported1.1x covenant vs1.6xpolicy,definition continuations,proposed amendment/certificate/default caveats,privateAPI/UI/export
  Phần còn thiếu tại checkpoint: Executed full indenture chain,trustee certificate/effective date,historical applicability and test reconciliation;legal threshold/headroom/compliance remain null
  Tài liệu: [UTILITY_COVENANT_EVIDENCE_VI.md](UTILITY_COVENANT_EVIDENCE_VI.md).
- Evidence: checkpoint. 10disclosed facility versions; minimum/definition clause evidence; not full debt-service/headroom
- Evidence: checkpoint. 34facilities+events tests
- Evidence: checkpoint. 5browser/source/export/mobile/outage groupsPASS

#### P3.08 — Debt & cash-flow schedule

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Verified SEC selected-filing instant facts theo explicit debt-only/debt-capital-lease family; facility dates/coupons/cashflows còn thiếu.

**Đầu ra đích của plan:** Debt maturities tab, exact buckets/candidates/definitions, subtotal/total/first-three-years share, private JSON/Excel Maturities/Facts với23formulas; new memo capture.

**Điều kiện nghiệm thu:** Principal buckets không là exact payment dates, carrying debt, EAD hoặc DSCR; after-year-five open ended; debt/lease families không cộng overlap.

**Bước tiếp theo ghi trong sổ:** Thu thập instrument/facility terms, actual payment dates và interest/cash-flow inputs; qualify full debt-service schedule và covenant definitions khi inputs available.

- Evidence: utility-debt-source-api-20261011. EBMUD two systems,20 continuing records/260 positions,60 rounded ACFR records/300 positions,40 rational DSCR checks,source/profile integrity and private API/export
  Phần còn thiếu tại checkpoint: UI/browser,full indenture/amendment/applicable covenant qualification; does not replace corporate/mortgage debt-service inputs
  Tài liệu: [UTILITY_DEBT_SERVICE_VI.md](UTILITY_DEBT_SERVICE_VI.md).
- Evidence: utility-debt-ui-20261011. Dedicated EBMUD pane,edition/system/year/lien filters,source input/timeline/bridges/rounded-source mismatch,private exact export,URL reload,mobile,outage recovery and unchanged holdout ledger
  Phần còn thiếu tại checkpoint: Full indenture/amendment/applicable covenant qualification;actual corporate/mortgage debt-service inputs remain missing
  Tài liệu: [UTILITY_DEBT_SERVICE_VI.md](UTILITY_DEBT_SERVICE_VI.md).
- Evidence: utility-covenant-description-20261011. Two dated official statements590pages,22selected evidence pages,reported1.1x covenant vs1.6xpolicy,definition continuations,proposed amendment/certificate/default caveats,privateAPI/UI/export
  Phần còn thiếu tại checkpoint: Executed full indenture chain,trustee certificate/effective date,historical applicability and test reconciliation;legal threshold/headroom/compliance remain null
  Tài liệu: [UTILITY_COVENANT_EVIDENCE_VI.md](UTILITY_COVENANT_EVIDENCE_VI.md).
- Evidence: utility-dscr-driver-20261011. 32exact adjacent-year DSCR accounting bridges,8unavailable priors,revenue/O&M/source-residual/debt-service effects,counterfactual/input evidence,privateAPI/export and five-year reported DSCR chart
  Phần còn thiếu tại checkpoint: Causal/economic drivers,qualified historical legal scope/headroom/compliance and actual corporate/mortgage debt-service inputs
  Tài liệu: [UTILITY_DSCR_DRIVERS_VI.md](UTILITY_DSCR_DRIVERS_VI.md).
- Evidence: p3-maturity-whole-source-api-excel-native-baseline-20261015. 67filings2families134APIscopes804buckets exact raw candidates/definitions/summary;8latestExcel captures;native1408cells184formulas;current JSON/Excel browser,exports/reload/mobile/outage and23testsPASS;source/production calculations unchanged
  Phần còn thiếu tại checkpoint: Full maturity Facts metadata/summary,date/native perturbation+visual and new memo capture/source freshness/history/export;actual facility/coupon/cashflow qualification remains missing
  Tài liệu: [P3_MATURITY_SOURCE_AUDIT_VI.md](P3_MATURITY_SOURCE_AUDIT_VI.md).
- Evidence: p3-maturity-metadata-native-visual-memo-20261015. Complete delivered SEC bucket workflow evidence: 134 API scopes, 8 Excel scopes, metadata, 48 native input cases/336 checks, 16 native images, 8 isolated synthetic memo histories, 33 tests. Actual facility payment/coupon/calendar/outstanding and full debt service remain unqualified.
  Phần còn thiếu tại checkpoint: Instrument terms/effective amendments, actual balances and dated principal/interest payments, calendar qualification; memo full UI/review-package acceptance is separately open under P3.06/P3.10.
  Tài liệu: [P3_MATURITY_SOURCE_AUDIT_VI.md](P3_MATURITY_SOURCE_AUDIT_VI.md).
- Evidence: apple-annual-debt-source-bridge-20261015. Issuer feed-linked annual filing, two annual principal/carrying/noncurrent bridges, six fiscal maturity buckets, original 2025 aggregate issue reconciliation
  Phần còn thiếu tại checkpoint: Per-series outstanding, actual payments, effective legal calendar and full debt-service qualification; app integration pending
  Tài liệu: [P3_MATURITY_SOURCE_AUDIT_VI.md](P3_MATURITY_SOURCE_AUDIT_VI.md).
- Evidence: apple-annual-debt-bridge-app-20261015. Private exact-filing annual debt bridge API/UI/export; two actual annual basis reconciliations, six maturity bucket parity, no cross-scope fallback, source hash fail-closed, 67 tests, actual browser/mobile/outage/boundary and frozen-ledger guards
  Phần còn thiếu tại checkpoint: Per-series outstanding and actual principal/interest payments/calendar/full debt-service still unavailable
  Tài liệu: [P3_MATURITY_SOURCE_AUDIT_VI.md](P3_MATURITY_SOURCE_AUDIT_VI.md).
- Evidence: apple-annual-xbrl-debt-dimensions-20261015. Issuer feed-linked raw XBRL package and rendered report; broad155facts150numeric DOM parity/5nonnumeric retained;two annual HTML issuance-group checks;principal-versus-carrying basis caveat
  Phần còn thiếu tại checkpoint: Per-series outstanding, actual coupon/principal events, amendment/payment calendar; source profile not yet added to app
  Tài liệu: [APPLE_XBRL_DEBT_DIMENSIONS_VI.md](APPLE_XBRL_DEBT_DIMENSIONS_VI.md).
- Evidence: checkpoint. 10disclosed facility versions; minimum/definition clause evidence; not full debt-service/headroom
- Evidence: checkpoint. 34facilities+events tests
- Evidence: checkpoint. 5browser/source/export/mobile/outage groupsPASS
- Evidence: checkpoint. Four acquired note series; original-full-issue/no-redemption nominal schedule; not actual/current outstanding or full issuer debt service
- Evidence: checkpoint. 36note+facility testsPASS
- Evidence: checkpoint. 6groupsPASS: independent PDF table/coupon reconciliation, source-cutoff/issuer boundaries, series/export/reload/mobile/outage/frozen ledger
- Evidence: checkpoint. Acquired base clauses, issuer-feed/PDF linkage; no qualified actual calendar
- Evidence: checkpoint. 34rules+note testsPASS
- Evidence: checkpoint. 6groupsPASS source/cutoff/app/export/reload/mobile/outage/frozen ledger
- Evidence: 2026-10-11. Six saved workbook native baselines and18representative memory-input cases; SEC blank-to-zero fixed; not full capability qualification

#### P3.09 — Sector & concentration

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** SBA NAICS/geography/program/status aggregate marts và denominators.

**Đầu ra đích của plan:** Sector/geography cohort tables và scoped exports.

**Điều kiện nghiệm thu:** Booked SBA program không đại diện toàn bộ SME economy; approval amount không tự là EAD.

**Bước tiếp theo ghi trong sổ:** Thêm comparable time snapshots và concentration uncertainty/support.

- Nghiệm thu: p3-sba-descriptive-full-current-requirements. Current June six-source dictionary/quality/status/FY/sector/geography descriptive workflow;whole raw-to-canonical and all1197marts cells parity;81fields162dictionarycells,12scope downloads and1197share denominators;not unique borrowers,EAD,fixed-horizon PD or whole SME market
  Báo cáo: [P3_SBA_DESCRIPTIVE_ACCEPTANCE_VI.md](P3_SBA_DESCRIPTIVE_ACCEPTANCE_VI.md).
- Evidence: sba-march-historical-archive-20261014. Six separately acquired March CSVs,885226430bytes,2174502source records;whole-file independent CSV/Decimal audit;hash-verified aggregate-only program/status/exact-amount report;no frozen-case change
  Phần còn thiếu tại checkpoint: Archive API/UI/export parity,current June requirement-level audit;historical schema/subprogram semantics,identity,transitions,publication timing and fixed-horizon PD remain unqualified
  Tài liệu: [SBA_HISTORICAL_ARCHIVE_VI.md](SBA_HISTORICAL_ARCHIVE_VI.md).
- Evidence: sba-march-historical-archive-api-ui-20261014. Six March CSVs,2174502source records;independent CSV/Decimal audit;hash-verified API/UI/program-status/exact-amount report/export;21backend/HTTP tests and5actual-browser groups PASS;reload/mobile/outage-retry;frozen June case unchanged
  Phần còn thiếu tại checkpoint: Current June requirement-level source/numerical/browser/export audit;historical schema/subprogram semantics,identity,transitions,publication timing and fixed-horizon PD remain unqualified
  Tài liệu: [SBA_HISTORICAL_ARCHIVE_VI.md](SBA_HISTORICAL_ARCHIVE_VI.md).

#### P3.10 — Business review/export

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Selected SEC filing/cutoff hoặc SBA program/dimension/bucket, source quality.

**Đầu ra đích của plan:** Private SEC/SBA reports, issuer financial memo store/history, private JSON và filter-scoped SEC Excel Analysis/Facts.

**Điều kiện nghiệm thu:** Không fuzzy-match SBA name với SEC để tạo labels; không trộn reporting grains; owner chưa authenticated.

**Bước tiếp theo ghi trong sổ:** Thêm reviewer workflow/issuer events và scoped business handoff khi có inputs.

- Nghiệm thu: p3-business-review-export-full-current-requirement. 67 full private SEC projections and all378 SBA report scopes with quality/grain separation; current UI/private downloads and36 Excel scopes;73656cells14040formulas identical to native-verified baseline; accepted financial memo/history. No fuzzy issuer join, authenticated reviewer, currentEAD, fixed-horizon PD or actual debt/covenant qualification.
  Báo cáo: [P3_BUSINESS_REVIEW_EXPORT_ACCEPTANCE_VI.md](P3_BUSINESS_REVIEW_EXPORT_ACCEPTANCE_VI.md).
- Evidence: 2026-10-11. Six saved workbook native baselines and18representative memory-input cases; SEC blank-to-zero fixed; not full capability qualification


### P4 — Portfolio & observatory

#### P4.01 — Typed exposure & Excel intake

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** InputPositions/InputControl XLSX; position/pool/representation/as-of/currency/amount và optional risk contract.

**Đầu ra đích của plan:** Verified import, input quality và private inventory.

**Điều kiện nghiệm thu:** File≤20MB/50000positions; formula inputs/unsafe numeric precision bị reject; missing risk không thành zero.

**Bước tiếp theo ghi trong sổ:** Thêm column mapping theo source/facility và domain-specific Excel templates.

- Nghiệm thu: p4-typed-intake-concentration-full-current-requirements. Current typed XLSX bounds/formula/precision/identity/risk contract, actual9698 source observations and3EXAMPLE positions,47tests,66source math checks,20scopes664inventory checks,78native template cells,12UI scopes plus zero-share meter fix. No institution ownership, obligor concentration, FX totals, EAD inference, calibrated PD/ECL or authenticated governance claim.
  Báo cáo: [P4_INTAKE_CONCENTRATION_ACCEPTANCE_VI.md](P4_INTAKE_CONCENTRATION_ACCEPTANCE_VI.md).
- Evidence: 2026-10-11. P4 acceptance checkpoint 11/10/2026: fixed exact XLSX significant-digit validation and allowlisted Excel POST error messages. Backend62PASS; independent import66checks/bridge500checksPASS; browser5groupsPASS including source/bucket→draft, exports, invalid numeric rejection, valid EXAMPLE intake/mobile. Full scope/ownership/native Excel/governance qualification remains open. See P4_ACCEPTANCE_AUDIT_VI.md.
- Evidence: 2026-10-11. Six saved workbook native baselines and18representative memory-input cases; SEC blank-to-zero fixed; not full capability qualification

#### P4.02 — Reconcile & concentration

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Verified imported amounts, region/segment/source_state/representation.

**Đầu ra đích của plan:** Overview KPIs, concentration rows/meters, bucket detail→review draft.

**Điều kiện nghiệm thu:** Không cộng cross-currency; source observations không tự là borrower concentration; reported amount khác EAD.

**Bước tiếp theo ghi trong sổ:** Thêm obligor/group identity và explicit FX policy nếu cần global totals.

- Nghiệm thu: p4-typed-intake-concentration-full-current-requirements. Current typed XLSX bounds/formula/precision/identity/risk contract, actual9698 source observations and3EXAMPLE positions,47tests,66source math checks,20scopes664inventory checks,78native template cells,12UI scopes plus zero-share meter fix. No institution ownership, obligor concentration, FX totals, EAD inference, calibrated PD/ECL or authenticated governance claim.
  Báo cáo: [P4_INTAKE_CONCENTRATION_ACCEPTANCE_VI.md](P4_INTAKE_CONCENTRATION_ACCEPTANCE_VI.md).
- Evidence: 2026-10-11. P4 acceptance checkpoint 11/10/2026: fixed exact XLSX significant-digit validation and allowlisted Excel POST error messages. Backend62PASS; independent import66checks/bridge500checksPASS; browser5groupsPASS including source/bucket→draft, exports, invalid numeric rejection, valid EXAMPLE intake/mobile. Full scope/ownership/native Excel/governance qualification remains open. See P4_ACCEPTANCE_AUDIT_VI.md.

#### P4.03 — Research expected loss

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** PD horizon/target/measure, LGD, EAD và scenario eligibility.

**Đầu ra đích của plan:** Scenario EL/attribution và exact result exports.

**Điều kiện nghiệm thu:** Không mượn PD khác target; actual source import vẫn EL unavailable nếu không có risk inputs.

**Bước tiếp theo ghi trong sổ:** Thêm calibrated probability/recovery evidence và documented economic exposure.


#### P4.04 — ECL & staging

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Hazard/default curves, schedules/EIR assumptions, SICR/default policy, recoveries/cost/lag/scenario weights.

**Đầu ra đích của plan:** 36-month event curves, stage/scenario comparisons, weighted research ECL và export.

**Điều kiện nghiệm thu:** Bullet/EIR/recovery terms hiện minh họa; stage3/POCI/revolving policies không mặc định supported; chưa accounting compliance.

**Bước tiếp theo ghi trong sổ:** Thu thập actual contract/EIR/risk evidence; review staging và recovery policy.


#### P4.05 — Scenario & stress

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Versioned odds/LGD addition/EAD factor assumptions và selected eligible segment.

**Đầu ra đích của plan:** Scenario comparisons, clipping counts, exact ordered EL attribution.

**Điều kiện nghiệm thu:** Không gọi macro-calibrated stress khi chỉ có assumptions; excluded positions không bị gán zero loss.

**Bước tiếp theo ghi trong sổ:** Estimate response functions từ suitable time data và validation protocol.


#### P4.06 — Movement bridge

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Có.

**Đầu vào yêu cầu:** Same-source namespace position keys, currency, opening/closing amount và buckets.

**Đầu ra đích của plan:** Native-currency/bucket bridge, transitions và private exact export.

**Điều kiện nghiệm thu:** Missing record không là default/payoff; currency migration không là FX P&L; residual phải giữ rõ.

**Bước tiếp theo ghi trong sổ:** Thêm disposition reasons và better source linkage khi có evidence.

- Nghiệm thu: p4-observation-movement-bridge-full-current-requirement. Actual same-source February/March bridge,500independent checks;100synthetic boundary pairs26668rational checks;15tests;all8current API/UI/private export scopes,source guards/outage/recovery and immutable ledgers. No actual payoff/default/cashflow attribution, borrower linkage, FX P&L or EL movement inference.
  Báo cáo: [P4_MOVEMENT_BRIDGE_ACCEPTANCE_VI.md](P4_MOVEMENT_BRIDGE_ACCEPTANCE_VI.md).
- Evidence: 2026-10-11. P4 acceptance checkpoint 11/10/2026: fixed exact XLSX significant-digit validation and allowlisted Excel POST error messages. Backend62PASS; independent import66checks/bridge500checksPASS; browser5groupsPASS including source/bucket→draft, exports, invalid numeric rejection, valid EXAMPLE intake/mobile. Full scope/ownership/native Excel/governance qualification remains open. See P4_ACCEPTANCE_AUDIT_VI.md.

#### P4.07 — Tail risk & concentration

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Eligible position EAD, declared PD/LGD, latent-factor rho, systemic LGD spread, seed/draws.

**Đầu ra đích của plan:** VaR/ES, Monte Carlo uncertainty, concentration và convergence reports.

**Điều kiện nghiệm thu:** Correlation/recovery chưa calibrated; thiếu obligor linkage; finite tails/CI unavailable giữ đúng; chưa capital approval.

**Bước tiếp theo ghi trong sổ:** Thêm calibrated dependence, group linkage và production convergence thresholds.


#### P4.08 — Bank observatory

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** FDIC CERT×REPDTE financials, failures, metric definitions và reporting units.

**Đầu ra đích của plan:** Bank metrics, peer/history charts, missingness và selected report export.

**Điều kiện nghiệm thu:** USD thousand giữ đúng; institution event không là borrower default; reporting date không tự là availability date.

**Bước tiếp theo ghi trong sổ:** Thêm publication lags và stress linkage theo bank contracts.


#### P4.09 — Country observatory

**Checkpoint:** Đã có. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** World Bank country/year series, units, regional/aggregate definitions và current classifications.

**Đầu ra đích của plan:** Annual trend, same-year peers và source-qualified export.

**Điều kiện nghiệm thu:** Không thay missing bằng latest; ratio không cộng thành tổng; current region/income labels không historical classification.

**Bước tiếp theo ghi trong sổ:** Thêm debt/default/availability sources và documented macro stress linkage.

- Evidence: sovereign-source-api-20261011. Two official editions, 21877 entity-year rows, 16 selected metrics, independent full value/source audit and bounded private API
  Phần còn thiếu tại checkpoint: Country UI/browser/review integration, source conflicts, historical availability and qualified macro stress linkage
  Tài liệu: [SOVEREIGN_DEFAULT_DATA_VI.md](SOVEREIGN_DEFAULT_DATA_VI.md).
- Evidence: sovereign-ui-20261011. Country tabs, six filters/URL, source conflicts/provisional values, distinct yearly/revision deltas, timeline/components/search/paging, scoped export, mobile and outage/late response guards
  Phần còn thiếu tại checkpoint: Sovereign review capture, source conflicts, historical availability and qualified macro stress linkage
  Tài liệu: [SOVEREIGN_DEFAULT_DATA_VI.md](SOVEREIGN_DEFAULT_DATA_VI.md).
- Evidence: sovereign-archive-20261011. Four official editions,42519rows,680304positions,explicit2024TOTAL alias,2023IADB schema absence,raw source markers,68retained count conflicts and edition-specific UI/export
  Phần còn thiếu tại checkpoint: Original publication-byte availability, source conflicts, macro stress linkage, PD/LGD qualification and sovereign review capture
  Tài liệu: [SOVEREIGN_ARCHIVE_EDITIONS_VI.md](SOVEREIGN_ARCHIVE_EDITIONS_VI.md).

#### P4.10 — Finance review package

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Source import/currency, scenario/ECL/tail evidence, owner/expiry/status/acknowledgment.

**Đầu ra đích của plan:** Review revisions, evidence freshness/expiry và finance workbook.

**Điều kiện nghiệm thu:** Reviewed không là human-authenticated sign-off; Excel notes không ghi ngược app; source values không bị sửa bởi memo.

**Bước tiếp theo ghi trong sổ:** Thêm authenticated reviewer roles và formal review policy.

- Evidence: 2026-10-11. Six saved workbook native baselines and18representative memory-input cases; SEC blank-to-zero fixed; not full capability qualification


### P5 — Structured & market

#### P5.01 — Deal & terms catalog

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** World Omni2025-A prospectus, servicing certificates và selected prospectus terms.

**Đầu ra đích của plan:** Deal source context, tranche terms và unsupported legal scope.

**Điều kiện nghiệm thu:** Chưa xác minh đầy đủ agreements/amendments/legal state; terms không mặc định full contractual waterfall.

**Bước tiếp theo ghi trong sổ:** Thu thập complete agreements, amendments và term extraction review.


#### P5.02 — Collateral pool

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** 20 monthly certificates; reported pool/note/distribution/reserve metrics.

**Đầu ra đích của plan:** Pool/note trends, period metrics và source comparisons.

**Điều kiện nghiệm thu:** Aggregate pool reports không là asset-level persistent panel; Ginnie/ABS-EE loan-level tracks còn thiếu.

**Bước tiếp theo ghi trong sổ:** Thêm deal-specific asset IDs/schema và collateral-history adapter.

- Evidence: 2026-10-11. Source-native21cohort static-pool curves; raw age/metric support, no asset-level/forecast/LGD qualification
- Evidence: 2026-10-11. Managed aggregate stock/flow adapter: 7 periods, 210 source values, 105 checks, 14 raw ratios; not collateral-level/forecast/LGD qualification
- Evidence: 2026-10-11. ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. See ABS_EE_MIRROR_COVERAGE_VI.md.
- Evidence: 2026-10-11. Official2025CFR definitions,62proposed mirror-field correspondences,source coverage and app/export; no XSD/XML-fidelity/model qualification

#### P5.03 — Cash-flow projection

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Asset schedules, rates/reset terms, default/prepay/recovery timing và servicing fees.

**Đầu ra đích của plan:** Forward pool cashflows và scenario assumptions.

**Điều kiện nghiệm thu:** Reported history không được gọi là projection; chưa có complete collateral contracts.

**Bước tiếp theo ghi trong sổ:** Thiết kế collateral schedule intake và calibrate suitable behavior models.

- Evidence: 2026-10-11. ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. See ABS_EE_MIRROR_COVERAGE_VI.md.
- Evidence: 2026-10-11. Official2025CFR definitions,62proposed mirror-field correspondences,source coverage and app/export; no XSD/XML-fidelity/model qualification

#### P5.04 — Sequential waterfall

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Reported inputs và selected pre-acceleration terms; cash/reserve beginning states.

**Đầu ra đích của plan:** Priority explorer, stage allocations, full ledger và period export.

**Điều kiện nghiệm thu:** Cash/balance conservation; reviewer prior obligations có giả định; không gọi unconditional legal compliance.

**Bước tiếp theo ghi trong sổ:** Verify full legal regimes, prior obligations và amendments trước full contractual engine.


#### P5.05 — Tranche & triggers

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Seven issued tranches, coupons/day counts, funded principal, OC/reserve và selected review trigger.

**Đầu ra đích của plan:** Tranche balances/payment detail và source checks.

**Điều kiện nghiệm thu:** Stage shortfalls không cộng thành credit loss; không prorate pool loss thành tranche loss; unsupported triggers giữ gap.

**Bước tiếp theo ghi trong sổ:** Bổ sung verified trigger state/history và loss-allocation/legal regimes.

- Evidence: 2026-10-11. Current administrator SOFR/SIFMA date/rate/coupon/base-interest comparison; historical publication and full legal qualification not established

#### P5.06 — Scenario valuation

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Fixed-coupon face/coupon/yield/years/frequency; actual instrument quotes chưa có.

**Đầu ra đích của plan:** Assumed bond price/schedule/export; actual ABS valuation chưa hỗ trợ.

**Điều kiện nghiệm thu:** Treasury/index OAS không là deal quote; không gọi market-calibrated ABS price.

**Bước tiếp theo ghi trong sổ:** Thu thập instrument quotes và supported projected cashflows trước calibrated valuation.


#### P5.07 — Bond sensitivity

**Checkpoint:** Có điều kiện. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Declared fixed-coupon terms và discount yield/conventions.

**Đầu ra đích của plan:** Duration, convexity, bump residuals và bond scenario export.

**Điều kiện nghiệm thu:** Scope coupon-date benchmark; chưa dirty/clean/accrued/spread curve của mọi actual security.

**Bước tiếp theo ghi trong sổ:** Thêm trade/settlement dates, day-count/accrual và curve benchmark pricers.


#### P5.08 — CDS credit curve

**Checkpoint:** Cần dữ liệu. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Reference entity quotes/tenors, recovery, discount curve và CDS conventions.

**Đầu ra đích của plan:** Credit curve, implied spreads và pricing residuals.

**Điều kiện nghiệm thu:** Index OAS không thay CDS quotes; risk-neutral probability không thay borrower real-world PD.

**Bước tiếp theo ghi trong sổ:** Lấy licensed term quotes và freeze pricing conventions/benchmark.


#### P5.09 — Position & scenario comparison

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Native Treasury/OAS series, declared bond scenarios và currency/date conventions.

**Đầu ra đích của plan:** Market context, scenario outputs và independent scoped exports; chưa combined security-position book.

**Điều kiện nghiệm thu:** Index không là executable price; actual exposure representations không double-count cùng underlying risk.

**Bước tiếp theo ghi trong sổ:** Thêm typed security-position mapping và supported instrument cashflow engines.


#### P5.10 — Surveillance & numerical evidence

**Checkpoint:** Một phần. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** Chưa chứng minh.

**Đầu vào yêu cầu:** Reported source metrics, canonical mappings, conservation checks và period history.

**Đầu ra đích của plan:** Period check report, discrepancy support và conditional qualification.

**Điều kiện nghiệm thu:** Không bỏ dropped amendments/unsupported triggers; chưa live surveillance event feed.

**Bước tiếp theo ghi trong sổ:** Thêm fresh servicing periods, legal change detection và review ownership.

- Evidence: 2026-10-11. Current administrator SOFR/SIFMA date/rate/coupon/base-interest comparison; historical publication and full legal qualification not established
- Evidence: 2026-10-11. Source-native21cohort static-pool curves; raw age/metric support, no asset-level/forecast/LGD qualification
- Evidence: 2026-10-11. Managed aggregate stock/flow adapter: 7 periods, 210 source values, 105 checks, 14 raw ratios; not collateral-level/forecast/LGD qualification
- Evidence: 2026-10-11. ABS-EE mirror checkpoint 11/10/2026: SEC metadata 22 filings, 11 monthly mirror Parquet files pinned at commit 071b897ec737ae05bd5e17be707f46e3d68b6a7c; 14 source files/28542411 bytes. Profile 488219 asset-period rows, 57–62 columns, 7 adjacent links and 3 gaps. Independent 651 missingness/99 money sums PASS, 5 tests PASS, browser 4 groups PASS. Original XML/source fidelity/units/labels/model readiness unqualified; statuses unchanged. See ABS_EE_MIRROR_COVERAGE_VI.md.
- Evidence: 2026-10-11. Official2025CFR definitions,62proposed mirror-field correspondences,source coverage and app/export; no XSD/XML-fidelity/model qualification

## 5. Plan KPI/phân tích riêng

11/17 = 64,7% về delivery coverage: A1–A5 và B1–B6 đã triển khai trong scope hiện có. Không cộng 17 mục này vào 50 vì có overlap.

| Nhóm | Nội dung | Tình trạng |
|---|---|---|
|A1–A5|Regional movement; mortgage migration/cure; policy economics; issuer ratios; structured cash bridge|Đã triển khai trong scope dữ liệu/assumptions|
|B1–B6|Quality controls; comparable baseline; analyst review; KPI Excel; corporate Excel; maturity Excel|Đã triển khai; qualification mở rộng còn thiếu|
|C1|Retail temporal/OOT validation|Có dữ liệu mới và temporal profile; chưa có study OOT đủ điều kiện|
|C2|Mortgage horizon PD12|Thiếu authorized multi-vintage data và model/calibration/OOT|
|C3|Qualified LGD|Thiếu recovery timing, cost/discount conventions và mature support|
|C4|Full DSCR/covenants|Actual DSCR/clause evidence đã bổ sung; chưa đóng full debt-service/legal scope|
|C5|Decision-grade EL/ECL|Engines conditional; thiếu qualified parameters, contracts/EIR/staging và governance|
|C6|Forward structured valuation|Replay/assumption studies; thiếu forecast/full waterfall/curves/benchmark|

## 6. Thứ tự để tiến tới hoàn thành

1. Nghiệm thu lại từng capability theo source, phép tính độc lập, runtime, browser, export và intended-use; ghi completion evidence trước khi nâng trạng thái.
2. Retail: qualify temporal/application sources, xác minh income/obligations và mở rộng Affordability intake; sau đó OOT, limit/pricing, collections.
3. Mortgage: lấy annual vintages hợp lệ, chốt temporal/entity-safe splits, PD12/calibration và recovery/LGD conventions.
4. Business: actual debt-service inputs, effective legal terms, adjustment ledger, headroom và complete memo/review.
5. Portfolio: qualified PD/LGD/EAD, actual positions/EIR/staging, validated stress/dependence và authenticated review.
6. Structured: original collateral provenance, complete contractual regimes, cashflow forecasts, security curves và independent pricing benchmark.

## 7. Nguồn đối chiếu

- [Sổ 50 yêu cầu](COMPLETION_REQUIREMENTS_50.json)
- [Plan workbench](PLAN_WORKBENCH_DETAIL.md)
- [Plan KPI](PLAN_KPI_ANALYTICS_NEXT_VI.md)
- [Kiểm kê trước ngày 11/10](PROGRESS_VS_PLAN_2026-10-11_VI.md)
- [Affordability contract](AFFORDABILITY_INTAKE_VI.md) — phần UI còn ghi cần làm trong tài liệu này đã được bổ sung; receipt UI nêu ở mục 3 là cập nhật mới hơn.
