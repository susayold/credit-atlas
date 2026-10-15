# P2.07 — nghiệm thu Competing Outcomes

Ngày12/10/2026. Đối chiếu yêu cầu hiện tại P2.07, case `d01-a24484b21a21`, official annual sample2012. Đích là cohort support, descriptive competing incidence/exits và target exclusions. Không là model PD12/OOT hoặc regulatory default probability.

## Yêu cầu và evidence

| Yêu cầu gốc | Kiểm chứng độc lập | Kết quả |
|---|---|---|
|Early-entry eligible loans|Đọc first observed month/source age/contractual age/state/modification/terminal từ full canonical; không dùng engine label SQL để phân loại eligibility|50.000source loans,48.066eligible,1.934excluded khớp|
|Endpoint observations và censoring|Python chronological walk từng loan cho24months, dừng gap/unknown trước event; D3 ưu tiên cùng tháng,other exit/prepayment tách riêng|48.066saved ledger rows khớp stop/cause/censor/calendar age|
|Horizon6/12/24|Recompute risk sets/cumulative event counts và incidence bằng Fraction, không dùng engine curve()|72curve rows,216incidence values khớp tolerance1e−12|
|Cohort support|Source/eligible/excluded/at-risk/calendar-mature và year/segment denominator kiểm tra trực tiếp|PASS|
|Incidence/exits charts|Browser so headlines/ledger/selected horizon với verified source; chart label ghi6/12/24|12segment×horizon scopes PASS|
|Target exclusions|Binary12m labels được reconstruct riêng; ineligible/other exit/censor/unknown không thành negative|Full label outcome/target counts khớp|
|Không gọi horizon connector là monthly prediction|Chart subtitle và note được kiểm tra; không có chart cho cohort unavailable|PASS|
|Censored/unknown không thành negative|Synthetic gap/unknown/immaturity/tie cases và label invariant tests; source chronological classifier|PASS|

## Kết quả snapshot và cách đọc

Trong50.000loans,1.919not-early-entry và15terminal-at-entry bị loại khỏi eligible cohort. Binary12m labels gồm45.241complete_no_event,2.641prepayment,102D3 events,82other exits và1.934ineligible. Other exits/ineligible giữ target null; prepayment là negative theo **event-before-prepayment estimand** đã định nghĩa, không phải xác nhận sẽ không default nếu khoản vay tiếp tục tồn tại.

Đối với nguồn thực này, không có censored/unknown label rows ở12m; absence không thay boundary tests. Các test có gap,unknown,short follow-up và calendar-immature cohorts để kiểm tra unavailable semantics.

Incidence dùng ba competing causes, có risk-set denominator và survival/cumulative-incidence identity. Không coi prepayment là censor như một-minus-KM thông thường. Event-free và incidence được tính từ observed first-event ledger, không từ independent classifiers.

Bootstrap đã tái tạo theo seed17/resamples500, dùng independently evaluated rational incidence, kiểm tra18CI bounds ở3cohorts×3horizons. Xác nhận reproducibility/công thức quantile, **không chứng minh nominal95% coverage ngoài sample**, borrower independence hoặc khả năng tổng quát hóa qua vintages.

## Receipts

- Independent audit `private evidence omitted from public release`: source hashes,case receipt,48.066ledger rows,72curve rows,216probability checks,18bootstrap bounds và12export scopes PASS; retail holdout ledger unchanged.
- Tests `private evidence omitted from public release`: **49 PASS**, gồm competing-event math/ties/unknown/gap/maturity/uncertainty,labels và frozen-serving filters/integrity.
- Browser `private evidence omitted from public release`: **12scopes PASS** (4segments×6/12/24), selected headlines/ledger/source/export parity, chart-not-monthly disclosure, unknown segment unavailable,mobile,reload. Không page errors,ledger unchanged. Desktop và unavailable mobile đã visual-review.

Report horizon filter chỉ lọc vintage_competing_risk table theo horizon. Binary target metadata vẫn12months và `censored_means=unavailable_not_negative`; không đổi nhãn12m sang24m vì người xem chọn chart24m. Export giữ scope này và source lineage.

## Kết luận

Đủ evidence cho **toàn bộ yêu cầu hiện tại P2.07**. Bước tiếp theo—survival/competing-risk model khi temporal cohorts đạt gate—vẫn mở. Không bổ sung vintage mới,không fit/refit model hoặc truy cập retail final predictors. P2.08/R2/R3 và goal100% chưa hoàn thành.
