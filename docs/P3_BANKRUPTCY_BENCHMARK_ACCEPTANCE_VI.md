# P3.04 — nghiệm thu bankruptcy benchmark hiện tại

Ngày 15/10/2026. Đối chiếu đúng yêu cầu P3.04 trong sổ 50 capability và `PLAN_WORKBENCH_DETAIL.md`: UCI365 original ARFF, subset5/horizon một năm, frozen splits/model/calibration, saved validation/final metrics, uncertainty và model card. Không mở rộng kết luận thành loan-default PD hoặc production corporate model.

## Source, split và model freeze

Audit `bankruptcy-frozen-lineage-audit-907872a3548a/receipt.json` PASS source/reference identity và hash graph của case → study → features → assessment → comparison → freeze → final evaluation. Original ARFF ZIP, CSV mirror/metadata, các receipts, methods và saved outputs giữ hash đã ghi. Không parse lại final financial predictors; original preparation evidence được xác minh bằng hash.

Horizon mapping giữ subset1→5 năm, subset2→4, subset3→3, subset4→2, subset5→1. Chỉ study một năm được dùng, không pool năm horizon. Có 5.910 source statements và 5.850 exact feature groups. Metadata có unique source ordinals; mỗi group chỉ thuộc một partition:

| Partition | Statements | Events | Exact groups |
|---|---:|---:|---:|
| Train | 3.546 | 246 | 3.516 |
| Calibration | 886 | 61 | 870 |
| Validation | 887 | 62 | 879 |
| Final | 591 | 41 | 585 |

Protocol/saved encoder/features/model/calibration giữ nguyên. Development coverage 5.319 rows, 128 dimensions từ 64 ratios và 64 missing indicators. Candidate selection được tính lại từ saved validation: Brier thấp nhất, log loss trong tie tolerance, rồi fixed preference. Kết quả `boosting_platt` khớp freeze và final receipt; final không tham gia selection. Study/features/assessment/comparison/freeze đều hoàn tất trước final evaluation. Read-only ledger có đúng một completed record cho original-source/horizon lineage.

## Numerical audit độc lập

`bankruptcy-saved-metrics-audit-0c01be07f13b/receipt.json` PASS:

- 4.435 saved validation score rows của năm candidates; 887 statements chung, target/group/order đồng nhất.
- 591 saved final scores của duy nhất chosen candidate; không tạo thêm final predictions.
- AUC được tính từ rank/ties; AP theo precision tại từng score threshold; Brier và log loss bằng công thức độc lập. Không gọi production metric helper hoặc sklearn metrics.
- 60 reliability bins của năm validation candidates và final: counts/events, mean probability, observed rate và empty-bin NULL.
- 1.000 final group-bootstrap draws và 5.000 paired validation candidate draws được dựng lại từ saved scores, đúng seeds và group/source-record weights. Tổng 24.000 metric cells khớp trong tolerance 2e−12.
- 180 validation point/percentile/delta cells của năm candidates và mười paired comparisons; final point/95% percentile intervals cũng khớp. Quantile interpolation được tính độc lập.
- Bankruptcy và Retail holdout ledgers giữ nguyên hash; không đọc final predictors, không model inference, không training.

| Final metric | Point |
|---|---:|
| ROC AUC | 0,962793792 |
| Average precision | 0,863689087 |
| Brier | 0,021610995 |
| Log loss | 0,087159890 |

Đây là kết quả trên source statements của historical random-group benchmark. Bootstrap conditional trên model đã cố định và exact groups; không phải retraining uncertainty hay independent-firm inference.

## App, export và model card

`bankruptcy-model-browser-qa-390102285f73/receipt.json` PASS tám nhóm actual browser checks: saved final/validation/support/badges, private aggregate export, URL reload, mobile, navigation và availability khi mortgage runs rỗng. Final transform/prediction functions bị vô hiệu hóa trong toàn bộ catalog/UI/export verification. Không browser/console errors; không thay đổi holdout ledger.

Đã xem trực tiếp desktop/mobile screenshots. Bảng validation, final point/intervals, reliability support và giới hạn source hiện rõ; mobile tables nằm trong phạm vi cuộn của panel. `bankruptcy-model-acceptance-tests.xml`: 36 tests PASS cho assessment/comparison/freeze/holdout/model-view boundaries.

Model card hiện hành: `docs/BANKRUPTCY_FINAL_MODEL_CARD.md`, giữ intended use, nguồn/horizon, cohorts, preprocessing/model settings, selection, final metrics/uncertainty và ledger restrictions. App/export luôn giữ production qualification false.

## Giới hạn vẫn giữ

Exact groups không phải firm IDs. Nguồn thiếu firm identity và publication dates, nên chưa chứng minh entity-disjoint/OOT hoặc application-time availability. Bankruptcy label không tự trở thành loan default. Không qualification cho Vietnam SME PD, approvals, limits, pricing, IFRS9 ECL hoặc deployment trên hồ sơ mới.

Nghiệm thu này đóng P3.04 theo **benchmark hiện tại**; bước thu thập identified dated statements cho deployed corporate-risk study vẫn giữ nguyên trong plan. Không sửa required inputs/outputs/acceptance/next để phù hợp với phần đã có.
