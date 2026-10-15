# CreditAtlas — dữ liệu, phân tích và 88 KPI theo năm domain

Checkpoint KPI data inspector 10/10/2026: catalogue tìm kiếm/lọc actual,
missing và comparable-baseline; bấm KPI mở hồ sơ; bảng hỗ trợ tìm mọi cột,
25-row paging và CSV toàn bộ filtered rows. 16 SEC ratio input traces và
3 mortgage ratio traces có actual numerator/denominator; metric schema cho
reviews/Excel giữ nguyên. QA `kpi-inspector-qa-f43c77e05a6b`: 10 nhóm PASS,
5 domain/source-table CSV parity, issuer/mortgage input parity, mobile và
frozen ledger unchanged. Excel regression đối chiếu110 KPI/control rows PASS;
13 supported SEC ratios reconcile Decimal60. [Cách sử dụng](KPI_DATA_INSPECTOR_VI.md).
88 KPI /22 controls giữ counts hiện có; chưa phải full record-level input
trace cho mọi KPI hoặc hoàn tất C1–C6 qualification gates.


Bản kiểm tra ngày 10/10/2026. Đây là bản chụp từ các nguồn đã lưu, không phải feed thời gian thực. Trong app: **Risk monitor → Phân tích KPI chi tiết → P1–P5**. Có thể đổi domain, cửa sổ lịch sử và count/UPB; xuất JSON riêng tư lưu cả kết quả, filters và provenance.

## 1. Cách đọc và phạm vi

Mỗi KPI gồm actual, công thức/mẫu số, so sánh khi có kỳ tương thích và cách diễn giải. Chưa có target, risk appetite hoặc giới hạn được phê duyệt của một tổ chức cụ thể; app không tự gán mức tốt/xấu. Null giữ là Unavailable; zero chỉ được dùng khi nguồn thực sự ghi zero.

Các nguồn khác nhau về thời gian, population và grain. Retail là Taiwan 2005; Mortgage là annual sample Freddie vintage 2012 theo dõi đến tháng 3/2026; SBA là source-record stock; Portfolio dùng chính snapshot Freddie đó; ABS là reported periods của World Omni 2025-A. Không cộng dữ liệu các domain thành một danh mục ngân hàng, đặc biệt P2/P4 có source overlap.

Amount nguồn trong backend và các bảng exact được giữ theo Decimal/string. KPI mô tả trong trình duyệt dùng số floating point; số USD hiển thị trên monitor làm tròn whole dollars. Bảng dưới giữ hai chữ số thập phân của phép tính mô tả, không thay ledger kế toán. Không cộng các monthly stock để suy ra unique loans.

## 2. Nguồn và snapshot

| Domain | API đã đọc | Evidence ID | Phạm vi |
| --- | --- | --- | --- |
| P1 | /api/suite-view | suite-view-74e07524f6d0 | UCI350 · Taiwan 2005 · saved random holdout |
| P3 | /api/suite-view | suite-view-74e07524f6d0 | SBA source records; status stock, not fixed-horizon default rates |
| P2 | /api/snapshot + /api/monitoring + /api/period-transitions + /api/episode-followup | d01-a24484b21a21 | Whole frozen Freddie annual sample; count/UPB denominators separate |
| P5 | /api/abs-view + /api/abs-period | abs-view-1ea94d36115b | World Omni 2025-A · reported periods · conditional replay |
| P4 | /api/exposure-aggregates | exposure-import-57b88e00bedb | USD · region · source observation; not owned positions |

P4 so sánh import `exposure-import-57b88e00bedb` (2026-03) với `exposure-import-facfbef3f419` (2026-02), cùng USD/region. Thời điểm đọc export: 2026-10-10T10:53:45.048Z.

## 3. P1: Retail — model, calibration và population

UCI 350 · Taiwan 2005 · saved random final test; development comparisons dùng validation riêng

### Nhận xét từ dữ liệu

- Final test có 664 events / 3,001 clients (22.13%). AP cần được đọc cùng base rate này.
- Weighted bin gap = 1.3191%; xem support từng bin trước diễn giải. Không có holdout confidence interval hoặc temporal validation.
- AUC/Brier đẹp không đủ chọn approval cutoff. Policy costs/capacity và subgroup cần xem riêng; demographic exclusion không chứng minh fairness.
- Policy lower_thresholds trên 4,499 validation clients: review 2,277 / capacity 600, overflow 1,677. Case đầu trong plan, không chọn theo cost thấp nhất.
- Expected declared cost 4808.640601 declared_cost_units; retrospective proxy 4643.000000. Costs là giả định; không đo realized profit hoặc reviewer efficacy.

### Định nghĩa và actual của từng KPI

#### 1. Final-test clients

**Actual:** 3,001. **Công thức/support:** events + non-events.

**Diễn giải:** Client-disjoint; không là out-of-time test.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 2. Event prevalence

**Actual:** 22.1260%. **Công thức/support:** 664 / 3001.

**Diễn giải:** Base rate của test cohort; không phải PD toàn thị trường.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 3. ROC AUC

**Actual:** 0.777878. **Công thức/support:** Saved ranking metric.

**Diễn giải:** Đo ranking event vs non-event; không đo profit hay calibration.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 4. Average precision

**Actual:** 0.543521. **Công thức/support:** Saved precision–recall summary.

**Diễn giải:** Phụ thuộc prevalence; không so thẳng với cohort có base rate khác.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 5. Brier

**Actual:** 0.136377. **Công thức/support:** mean((p − y)²).

**Diễn giải:** Probability error; thấp hơn tốt hơn trong cùng cohort.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 6. Log loss

**Actual:** 0.432887. **Công thức/support:** −mean(y ln p + (1−y) ln(1−p)).

**Diễn giải:** Phạt dự báo tự tin nhưng sai; không phải loss dollars.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 7. Weighted absolute bin gap

**Actual:** 1.3191%. **Công thức/support:** Σ bin clients × |mean p − observed rate| / N.

**Diễn giải:** Descriptive calibration gap trên bins định trước; phụ thuộc cách chia bins.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 8. Validation Brier improvement

**Actual:** 0.039887. **Công thức/support:** constant Brier − selected model Brier trên cùng validation.

**Diễn giải:** Exploratory development comparison; không tune lại bằng test.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 9. Validation AP / base rate

**Actual:** 2.536612. **Công thức/support:** selected validation AP / validation prevalence.

**Diễn giải:** Tỷ số benchmark, không phải lift@k hoặc economic return.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 10. Policy validation clients

**Actual:** 4,499. **Công thức/support:** Saved development-validation cohort.

**Diễn giải:** Tách khỏi final-test metrics ở trên.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 11. Scenario accept share

**Actual:** 27.0282%. **Công thức/support:** Scenario action clients / validation clients.

**Diễn giải:** Simulated action trên booked cohort; không actual application decision rate.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 12. Scenario review share

**Actual:** 50.6112%. **Công thức/support:** Scenario action clients / validation clients.

**Diễn giải:** Simulated action trên booked cohort; không actual application decision rate.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 13. Scenario decline share

**Actual:** 22.3605%. **Công thức/support:** Scenario action clients / validation clients.

**Diễn giải:** Simulated action trên booked cohort; không actual application decision rate.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 14. Scenario review overflow

**Actual:** 1,677. **Công thức/support:** max(0, review records − declared capacity).

**Diễn giải:** Capacity là giả định trên cohort; không daily staffing productivity.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 15. Expected declared cost

**Actual:** 4808.640601 declared cost units. **Công thức/support:** Σ [(1−p)×c(action,0) + p×c(action,1)].

**Diễn giải:** Declared cost units; không USD/TWD realized loss.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 16. Retrospective cost proxy

**Actual:** 4643.000000 declared cost units. **Công thức/support:** Σ c(action, observed target).

**Diễn giải:** Observed labels không xác định counterfactual sau reject/review.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 17. Expected declared cost per client

**Actual:** 1.068824 declared cost units. **Công thức/support:** Expected declared cost / validation clients.

**Diễn giải:** Phụ thuộc cost matrix và model probabilities; chưa actual profit.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 18. Expected cost difference vs accept_all

**Actual:** -5295.640222 declared cost units. **Công thức/support:** Scenario expected cost − accept_all expected cost.

**Diễn giải:** Cùng cohort/cost matrix; delta không chứng minh lợi ích can thiệp.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

### Split support

| Partition | Clients | Events | Event rate |
| --- | --- | --- | --- |
| train | 17,999 | 3,981 | 22.12% |
| calibration | 4,501 | 996 | 22.13% |
| validation | 4,499 | 995 | 22.12% |
| final_test | 3,001 | 664 | 22.13% |

### Validation candidates — cùng cohort

| Model | Variant | AUC | AP | Brier | Log loss |
| --- | --- | --- | --- | --- | --- |
| constant | raw | 0.5000 | 0.2212 | 0.172248 | 0.528373 |
| constant | calibrated | 0.5000 | 0.2212 | 0.172248 | 0.528373 |
| logistic | raw | 0.7763 | 0.5480 | 0.134773 | 0.431000 |
| logistic | calibrated | 0.7763 | 0.5480 | 0.134855 | 0.431242 |
| boosting | raw | 0.7842 | 0.5610 | 0.132362 | 0.423153 |
| boosting | calibrated | 0.7842 | 0.5610 | 0.132331 | 0.423037 |

### Final-test reliability — không bỏ support

| Bin | Clients | Events | Mean p | Observed | Gap pp |
| --- | --- | --- | --- | --- | --- |
| 0.0–0.1 | 825 | 52 | 6.81% | 6.30% | 0.5056 |
| 0.1–0.2 | 1,105 | 159 | 14.21% | 14.39% | -0.1813 |
| 0.2–0.3 | 393 | 99 | 24.27% | 25.19% | -0.9238 |
| 0.3–0.4 | 210 | 77 | 34.24% | 36.67% | -2.4249 |
| 0.4–0.5 | 114 | 43 | 44.14% | 37.72% | 6.4187 |
| 0.5–0.6 | 62 | 34 | 54.37% | 54.84% | -0.4717 |
| 0.6–0.7 | 143 | 84 | 65.60% | 58.74% | 6.8598 |
| 0.7–0.8 | 135 | 106 | 74.29% | 78.52% | -4.2321 |
| 0.8–0.9 | 14 | 10 | 82.56% | 71.43% | 11.1266 |
| 0.9–1.0 | 0 | 0 | Unavailable | Unavailable | Unavailable |

### Policy assumptions — units và decision rules

| Field | Value |
| --- | --- |
| Policy | retail-policy-bd4b8623de28 |
| Case | lower_thresholds |
| Partition | validation |
| Units | declared_cost_units |
| Threshold rule | accept p < lower; review lower <= p < upper; decline p >= upper; ties remain together |
| Capacity rule | Flag excess review demand; no records dropped or silently reassigned |
| Review capacity | 600 |
| accept costs non_event / event | 0 / 10 |
| review costs non_event / event | 1 / 3 |
| decline costs non_event / event | 2 / 0 |

### Declared cases và constant-action benchmarks — cùng validation

| Case | Lower / upper | Accept | Review | Decline | Overflow | Expected exact cost units | Retrospective exact cost units |
| --- | --- | --- | --- | --- | --- | --- | --- |
| accept_all | accept | 4,499 | 0 | 0 | 0 | 10104.2808230118883825 | 9950 |
| review_all | review | 0 | 4,499 | 0 | 3,899 | 6519.8561646023776765 | 6489 |
| decline_all | decline | 0 | 0 | 4,499 | 0 | 6977.1438353976223235 | 7008 |
| lower_thresholds | 0.10 / 0.30 | 1,216 | 2,277 | 1,006 | 1,677 | 4808.64060113836443494 | 4643 |
| middle_thresholds | 0.20 / 0.50 | 2,904 | 1,053 | 542 | 453 | 5282.01829890020810362 | 5055 |
| higher_thresholds | 0.25 / 0.65 | 3,245 | 892 | 362 | 292 | 5790.67593881588885178 | 5554 |

### Action support — all scenarios

| Case | Action | Clients | Events | Event rate | Mean p | Expected exact cost units | Retrospective exact cost units |
| --- | --- | --- | --- | --- | --- | --- | --- |
| accept_all | accept | 4,499 | 995 | 22.1160% | 22.4589% | 10104.2808230118883825 | 9950 |
| accept_all | review | 0 | 0 | Unavailable | Unavailable | 0 | 0 |
| accept_all | decline | 0 | 0 | Unavailable | Unavailable | 0 | 0 |
| review_all | accept | 0 | 0 | Unavailable | Unavailable | 0 | 0 |
| review_all | review | 4,499 | 995 | 22.1160% | 22.4589% | 6519.8561646023776765 | 6489 |
| review_all | decline | 0 | 0 | Unavailable | Unavailable | 0 | 0 |
| decline_all | accept | 0 | 0 | Unavailable | Unavailable | 0 | 0 |
| decline_all | review | 0 | 0 | Unavailable | Unavailable | 0 | 0 |
| decline_all | decline | 4,499 | 995 | 22.1160% | 22.4589% | 6977.1438353976223235 | 7008 |
| lower_thresholds | accept | 1,216 | 75 | 6.1678% | 6.8880% | 837.5762325740790458 | 750 |
| lower_thresholds | review | 2,277 | 361 | 15.8542% | 16.8578% | 3044.70264332592362824 | 2999 |
| lower_thresholds | decline | 1,006 | 559 | 55.5666% | 53.9582% | 926.3617252383617609 | 894 |
| middle_thresholds | accept | 2,904 | 302 | 10.3994% | 11.1512% | 3238.2943728718006009 | 3020 |
| middle_thresholds | review | 1,053 | 321 | 30.4843% | 30.3875% | 1692.96060802821252952 | 1695 |
| middle_thresholds | decline | 542 | 372 | 68.6347% | 67.6418% | 350.7633180001949732 | 340 |
| higher_thresholds | accept | 3,245 | 377 | 11.6179% | 12.3266% | 3999.9889834553206776 | 3770 |
| higher_thresholds | review | 892 | 351 | 39.3498% | 39.1128% | 1589.77266163594085758 | 1594 |
| higher_thresholds | decline | 362 | 267 | 73.7569% | 72.2494% | 200.9142937246273166 | 190 |

### Chất lượng dữ liệu và phạm vi kiểm tra

Saved final-test reliability aggregation; raw feature missingness chưa có trong monitor payload

| Control/KPI | Actual | Formula/support | Diễn giải |
| --- | --- | --- | --- |
| Reliability support coverage | 100.0000% | 3001 bin clients / 3001 final clients | Kiểm tra population aggregation; không chứng minh probability calibration. |
| Empty reliability bins | 1 | Count bins with zero clients | Empty event rate giữ Unavailable; không thêm zero estimates. |
| Raw feature missingness | Unavailable | Requires source feature-level quality profile | Chưa có nguyên liệu trong monitor; không infer từ imputed model features. |

- Random split không là temporal validation. Nguồn Taiwan 2005 là historical booked-card benchmark; chưa thiết lập live freshness SLA.

### Bước phân tích tiếp theo

Đọc policy/subgroup, intended use và OOT requirements trước quyết định triển khai; đây là saved benchmark.

## 4. P2: Mortgage — stock quality, biến động và loss coverage

Whole frozen Freddie sample · 2026-03 · selected history 36 periods · count

### Nhận xét từ dữ liệu

- D3 share hiện tại 0.1883% từ 18 / 9,557 theo basis count.
- So baseline đã chọn: numerator contribution -0.0825 pp, denominator contribution 0.0027 pp. Đó là phân rã số học, không kết luận borrower deterioration/cure.
- Observed loss có 374 / 381 resolved cases; gate blocked. Mean uncapped severity là average case ratio, không weighted LGD.
- Transitions/episode counts là toàn kỳ, segment all; không bị cắt theo history window. Sustained cure confirmed ở tháng CURRENT nonterminal thứ ba liên tiếp sau D3; gaps/unknown phá linkage; không backdate hoặc coi terminal CURRENT là cure.

### Định nghĩa và actual của từng KPI

#### 1. Reported loans

**Actual:** 9,698. **Công thức/support:** active + terminal observations.

**Diễn giải:** Monthly stock; không cộng qua tháng thành unique loans.

**So sánh 2026-02:** baseline 9,804; thay đổi tuyệt đối -106; tương đối -1.0812%.

#### 2. Active loans

**Actual:** 9,557. **Công thức/support:** reported − terminal.

**Diễn giải:** Đọc cùng exits/population change.

**So sánh 2026-02:** baseline 9,698; thay đổi tuyệt đối -141; tương đối -1.4539%.

#### 3. Active reported principal

**Actual:** 915,208,989.12 USD. **Công thức/support:** Σ known active UPB.

**Diễn giải:** Không phải EAD hoặc owned assets.

**So sánh 2026-02:** baseline 928,246,113.34 USD; thay đổi tuyệt đối -13,037,124.22 USD; tương đối -1.4045%.

#### 4. D3 active loans

**Actual:** 18. **Công thức/support:** Count active state D3.

**Diễn giải:** Không phải count new defaults trong tháng.

**So sánh 2026-02:** baseline 26; thay đổi tuyệt đối -8; tương đối -30.7692%.

#### 5. D3 share — selected basis

**Actual:** 0.1883%. **Công thức/support:** 18 / 9557.

**Diễn giải:** State-usable active denominator; không phải model PD.

**So sánh 2026-02:** baseline 0.2681%; thay đổi tuyệt đối -0.0798 điểm phần trăm; tương đối -29.7478%.

#### 6. D3 share — same month prior year

**Actual:** 0.1883%. **Công thức/support:** Current share vs matching calendar month.

**Diễn giải:** Stock populations thay đổi; không causal attribution.

**So sánh 2025-03:** baseline 0.2659%; thay đổi tuyệt đối -0.0775 điểm phần trăm; tương đối -29.1633%.

#### 7. Unknown active-state share

**Actual:** 0.0000%. **Công thức/support:** unknown active / active.

**Diễn giải:** Unknown không gán current/non-event.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 8. Loss resolution coverage

**Actual:** 98.1627%. **Công thức/support:** reported loss loans / loss-terminal loans.

**Diễn giải:** Loss subset không là toàn book; xem gate/partial components.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 9. Reported loss sum

**Actual:** 18,659,957.55 USD. **Công thức/support:** Σ observed reported loss on supported terminal subset.

**Diễn giải:** Historical realized components; không expected loss.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 10. Adjacent pairs — lifetime

**Actual:** 4,460,559. **Công thức/support:** Σ adjacent transition cell pairs; segment all.

**Diễn giải:** Repeated loan-month pairs, không unique loans; không áp monthly history window.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 11. Missing opening-balance pair share

**Actual:** 0.0000%. **Công thức/support:** Σ missing_balance_pairs / Σ pairs.

**Diễn giải:** Opening UPB weight missingness; không imputing zero.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 12. CURRENT → D3PLUS adjacent share

**Actual:** 0.0007%. **Công thức/support:** Cell pairs / origin pairs; UPB basis dùng opening balance.

**Diễn giải:** Lifetime observed one-step movement; không PD12 hoặc tổng mọi đường vào D3.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 13. D3PLUS → CURRENT adjacent share

**Actual:** 7.4542%. **Công thức/support:** Cell pairs / origin pairs; UPB basis dùng opening balance.

**Diễn giải:** Adjacent movement; không sustained cure rate.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 14. FIRST_OBSERVED_D3 events

**Actual:** 1,713. **Công thức/support:** Forward-only confirmed episode event count; toàn kỳ.

**Diễn giải:** Repeated events có thể cùng loan; event count không là cure/redefault probability.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 15. ONE_MONTH_CURE events

**Actual:** 1,694. **Công thức/support:** Forward-only confirmed episode event count; toàn kỳ.

**Diễn giải:** Repeated events có thể cùng loan; event count không là cure/redefault probability.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 16. SUSTAINED_CURE_CONFIRMED events

**Actual:** 1,224. **Công thức/support:** Forward-only confirmed episode event count; toàn kỳ.

**Diễn giải:** Repeated events có thể cùng loan; event count không là cure/redefault probability.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 17. REDEFAULT_AFTER_SUSTAINED_CURE events

**Actual:** 271. **Công thức/support:** Forward-only confirmed episode event count; toàn kỳ.

**Diễn giải:** Repeated events có thể cùng loan; event count không là cure/redefault probability.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 18. FIRST_OBSERVED_D3 complete 12m follow-up share

**Actual:** 70.6363%. **Công thức/support:** 1210 complete events / 1713 confirmed events.

**Diễn giải:** Follow-up availability; không survival, cure hoặc treatment success probability.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 19. SUSTAINED_CURE_CONFIRMED complete 12m follow-up share

**Actual:** 79.9837%. **Công thức/support:** 979 complete events / 1224 confirmed events.

**Diễn giải:** Follow-up availability; không survival, cure hoặc treatment success probability.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

### Phân rã biến động D3

Δ(n/d) = (n1−n0)/d0 + n1×(1/d1−1/d0)

Numerator-first arithmetic decomposition; order-dependent, không causal proof.

| Thành phần | Điểm phần trăm |
| --- | --- |
| numerator_effect | -0.082491 |
| denominator_effect | +0.002738 |
| total_change | -0.079753 |

Giữ mẫu số kỳ trước cho bước đổi tử số, rồi giữ tử số kỳ hiện tại cho bước đổi mẫu số. Hai phần cộng đúng thay đổi tỷ lệ; đổi thứ tự có thể đổi phân bổ. Phép tính không chứng minh cure, deterioration hoặc tác động chính sách.

### So sánh segments tại kỳ hiện tại

| Segment | Active | D3 count | Usable count | D3 count share | D3 UPB share |
| --- | --- | --- | --- | --- | --- |
| non_relief | 6,169 | 7 | 6,169 | 0.1135% | 0.1953% |
| relief | 3,388 | 11 | 3,388 | 0.3247% | 0.3475% |

### Selected monthly history

| Month | Active | D3 count | D3 UPB USD | D3 count share | D3 UPB share |
| --- | --- | --- | --- | --- | --- |
| 2023-04 | 13,136 | 56 | $7,810,118 | 0.4263% | 0.5484% |
| 2023-05 | 13,033 | 54 | $7,153,167 | 0.4143% | 0.5091% |
| 2023-06 | 12,936 | 43 | $6,701,239 | 0.3324% | 0.4829% |
| 2023-07 | 12,836 | 44 | $6,663,987 | 0.3428% | 0.4864% |
| 2023-08 | 12,725 | 46 | $6,941,933 | 0.3615% | 0.5135% |
| 2023-09 | 12,621 | 39 | $6,176,946 | 0.3090% | 0.4626% |
| 2023-10 | 12,545 | 42 | $6,769,060 | 0.3348% | 0.5122% |
| 2023-11 | 12,453 | 40 | $6,273,201 | 0.3212% | 0.4803% |
| 2023-12 | 12,352 | 39 | $6,279,277 | 0.3157% | 0.4868% |
| 2024-01 | 12,263 | 41 | $6,070,642 | 0.3343% | 0.4760% |
| 2024-02 | 12,191 | 40 | $6,211,396 | 0.3281% | 0.4921% |
| 2024-03 | 12,080 | 39 | $5,848,864 | 0.3228% | 0.4694% |
| 2024-04 | 11,998 | 35 | $4,928,717 | 0.2917% | 0.4000% |
| 2024-05 | 11,893 | 32 | $4,261,325 | 0.2691% | 0.3504% |
| 2024-06 | 11,790 | 29 | $4,045,532 | 0.2460% | 0.3364% |
| 2024-07 | 11,672 | 28 | $3,852,048 | 0.2399% | 0.3247% |
| 2024-08 | 11,586 | 27 | $3,400,252 | 0.2330% | 0.2904% |
| 2024-09 | 11,490 | 29 | $3,490,664 | 0.2524% | 0.3018% |
| 2024-10 | 11,380 | 30 | $3,349,343 | 0.2636% | 0.2934% |
| 2024-11 | 11,298 | 29 | $3,462,509 | 0.2567% | 0.3067% |
| 2024-12 | 11,199 | 29 | $3,219,032 | 0.2590% | 0.2887% |
| 2025-01 | 11,111 | 30 | $3,344,583 | 0.2700% | 0.3036% |
| 2025-02 | 11,015 | 36 | $3,840,726 | 0.3268% | 0.3529% |
| 2025-03 | 10,907 | 29 | $3,284,979 | 0.2659% | 0.3060% |
| 2025-04 | 10,802 | 34 | $3,642,971 | 0.3148% | 0.3438% |
| 2025-05 | 10,693 | 29 | $3,132,396 | 0.2712% | 0.3000% |
| 2025-06 | 10,589 | 29 | $3,007,117 | 0.2739% | 0.2918% |
| 2025-07 | 10,482 | 29 | $2,925,278 | 0.2767% | 0.2876% |
| 2025-08 | 10,374 | 30 | $3,107,361 | 0.2892% | 0.3093% |
| 2025-09 | 10,262 | 28 | $2,901,787 | 0.2729% | 0.2930% |
| 2025-10 | 10,121 | 22 | $2,435,190 | 0.2174% | 0.2496% |
| 2025-11 | 10,024 | 27 | $3,363,470 | 0.2694% | 0.3490% |
| 2025-12 | 9,905 | 27 | $3,543,519 | 0.2726% | 0.3726% |
| 2026-01 | 9,804 | 25 | $3,111,297 | 0.2550% | 0.3308% |
| 2026-02 | 9,698 | 26 | $2,860,540 | 0.2681% | 0.3082% |
| 2026-03 | 9,557 | 18 | $2,247,016 | 0.1883% | 0.2455% |

### Loss bridge — supported reported subset

| Component | Signed USD |
| --- | --- |
| removal_upb | $63,571,075 |
| net_sales_proceeds | -$50,439,065 |
| delinquent_accrued_interest | $3,602,168 |
| total_expenses | $5,717,231 |
| mi_recoveries | -$3,096,865 |
| non_mi_recoveries | -$694,587 |

### Lifetime adjacent-state support — count và opening UPB

| Origin | Destination | Pairs | Origin pairs | Opening UPB USD | Origin opening UPB USD | Count share | UPB share | Distinct loans | Missing balance pairs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CURRENT | CREDIT_TERMINATION | 3 | 4,415,313 | $607,581 | $718,179,558,408 | 0.0001% | 0.0001% | 3 | 0 |
| CURRENT | CURRENT | 4,363,335 | 4,415,313 | $710,099,166,363 | $718,179,558,408 | 98.8228% | 98.8749% | 49,934 | 0 |
| CURRENT | D1 | 12,474 | 4,415,313 | $1,980,901,010 | $718,179,558,408 | 0.2825% | 0.2758% | 5,762 | 0 |
| CURRENT | D2 | 69 | 4,415,313 | $12,847,246 | $718,179,558,408 | 0.0016% | 0.0018% | 62 | 0 |
| CURRENT | D3PLUS | 31 | 4,415,313 | $5,367,206 | $718,179,558,408 | 0.0007% | 0.0007% | 29 | 0 |
| CURRENT | OTHER_TERMINATION | 258 | 4,415,313 | $48,235,271 | $718,179,558,408 | 0.0058% | 0.0067% | 258 | 0 |
| CURRENT | PREPAID_OR_MATURED | 39,143 | 4,415,313 | $6,032,433,731 | $718,179,558,408 | 0.8865% | 0.8400% | 39,143 | 0 |
| D1 | CREDIT_TERMINATION | 3 | 21,216 | $942,712 | $3,372,768,962 | 0.0141% | 0.0280% | 3 | 0 |
| D1 | CURRENT | 9,342 | 21,216 | $1,480,818,483 | $3,372,768,962 | 44.0328% | 43.9051% | 4,479 | 0 |
| D1 | D1 | 7,936 | 21,216 | $1,269,761,751 | $3,372,768,962 | 37.4057% | 37.6475% | 1,495 | 0 |
| D1 | D2 | 3,606 | 21,216 | $575,985,188 | $3,372,768,962 | 16.9966% | 17.0775% | 2,147 | 0 |
| D1 | D3PLUS | 20 | 21,216 | $3,464,994 | $3,372,768,962 | 0.0943% | 0.1027% | 20 | 0 |
| D1 | OTHER_TERMINATION | 28 | 21,216 | $4,351,803 | $3,372,768,962 | 0.1320% | 0.1290% | 28 | 0 |
| D1 | PREPAID_OR_MATURED | 281 | 21,216 | $37,444,032 | $3,372,768,962 | 1.3245% | 1.1102% | 281 | 0 |
| D2 | CREDIT_TERMINATION | 4 | 5,409 | $667,418 | $878,142,245 | 0.0740% | 0.0760% | 4 | 0 |
| D2 | CURRENT | 816 | 5,409 | $121,511,209 | $878,142,245 | 15.0860% | 13.8373% | 639 | 0 |
| D2 | D1 | 691 | 5,409 | $106,124,525 | $878,142,245 | 12.7750% | 12.0851% | 382 | 0 |
| D2 | D2 | 1,491 | 5,409 | $245,687,095 | $878,142,245 | 27.5652% | 27.9781% | 494 | 0 |
| D2 | D3PLUS | 2,316 | 5,409 | $389,673,946 | $878,142,245 | 42.8175% | 44.3748% | 1,671 | 0 |
| D2 | OTHER_TERMINATION | 9 | 5,409 | $1,335,052 | $878,142,245 | 0.1664% | 0.1520% | 9 | 0 |
| D2 | PREPAID_OR_MATURED | 81 | 5,409 | $13,014,320 | $878,142,245 | 1.4975% | 1.4820% | 81 | 0 |
| D2 | REO | 1 | 5,409 | $128,682 | $878,142,245 | 0.0185% | 0.0147% | 1 | 0 |
| D3PLUS | CREDIT_TERMINATION | 211 | 17,668 | $35,888,360 | $3,064,114,935 | 1.1942% | 1.1712% | 211 | 0 |
| D3PLUS | CURRENT | 1,317 | 17,668 | $225,821,387 | $3,064,114,935 | 7.4542% | 7.3699% | 1,053 | 0 |
| D3PLUS | D1 | 162 | 17,668 | $23,405,154 | $3,064,114,935 | 0.9169% | 0.7638% | 141 | 0 |
| D3PLUS | D2 | 253 | 17,668 | $45,073,873 | $3,064,114,935 | 1.4320% | 1.4710% | 182 | 0 |
| D3PLUS | D3PLUS | 15,319 | 17,668 | $2,668,830,794 | $3,064,114,935 | 86.7048% | 87.0996% | 1,432 | 0 |
| D3PLUS | OTHER_TERMINATION | 58 | 17,668 | $10,800,471 | $3,064,114,935 | 0.3283% | 0.3525% | 58 | 0 |
| D3PLUS | PREPAID_OR_MATURED | 229 | 17,668 | $35,347,638 | $3,064,114,935 | 1.2961% | 1.1536% | 229 | 0 |
| D3PLUS | REO | 119 | 17,668 | $18,947,259 | $3,064,114,935 | 0.6735% | 0.6184% | 119 | 0 |
| REO | CREDIT_TERMINATION | 118 | 953 | $18,695,708 | $156,454,283 | 12.3820% | 11.9496% | 118 | 0 |
| REO | OTHER_TERMINATION | 2 | 953 | $380,234 | $156,454,283 | 0.2099% | 0.2430% | 2 | 0 |
| REO | REO | 833 | 953 | $137,378,342 | $156,454,283 | 87.4082% | 87.8073% | 120 | 0 |

### Confirmed events — 12-month follow-up support

| Event | Follow-up status | Events | Distinct loans | Observed nonterminal months |
| --- | --- | --- | --- | --- |
| FIRST_OBSERVED_D3 | complete_nonterminal_followup | 1,210 | 1,210 | 14,520 |
| FIRST_OBSERVED_D3 | end_of_source | 17 | 17 | 94 |
| FIRST_OBSERVED_D3 | terminal_at_confirmation | 31 | 31 | 0 |
| FIRST_OBSERVED_D3 | terminal_exit | 455 | 455 | 2,492 |
| ONE_MONTH_CURE | complete_nonterminal_followup | 1,345 | 933 | 16,140 |
| ONE_MONTH_CURE | end_of_source | 48 | 39 | 228 |
| ONE_MONTH_CURE | terminal_exit | 301 | 268 | 1,586 |
| REDEFAULT_AFTER_SUSTAINED_CURE | complete_nonterminal_followup | 208 | 167 | 2,496 |
| REDEFAULT_AFTER_SUSTAINED_CURE | end_of_source | 11 | 11 | 61 |
| REDEFAULT_AFTER_SUSTAINED_CURE | terminal_at_confirmation | 4 | 4 | 0 |
| REDEFAULT_AFTER_SUSTAINED_CURE | terminal_exit | 48 | 48 | 213 |
| SUSTAINED_CURE_CONFIRMED | complete_nonterminal_followup | 979 | 845 | 11,748 |
| SUSTAINED_CURE_CONFIRMED | end_of_source | 26 | 26 | 111 |
| SUSTAINED_CURE_CONFIRMED | terminal_exit | 219 | 219 | 1,146 |

### Chất lượng dữ liệu và phạm vi kiểm tra

whole_frozen_sample · d01-frozen-quality-monitor-v1 · source coverage 2012-01-01–2026-03-01

| Control/KPI | Actual | Formula/support | Diễn giải |
| --- | --- | --- | --- |
| classic_fico missing share | 0.0000% | 0 / 50000 | Availability in this frozen source; a causal reason or drift is not established. |
| original_dti missing share | 34.8000% | 17400 / 50000 | Availability in this frozen source; a causal reason or drift is not established. |
| original_ltv missing share | 0.0060% | 3 / 50000 | Availability in this frozen source; a causal reason or drift is not established. |
| original_cltv missing share | 0.0060% | 3 / 50000 | Availability in this frozen source; a causal reason or drift is not established. |
| vantagescore missing share | 100.0000% | 50000 / 50000 | Availability in this frozen source; a causal reason or drift is not established. |
| property_valuation_method missing share | 100.0000% | 50000 / 50000 | Availability in this frozen source; a causal reason or drift is not established. |
| duplicate_origination_keys | 0 | Saved canonical integrity count | If nonzero, stop dependent analytics; inspect source keys and parent joins. |
| duplicate_monthly_keys | 0 | Saved canonical integrity count | If nonzero, stop dependent analytics; inspect source keys and parent joins. |
| orphan_performance_rows | 0 | Saved canonical integrity count | If nonzero, stop dependent analytics; inspect source keys and parent joins. |
| loans_without_performance | 0 | Saved canonical integrity count | Inspect observation/censoring exclusions; do not fill absent performance as current. |
| loans_with_gaps | 0 | Saved canonical integrity count | Inspect observation/censoring exclusions; do not fill absent performance as current. |

- Missingness ở grain loan, không là monthly missing count hoặc drift. Unknown state và model qualification được đọc riêng.
- frozen_historical_source_not_live_feed; tuổi snapshot không tự là late-feed alert.

### Bước phân tích tiếp theo

Đọc transitions, individual timelines và competing exits để investigate movement; không diễn giải stock decrease thành causal cure.

### Baseline control

| Field | Value |
| --- | --- |
| requested | auto |
| current_period | 2026-03-01 |
| resolved_period | 2026-02-01 |
| status | EXACT_PREVIOUS_CALENDAR_MONTH |
| rule | Auto chỉ lấy đúng tháng lịch trước; manual dùng exact prior period. Không fallback nearest; baseline không áp lifetime/quality/cash-replay scope. |

Baseline chính chỉ áp các delta/decomposition tương ứng, không thay current actual. Chọn manual prior period hoặc tắt baseline trong app; không fallback nearest khi không có exact period. P2 YoY cùng tháng là comparison riêng, overview chart giữ monthly delta; lifetime transitions, data-quality controls và selected cash replay có scopes riêng.

## 5. P3: Business — SBA outcomes, amounts và data grain

SBA source records · 7A/504 separate · status stock snapshot; borrower identities chưa deduplicate

### Nhận xét từ dữ liệu

- 7A: 220,688 charged-off records / 1,961,455 (11.25%). Approval amounts và status coverage khác risk exposure; không so hai programs như controlled cohorts.
- 504: 12,169 charged-off records / 229,049 (5.31%). Approval amounts và status coverage khác risk exposure; không so hai programs như controlled cohorts.
- AAPL: report 2025-09-27, filed 2025-10-31; 8 / 8 supported fields. Không thay missing/ambiguous facts bằng zero.
- MSFT: report 2026-06-30, filed 2026-07-29; 8 / 8 supported fields. Không thay missing/ambiguous facts bằng zero.
- F: report 2025-12-31, filed 2026-02-11; 7 / 8 supported fields. Không thay missing/ambiguous facts bằng zero.
- GM: report 2025-12-31, filed 2026-01-27; 7 / 8 supported fields. Không thay missing/ambiguous facts bằng zero.
- SEC và SBA là hai populations riêng. Cutoff filing date 2026-10-10; latest supported annual filing từng issuer có report date khác nhau, không coi đây là same-year peer ranking hoặc historical-vintage availability.

### Định nghĩa và actual của từng KPI

#### 1. 7A source records

**Actual:** 1,961,455. **Công thức/support:** Σ program status records.

**Diễn giải:** Source records; không unique borrowers.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 2. 7A charged-off status share

**Actual:** 11.2512%. **Công thức/support:** 220688 / 1961455.

**Diễn giải:** Status mix; không fixed-horizon default incidence hoặc PD.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 3. 7A reported approval amount

**Actual:** 601,499,996,158.95 USD. **Công thức/support:** Σ known reported approval amounts.

**Diễn giải:** Approval measure; không outstanding principal hay EAD.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 4. 7A reported chargeoff amount

**Actual:** 23,875,313,169.43 USD. **Công thức/support:** Σ known reported chargeoff amounts.

**Diễn giải:** Reported amounts trên source stock; không net LGD hoặc current exposure.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 5. 7A approval amount coverage

**Actual:** 100.0000%. **Công thức/support:** 1961455 known records / 1961455.

**Diễn giải:** Đọc coverage trước amount comparison.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 6. 504 source records

**Actual:** 229,049. **Công thức/support:** Σ program status records.

**Diễn giải:** Source records; không unique borrowers.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 7. 504 charged-off status share

**Actual:** 5.3128%. **Công thức/support:** 12169 / 229049.

**Diễn giải:** Status mix; không fixed-horizon default incidence hoặc PD.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 8. 504 reported approval amount

**Actual:** 150,885,333,006.00 USD. **Công thức/support:** Σ known reported approval amounts.

**Diễn giải:** Approval measure; không outstanding principal hay EAD.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 9. 504 reported chargeoff amount

**Actual:** 5,594,082,573.43 USD. **Công thức/support:** Σ known reported chargeoff amounts.

**Diễn giải:** Reported amounts trên source stock; không net LGD hoặc current exposure.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 10. 504 approval amount coverage

**Actual:** 100.0000%. **Công thức/support:** 229049 known records / 229049.

**Diễn giải:** Đọc coverage trước amount comparison.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 11. AAPL · Current ratio

**Actual:** 0.893293. **Công thức/support:** current_assets / current_liabilities.

**Diễn giải:** Status supported; report 2025-09-27, filed 2025-10-31. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 12. AAPL · Liabilities / assets

**Actual:** 79.4753%. **Công thức/support:** liabilities / assets.

**Diễn giải:** Status supported; report 2025-09-27, filed 2025-10-31. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 13. AAPL · Net income margin

**Actual:** 26.9151%. **Công thức/support:** net_income / revenue.

**Diễn giải:** Status supported; report 2025-09-27, filed 2025-10-31. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 14. AAPL · Operating cashflow / revenue

**Actual:** 26.7882%. **Công thức/support:** operating_cashflow / revenue.

**Diễn giải:** Status supported; report 2025-09-27, filed 2025-10-31. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 15. MSFT · Current ratio

**Actual:** 1.230327. **Công thức/support:** current_assets / current_liabilities.

**Diễn giải:** Status supported; report 2026-06-30, filed 2026-07-29. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 16. MSFT · Liabilities / assets

**Actual:** 41.6665%. **Công thức/support:** liabilities / assets.

**Diễn giải:** Status supported; report 2026-06-30, filed 2026-07-29. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 17. MSFT · Net income margin

**Actual:** 40.3054%. **Công thức/support:** net_income / revenue.

**Diễn giải:** Status supported; report 2026-06-30, filed 2026-07-29. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 18. MSFT · Operating cashflow / revenue

**Actual:** 55.1276%. **Công thức/support:** operating_cashflow / revenue.

**Diễn giải:** Status supported; report 2026-06-30, filed 2026-07-29. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 19. F · Current ratio

**Actual:** 1.074828. **Công thức/support:** current_assets / current_liabilities.

**Diễn giải:** Status supported; report 2025-12-31, filed 2026-02-11. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 20. F · Liabilities / assets

**Actual:** 87.5571%. **Công thức/support:** liabilities / assets.

**Diễn giải:** Status supported; report 2025-12-31, filed 2026-02-11. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 21. F · Net income margin

**Actual:** Unavailable. **Công thức/support:** net_income / revenue.

**Diễn giải:** Status missing_or_ambiguous_input; report 2025-12-31, filed 2026-02-11. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 22. F · Operating cashflow / revenue

**Actual:** 11.3645%. **Công thức/support:** operating_cashflow / revenue.

**Diễn giải:** Status supported; report 2025-12-31, filed 2026-02-11. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 23. GM · Current ratio

**Actual:** 1.165253. **Công thức/support:** current_assets / current_liabilities.

**Diễn giải:** Status supported; report 2025-12-31, filed 2026-01-27. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 24. GM · Liabilities / assets

**Actual:** 77.5430%. **Công thức/support:** liabilities / assets.

**Diễn giải:** Status supported; report 2025-12-31, filed 2026-01-27. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 25. GM · Net income margin

**Actual:** Unavailable. **Công thức/support:** net_income / revenue.

**Diễn giải:** Status missing_or_ambiguous_input; report 2025-12-31, filed 2026-01-27. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 26. GM · Operating cashflow / revenue

**Actual:** Unavailable. **Công thức/support:** operating_cashflow / revenue.

**Diễn giải:** Status missing_or_ambiguous_input; report 2025-12-31, filed 2026-01-27. Source filing-specific; không issuer PD/rating hoặc covenant conclusion.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

### Scope từng issuer và đường dẫn evidence

| Issuer | CIK | Accession | Report date | Filed | Cutoff | SEC filing |
| --- | --- | --- | --- | --- | --- | --- |
| AAPL | 0000320193 | 0000320193-25-000079 | 2025-09-27 | 2025-10-31 | 2026-10-10 | https://www.sec.gov/Archives/edgar/data/320193/0000320193-25-000079-index.html |
| MSFT | 0000789019 | 0001193125-26-323660 | 2026-06-30 | 2026-07-29 | 2026-10-10 | https://www.sec.gov/Archives/edgar/data/789019/0001193125-26-323660-index.html |
| F | 0000037996 | 0000037996-26-000015 | 2025-12-31 | 2026-02-11 | 2026-10-10 | https://www.sec.gov/Archives/edgar/data/37996/0000037996-26-000015-index.html |
| GM | 0001467858 | 0001467858-26-000013 | 2025-12-31 | 2026-01-27 | 2026-10-10 | https://www.sec.gov/Archives/edgar/data/1467858/0001467858-26-000013-index.html |

Ratio source giữ exact values; current ratio dùng current assets/current liabilities, liabilities/assets không thay debt/EBITDA, net margin không thay interest coverage, OCF/revenue không thay DSCR. Các fields missing/ambiguous làm ratio Unavailable. SEC snapshot không phải issuer default dataset hoặc historical-vintage snapshot.

### Toàn bộ status và program denominators

| Program | Status | Records | Program share | Approval USD | Chargeoff USD | Known approval rows |
| --- | --- | --- | --- | --- | --- | --- |
| 7A | cancelled | 242,790 | 12.38% | $74,256,027,517 | $0 | 242,790 |
| 7A | charged_off | 220,688 | 11.25% | $38,298,463,056 | $23,875,313,169 | 220,688 |
| 7A | disbursed_status_withheld | 297,494 | 15.17% | $168,918,092,596 | $0 | 297,494 |
| 7A | paid_in_full | 1,179,360 | 60.13% | $312,271,576,773 | $0 | 1,179,360 |
| 7A | undisbursed | 21,123 | 1.08% | $7,755,836,218 | $0 | 21,123 |
| 504 | cancelled | 32,314 | 14.11% | $21,829,755,595 | $0 | 32,314 |
| 504 | charged_off | 12,169 | 5.31% | $7,000,813,486 | $5,594,082,573 | 12,169 |
| 504 | closed_other_legacy | 339 | 0.15% | $124,078,417 | $0 | 339 |
| 504 | disbursed_status_withheld | 61,266 | 26.75% | $49,369,061,539 | $0 | 61,266 |
| 504 | paid_in_full | 114,445 | 49.97% | $60,930,425,969 | $0 | 114,445 |
| 504 | undisbursed | 8,516 | 3.72% | $11,631,198,000 | $0 | 8,516 |

### SEC financial fields — exact values, periods và support

| Issuer | Accession | Field | Status | USD exact | Start | End | Candidates |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL | 0000320193-25-000079 | assets | supported | 359241000000 | Instant / unavailable | 2025-09-27 | 1 |
| AAPL | 0000320193-25-000079 | liabilities | supported | 285508000000 | Instant / unavailable | 2025-09-27 | 1 |
| AAPL | 0000320193-25-000079 | current_assets | supported | 147957000000 | Instant / unavailable | 2025-09-27 | 1 |
| AAPL | 0000320193-25-000079 | current_liabilities | supported | 165631000000 | Instant / unavailable | 2025-09-27 | 1 |
| AAPL | 0000320193-25-000079 | cash_equivalents | supported | 35934000000 | Instant / unavailable | 2025-09-27 | 1 |
| AAPL | 0000320193-25-000079 | revenue | supported | 416161000000 | 2024-09-29 | 2025-09-27 | 1 |
| AAPL | 0000320193-25-000079 | net_income | supported | 112010000000 | 2024-09-29 | 2025-09-27 | 1 |
| AAPL | 0000320193-25-000079 | operating_cashflow | supported | 111482000000 | 2024-09-29 | 2025-09-27 | 1 |
| MSFT | 0001193125-26-323660 | assets | supported | 758376000000 | Instant / unavailable | 2026-06-30 | 1 |
| MSFT | 0001193125-26-323660 | liabilities | supported | 315989000000 | Instant / unavailable | 2026-06-30 | 1 |
| MSFT | 0001193125-26-323660 | current_assets | supported | 207710000000 | Instant / unavailable | 2026-06-30 | 1 |
| MSFT | 0001193125-26-323660 | current_liabilities | supported | 168825000000 | Instant / unavailable | 2026-06-30 | 1 |
| MSFT | 0001193125-26-323660 | cash_equivalents | supported | 20935000000 | Instant / unavailable | 2026-06-30 | 1 |
| MSFT | 0001193125-26-323660 | revenue | supported | 331839000000 | 2025-07-01 | 2026-06-30 | 1 |
| MSFT | 0001193125-26-323660 | net_income | supported | 133749000000 | 2025-07-01 | 2026-06-30 | 1 |
| MSFT | 0001193125-26-323660 | operating_cashflow | supported | 182935000000 | 2025-07-01 | 2026-06-30 | 1 |
| F | 0000037996-26-000015 | assets | supported | 289160000000 | Instant / unavailable | 2025-12-31 | 1 |
| F | 0000037996-26-000015 | liabilities | supported | 253180000000 | Instant / unavailable | 2025-12-31 | 1 |
| F | 0000037996-26-000015 | current_assets | supported | 123487000000 | Instant / unavailable | 2025-12-31 | 1 |
| F | 0000037996-26-000015 | current_liabilities | supported | 114890000000 | Instant / unavailable | 2025-12-31 | 1 |
| F | 0000037996-26-000015 | cash_equivalents | supported | 23356000000 | Instant / unavailable | 2025-12-31 | 1 |
| F | 0000037996-26-000015 | revenue | supported | 187267000000 | 2025-01-01 | 2025-12-31 | 1 |
| F | 0000037996-26-000015 | net_income | missing | Unavailable | Instant / unavailable | 2025-12-31 | 0 |
| F | 0000037996-26-000015 | operating_cashflow | supported | 21282000000 | 2025-01-01 | 2025-12-31 | 1 |
| GM | 0001467858-26-000013 | assets | supported | 281284000000 | Instant / unavailable | 2025-12-31 | 1 |
| GM | 0001467858-26-000013 | liabilities | supported | 218116000000 | Instant / unavailable | 2025-12-31 | 1 |
| GM | 0001467858-26-000013 | current_assets | supported | 108767000000 | Instant / unavailable | 2025-12-31 | 1 |
| GM | 0001467858-26-000013 | current_liabilities | supported | 93342000000 | Instant / unavailable | 2025-12-31 | 1 |
| GM | 0001467858-26-000013 | cash_equivalents | supported | 20945000000 | Instant / unavailable | 2025-12-31 | 1 |
| GM | 0001467858-26-000013 | revenue | ambiguous | Unavailable | Instant / unavailable | 2025-12-31 | 2 |
| GM | 0001467858-26-000013 | net_income | supported | 2697000000 | 2025-01-01 | 2025-12-31 | 1 |
| GM | 0001467858-26-000013 | operating_cashflow | supported | 26867000000 | 2025-01-01 | 2025-12-31 | 1 |

### SEC concept evidence — conflicts retained

| Issuer | Accession | Field | Concept | Unit | Exact value | Start | End | Filed | Ordinal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL | 0000320193-25-000079 | assets | us-gaap:Assets | USD | 359241000000 | Instant | 2025-09-27 | 2025-10-31 | 139 |
| AAPL | 0000320193-25-000079 | liabilities | us-gaap:Liabilities | USD | 285508000000 | Instant | 2025-09-27 | 2025-10-31 | 137 |
| AAPL | 0000320193-25-000079 | current_assets | us-gaap:AssetsCurrent | USD | 147957000000 | Instant | 2025-09-27 | 2025-10-31 | 137 |
| AAPL | 0000320193-25-000079 | current_liabilities | us-gaap:LiabilitiesCurrent | USD | 165631000000 | Instant | 2025-09-27 | 2025-10-31 | 137 |
| AAPL | 0000320193-25-000079 | cash_equivalents | us-gaap:CashAndCashEquivalentsAtCarryingValue | USD | 35934000000 | Instant | 2025-09-27 | 2025-10-31 | 221 |
| AAPL | 0000320193-25-000079 | revenue | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | USD | 416161000000 | 2024-09-29 | 2025-09-27 | 2025-10-31 | 111 |
| AAPL | 0000320193-25-000079 | net_income | us-gaap:NetIncomeLoss | USD | 112010000000 | 2024-09-29 | 2025-09-27 | 2025-10-31 | 332 |
| AAPL | 0000320193-25-000079 | operating_cashflow | us-gaap:NetCashProvidedByUsedInOperatingActivities | USD | 111482000000 | 2024-09-29 | 2025-09-27 | 2025-10-31 | 130 |
| MSFT | 0001193125-26-323660 | assets | us-gaap:Assets | USD | 758376000000 | Instant | 2026-06-30 | 2026-07-29 | 141 |
| MSFT | 0001193125-26-323660 | liabilities | us-gaap:Liabilities | USD | 315989000000 | Instant | 2026-06-30 | 2026-07-29 | 133 |
| MSFT | 0001193125-26-323660 | current_assets | us-gaap:AssetsCurrent | USD | 207710000000 | Instant | 2026-06-30 | 2026-07-29 | 141 |
| MSFT | 0001193125-26-323660 | current_liabilities | us-gaap:LiabilitiesCurrent | USD | 168825000000 | Instant | 2026-06-30 | 2026-07-29 | 141 |
| MSFT | 0001193125-26-323660 | cash_equivalents | us-gaap:CashAndCashEquivalentsAtCarryingValue | USD | 20935000000 | Instant | 2026-06-30 | 2026-07-29 | 265 |
| MSFT | 0001193125-26-323660 | revenue | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | USD | 331839000000 | 2025-07-01 | 2026-06-30 | 2026-07-29 | 133 |
| MSFT | 0001193125-26-323660 | net_income | us-gaap:NetIncomeLoss | USD | 133749000000 | 2025-07-01 | 2026-06-30 | 2026-07-29 | 339 |
| MSFT | 0001193125-26-323660 | operating_cashflow | us-gaap:NetCashProvidedByUsedInOperatingActivities | USD | 182935000000 | 2025-07-01 | 2026-06-30 | 2026-07-29 | 169 |
| F | 0000037996-26-000015 | assets | us-gaap:Assets | USD | 289160000000 | Instant | 2025-12-31 | 2026-02-11 | 197 |
| F | 0000037996-26-000015 | liabilities | us-gaap:Liabilities | USD | 253180000000 | Instant | 2025-12-31 | 2026-02-11 | 136 |
| F | 0000037996-26-000015 | current_assets | us-gaap:AssetsCurrent | USD | 123487000000 | Instant | 2025-12-31 | 2026-02-11 | 77 |
| F | 0000037996-26-000015 | current_liabilities | us-gaap:LiabilitiesCurrent | USD | 114890000000 | Instant | 2025-12-31 | 2026-02-11 | 77 |
| F | 0000037996-26-000015 | cash_equivalents | us-gaap:CashAndCashEquivalentsAtCarryingValue | USD | 23356000000 | Instant | 2025-12-31 | 2026-02-11 | 204 |
| F | 0000037996-26-000015 | revenue | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | USD | 187267000000 | 2025-01-01 | 2025-12-31 | 2026-02-11 | 105 |
| F | 0000037996-26-000015 | operating_cashflow | us-gaap:NetCashProvidedByUsedInOperatingActivities | USD | 21282000000 | 2025-01-01 | 2025-12-31 | 2026-02-11 | 71 |
| GM | 0001467858-26-000013 | assets | us-gaap:Assets | USD | 281284000000 | Instant | 2025-12-31 | 2026-01-27 | 170 |
| GM | 0001467858-26-000013 | liabilities | us-gaap:Liabilities | USD | 218116000000 | Instant | 2025-12-31 | 2026-01-27 | 119 |
| GM | 0001467858-26-000013 | current_assets | us-gaap:AssetsCurrent | USD | 108767000000 | Instant | 2025-12-31 | 2026-01-27 | 113 |
| GM | 0001467858-26-000013 | current_liabilities | us-gaap:LiabilitiesCurrent | USD | 93342000000 | Instant | 2025-12-31 | 2026-01-27 | 113 |
| GM | 0001467858-26-000013 | cash_equivalents | us-gaap:CashAndCashEquivalentsAtCarryingValue | USD | 20945000000 | Instant | 2025-12-31 | 2026-01-27 | 153 |
| GM | 0001467858-26-000013 | revenue | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | USD | 167971000000 | 2025-01-01 | 2025-12-31 | 2026-01-27 | 80 |
| GM | 0001467858-26-000013 | revenue | us-gaap:Revenues | USD | 185019000000 | 2025-01-01 | 2025-12-31 | 2026-01-27 | 270 |
| GM | 0001467858-26-000013 | net_income | us-gaap:NetIncomeLoss | USD | 2697000000 | 2025-01-01 | 2025-12-31 | 2026-01-27 | 258 |
| GM | 0001467858-26-000013 | operating_cashflow | us-gaap:NetCashProvidedByUsedInOperatingActivities | USD | 26867000000 | 2025-01-01 | 2025-12-31 | 2026-01-27 | 99 |

### Chất lượng dữ liệu và phạm vi kiểm tra

SBA six source files, retained source-record grain; SEC controls theo issuer riêng

| Control/KPI | Actual | Formula/support | Diễn giải |
| --- | --- | --- | --- |
| SBA retained source rows | 2,190,504 | Σ retained_rows across source files | Phải khớp SBA records; không unique borrower count. |
| SBA exact duplicate excess share | 0.0907% | 1987 duplicate excess / 2190504 retained rows | Duplicate source rows được giữ; không tự deduplicate loan/business identities. |
| SBA invalid parsed field occurrences | 0 | Σ invalid_nonblank across files × fields | Một record có thể có nhiều field errors; không unique affected-row rate. |

- Blank PaidInFullDate/ChargeOffDate có thể là outcome chưa xảy ra; không kết luận tất cả là ingestion failure.
- Source flags như chargeoff_exceeds_approval cần field convention review; không tự loại rows. SEC ambiguous concepts giữ nguyên candidates; không chọn giá trị đẹp hơn.

#### SBA quality theo từng source file

| Source | Retained rows | Duplicate excess | Duplicate share | Disbursement before approval | Chargeoff exceeds approval | Raw/saved differing groups |
| --- | --- | --- | --- | --- | --- | --- |
| sba-504-fy1991_fy2009 | 111,066 | 11 | 0.0099% | 3 | 901 | 0 |
| sba-504-fy2010_present | 117,983 | 58 | 0.0492% | 0 | 58 | 0 |
| sba-7a-fy1991_fy1999 | 337,033 | 113 | 0.0335% | 507 | 758 | 0 |
| sba-7a-fy2000_fy2009 | 690,333 | 278 | 0.0403% | 13 | 3,736 | 0 |
| sba-7a-fy2010_fy2019 | 545,751 | 1,136 | 0.2082% | 421 | 1,205 | 0 |
| sba-7a-fy2020_present | 388,338 | 391 | 0.1007% | 0 | 326 | 0 |

#### SBA parse completeness — field denominator là retained source rows

| Source | Field | Blank | Blank share | Invalid nonblank | Precision loss |
| --- | --- | --- | --- | --- | --- |
| sba-504-fy1991_fy2009 | AsOfDate | 0 | 0.0000% | 0 | Not applicable |
| sba-504-fy1991_fy2009 | ApprovalDate | 0 | 0.0000% | 0 | Not applicable |
| sba-504-fy1991_fy2009 | FirstDisbursementDate | 17,906 | 16.1219% | 0 | Not applicable |
| sba-504-fy1991_fy2009 | PaidInFullDate | 33,246 | 29.9336% | 0 | Not applicable |
| sba-504-fy1991_fy2009 | ChargeOffDate | 99,820 | 89.8745% | 0 | Not applicable |
| sba-504-fy1991_fy2009 | GrossApproval | 0 | 0.0000% | 0 | 0 |
| sba-504-fy1991_fy2009 | GrossChargeOffAmount | 0 | 0.0000% | 0 | 0 |
| sba-504-fy1991_fy2009 | ThirdPartyDollars | 9,505 | 8.5580% | 0 | 0 |
| sba-504-fy1991_fy2009 | ApprovalFY | 0 | 0.0000% | 0 | 0 |
| sba-504-fy1991_fy2009 | TermInMonths | 0 | 0.0000% | 0 | 0 |
| sba-504-fy1991_fy2009 | JobsSupported | 0 | 0.0000% | 0 | 0 |
| sba-504-fy2010_present | AsOfDate | 0 | 0.0000% | 0 | Not applicable |
| sba-504-fy2010_present | ApprovalDate | 0 | 0.0000% | 0 | Not applicable |
| sba-504-fy2010_present | FirstDisbursementDate | 23,080 | 19.5621% | 0 | Not applicable |
| sba-504-fy2010_present | PaidInFullDate | 81,360 | 68.9591% | 0 | Not applicable |
| sba-504-fy2010_present | ChargeOffDate | 117,060 | 99.2177% | 0 | Not applicable |
| sba-504-fy2010_present | GrossApproval | 0 | 0.0000% | 0 | 0 |
| sba-504-fy2010_present | GrossChargeOffAmount | 0 | 0.0000% | 0 | 0 |
| sba-504-fy2010_present | ThirdPartyDollars | 419 | 0.3551% | 0 | 0 |
| sba-504-fy2010_present | ApprovalFY | 0 | 0.0000% | 0 | 0 |
| sba-504-fy2010_present | TermInMonths | 0 | 0.0000% | 0 | 0 |
| sba-504-fy2010_present | JobsSupported | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy1991_fy1999 | AsOfDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy1991_fy1999 | ApprovalDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy1991_fy1999 | FirstDisbursementDate | 43,915 | 13.0299% | 0 | Not applicable |
| sba-7a-fy1991_fy1999 | PaidInFullDate | 80,817 | 23.9790% | 0 | Not applicable |
| sba-7a-fy1991_fy1999 | ChargeOffDate | 301,780 | 89.5402% | 0 | Not applicable |
| sba-7a-fy1991_fy1999 | GrossApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy1991_fy1999 | GrossChargeOffAmount | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy1991_fy1999 | SBAGuaranteedApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy1991_fy1999 | ApprovalFY | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy1991_fy1999 | TermInMonths | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy1991_fy1999 | JobsSupported | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy1991_fy1999 | InitialInterestRate | 337,033 | 100.0000% | 0 | 0 |
| sba-7a-fy2000_fy2009 | AsOfDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy2000_fy2009 | ApprovalDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy2000_fy2009 | FirstDisbursementDate | 83,556 | 12.1037% | 0 | Not applicable |
| sba-7a-fy2000_fy2009 | PaidInFullDate | 230,111 | 33.3333% | 0 | Not applicable |
| sba-7a-fy2000_fy2009 | ChargeOffDate | 545,987 | 79.0904% | 0 | Not applicable |
| sba-7a-fy2000_fy2009 | GrossApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2000_fy2009 | GrossChargeOffAmount | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2000_fy2009 | SBAGuaranteedApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2000_fy2009 | ApprovalFY | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2000_fy2009 | TermInMonths | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2000_fy2009 | JobsSupported | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2000_fy2009 | InitialInterestRate | 653,700 | 94.6934% | 0 | 0 |
| sba-7a-fy2010_fy2019 | AsOfDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy2010_fy2019 | ApprovalDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy2010_fy2019 | FirstDisbursementDate | 67,051 | 12.2860% | 0 | Not applicable |
| sba-7a-fy2010_fy2019 | PaidInFullDate | 151,030 | 27.6738% | 0 | Not applicable |
| sba-7a-fy2010_fy2019 | ChargeOffDate | 511,608 | 93.7439% | 0 | Not applicable |
| sba-7a-fy2010_fy2019 | GrossApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2010_fy2019 | GrossChargeOffAmount | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2010_fy2019 | SBAGuaranteedApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2010_fy2019 | ApprovalFY | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2010_fy2019 | TermInMonths | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2010_fy2019 | JobsSupported | 2 | 0.0004% | 0 | 0 |
| sba-7a-fy2010_fy2019 | InitialInterestRate | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2020_present | AsOfDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy2020_present | ApprovalDate | 0 | 0.0000% | 0 | Not applicable |
| sba-7a-fy2020_present | FirstDisbursementDate | 71,186 | 18.3309% | 0 | Not applicable |
| sba-7a-fy2020_present | PaidInFullDate | 320,136 | 82.4375% | 0 | Not applicable |
| sba-7a-fy2020_present | ChargeOffDate | 381,450 | 98.2263% | 0 | Not applicable |
| sba-7a-fy2020_present | GrossApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2020_present | GrossChargeOffAmount | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2020_present | SBAGuaranteedApproval | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2020_present | ApprovalFY | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2020_present | TermInMonths | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2020_present | JobsSupported | 0 | 0.0000% | 0 | 0 |
| sba-7a-fy2020_present | InitialInterestRate | 8 | 0.0021% | 0 | 0 |

#### SEC manifest/date integrity — issuer facts grain

| Issuer | Fact entries | Unlinked facts | Manifest date/form mismatch | Filed before end | Available |
| --- | --- | --- | --- | --- | --- |
| AAPL | 25,135 | 0 | 0 | 0 | true |
| MSFT | 32,671 | 0 | 0 | 0 | true |
| F | 24,139 | 0 | 0 | 0 | true |
| GM | 23,496 | 0 | 0 | 0 | true |

### Bước phân tích tiếp theo

Mở cohorts/program/vintage filters; cần matured event/censoring definitions để xây fixed-horizon credit target. SEC financials và UCI bankruptcy là sources riêng.

## 6. P4: Portfolio — exposure anatomy, concentration và movement

2026-03 · USD · region · pinned source observations, not owned positions

### Nhận xét từ dữ liệu

- Largest bucket CA = 20.48%; top five = 40.16%. Đây là region shares trong cùng USD total.
- Reported principal đổi -$13,037,124 (-1.40%) từ 2026-02. Snapshot delta gồm entries/exits/balance movement; không đồng nghĩa realized loss.
- EL vẫn unavailable khi thiếu risk inputs. P2/P4 có source overlap; không cộng balances thành total suite exposure.
- Vùng giảm nhiều nhất: CA -$2,728,148; NY -$691,944; MA -$664,288. Vùng tăng nhiều nhất: không có. Bridge khớp tổng đến cent; đây là đóng góp số học.

### Định nghĩa và actual của từng KPI

#### 1. Reported principal

**Actual:** 915,208,989.12 USD. **Công thức/support:** Σ known source principal.

**Diễn giải:** Không mặc định EAD.

**So sánh 2026-02:** baseline 928,246,113.34 USD; thay đổi tuyệt đối -13,037,124.22 USD; tương đối -1.4045%.

#### 2. Observations

**Actual:** 9,698. **Công thức/support:** Source rows in selected import.

**Diễn giải:** Observation grain; chưa borrower count.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 3. Zero-balance share

**Actual:** 1.4539%. **Công thức/support:** 141 / 9698.

**Diễn giải:** Zero khác missing; không tự là bad debt.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 4. Average positive balance

**Actual:** 95,763.21 USD. **Công thức/support:** Reported principal / nonzero-balance records.

**Diễn giải:** Arithmetic average của observations; không borrower exposure.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 5. Largest region share

**Actual:** 20.4841%. **Công thức/support:** Largest bucket amount / currency total.

**Diễn giải:** CA là largest geographic bucket; không tự là concentration limit breach.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 6. Top-five region share

**Actual:** 40.1578%. **Công thức/support:** Σ top five geographic amount shares.

**Diễn giải:** Tập trung địa lý; không đánh giá entity/group concentration.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 7. Geographic HHI

**Actual:** 0.065459. **Công thức/support:** Σ region amount_share²; scale 0–1.

**Diễn giải:** Mô tả concentration của partition hiện tại; không dùng antitrust thresholds làm credit limit.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 8. Research EL

**Actual:** Unavailable. **Công thức/support:** Requires qualified PD/LGD/EAD contract.

**Diễn giải:** UNAVAILABLE_NO_RISK_INPUTS

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

### Bridge địa lý và đối soát tổng

Σ region (current − prior) = current total − prior total; contribution = region delta / prior total

Grouped snapshot arithmetic; không xác định nguyên nhân hoặc tách entries/exits/shared-loan movements. Bucket vắng trong complete partition có subtotal 0, không gán missing amount thành zero.

Prior 2026-02: 928246113.34 USD; current 2026-03: 915208989.12 USD; delta -13037124.22 USD. Đối soát EXACT_CENTS_PASS bằng integer cents. Contribution dùng prior total để các vùng cộng ra total relative change, không chia cho net delta.

### Tất cả geographic buckets — exact source amounts

| Region | Records | Reported USD exact | Amount share | Research EL exact |
| --- | --- | --- | --- | --- |
| CA | 1,398 | 187472203.58 | 20.4841% | Unavailable |
| NY | 496 | 54316633.65 | 5.9349% | Unavailable |
| IL | 559 | 45746267.55 | 4.9985% | Unavailable |
| FL | 449 | 40518870.83 | 4.4273% | Unavailable |
| VA | 340 | 39473869.78 | 4.3131% | Unavailable |
| MA | 317 | 38582961.08 | 4.2158% | Unavailable |
| MD | 261 | 35209761.06 | 3.8472% | Unavailable |
| NJ | 306 | 33805851.23 | 3.6938% | Unavailable |
| PA | 383 | 29648797.23 | 3.2396% | Unavailable |
| TX | 391 | 29493612.08 | 3.2226% | Unavailable |
| MI | 413 | 25229001.98 | 2.7566% | Unavailable |
| WA | 224 | 24759002.23 | 2.7053% | Unavailable |
| NC | 290 | 23841847.50 | 2.6051% | Unavailable |
| MN | 297 | 23261729.93 | 2.5417% | Unavailable |
| OH | 401 | 22795689.87 | 2.4908% | Unavailable |
| GA | 246 | 20051938.69 | 2.1910% | Unavailable |
| AZ | 219 | 19071160.17 | 2.0838% | Unavailable |
| WI | 255 | 17957671.65 | 1.9621% | Unavailable |
| MO | 234 | 16531242.44 | 1.8063% | Unavailable |
| CT | 156 | 15071267.83 | 1.6468% | Unavailable |
| CO | 141 | 14370673.70 | 1.5702% | Unavailable |
| IN | 220 | 13112189.51 | 1.4327% | Unavailable |
| OR | 117 | 11269954.58 | 1.2314% | Unavailable |
| KY | 158 | 11057785.34 | 1.2082% | Unavailable |
| HI | 48 | 10506048.75 | 1.1479% | Unavailable |
| TN | 125 | 8866510.05 | 0.9688% | Unavailable |
| SC | 102 | 8584628.02 | 0.9380% | Unavailable |
| UT | 76 | 8508562.07 | 0.9297% | Unavailable |
| NH | 79 | 8279484.88 | 0.9047% | Unavailable |
| AL | 88 | 6480119.91 | 0.7080% | Unavailable |
| LA | 76 | 6048508.32 | 0.6609% | Unavailable |
| IA | 88 | 5673153.88 | 0.6199% | Unavailable |
| NV | 71 | 5505861.93 | 0.6016% | Unavailable |
| KS | 83 | 5220546.87 | 0.5704% | Unavailable |
| ME | 52 | 4509047.55 | 0.4927% | Unavailable |
| NM | 47 | 3946994.12 | 0.4313% | Unavailable |
| DE | 32 | 3655569.57 | 0.3994% | Unavailable |
| DC | 25 | 3614876.24 | 0.3950% | Unavailable |
| RI | 41 | 3595479.18 | 0.3929% | Unavailable |
| OK | 55 | 3582843.39 | 0.3915% | Unavailable |
| AR | 50 | 3580216.92 | 0.3912% | Unavailable |
| ID | 49 | 3499813.39 | 0.3824% | Unavailable |
| VT | 43 | 3336263.70 | 0.3645% | Unavailable |
| NE | 43 | 2581645.95 | 0.2821% | Unavailable |
| MT | 21 | 2202633.60 | 0.2407% | Unavailable |
| WV | 26 | 2162307.05 | 0.2363% | Unavailable |
| AK | 19 | 2012252.51 | 0.2199% | Unavailable |
| MS | 24 | 1732979.67 | 0.1894% | Unavailable |
| ND | 20 | 1487497.64 | 0.1625% | Unavailable |
| SD | 17 | 950568.91 | 0.1039% | Unavailable |
| PR | 11 | 925715.42 | 0.1011% | Unavailable |
| WY | 9 | 901715.21 | 0.0985% | Unavailable |
| GU | 7 | 607160.93 | 0.0663% | Unavailable |

### Phân rã biến động theo vùng — exact-cent bridge

| Region | Prior USD exact | Current USD exact | Delta USD exact | Contribution pp of prior total | Prior records | Current records | Presence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CA | 190200351.54 | 187472203.58 | -2728147.96 | -0.293904 | 1,409 | 1,398 | Both snapshots |
| NY | 55008577.80 | 54316633.65 | -691944.15 | -0.074543 | 502 | 496 | Both snapshots |
| MA | 39247248.77 | 38582961.08 | -664287.69 | -0.071564 | 317 | 317 | Both snapshots |
| VA | 40135502.54 | 39473869.78 | -661632.76 | -0.071278 | 345 | 340 | Both snapshots |
| FL | 41090936.14 | 40518870.83 | -572065.31 | -0.061629 | 459 | 449 | Both snapshots |
| MI | 25731053.29 | 25229001.98 | -502051.31 | -0.054086 | 416 | 413 | Both snapshots |
| MD | 35707745.87 | 35209761.06 | -497984.81 | -0.053648 | 266 | 261 | Both snapshots |
| TX | 29952967.29 | 29493612.08 | -459355.21 | -0.049486 | 396 | 391 | Both snapshots |
| PA | 30105511.99 | 29648797.23 | -456714.76 | -0.049202 | 389 | 383 | Both snapshots |
| IL | 46190646.09 | 45746267.55 | -444378.54 | -0.047873 | 568 | 559 | Both snapshots |
| NC | 24235098.00 | 23841847.50 | -393250.50 | -0.042365 | 291 | 290 | Both snapshots |
| MN | 23639508.20 | 23261729.93 | -377778.27 | -0.040698 | 300 | 297 | Both snapshots |
| KY | 11424842.21 | 11057785.34 | -367056.87 | -0.039543 | 159 | 158 | Both snapshots |
| NJ | 34148704.83 | 33805851.23 | -342853.60 | -0.036936 | 310 | 306 | Both snapshots |
| MO | 16861128.48 | 16531242.44 | -329886.04 | -0.035539 | 236 | 234 | Both snapshots |
| AZ | 19396179.29 | 19071160.17 | -325019.12 | -0.035014 | 222 | 219 | Both snapshots |
| OH | 23073903.11 | 22795689.87 | -278213.24 | -0.029972 | 404 | 401 | Both snapshots |
| WI | 18200624.65 | 17957671.65 | -242953.00 | -0.026173 | 255 | 255 | Both snapshots |
| WA | 24993972.33 | 24759002.23 | -234970.10 | -0.025313 | 227 | 224 | Both snapshots |
| NE | 2798059.65 | 2581645.95 | -216413.70 | -0.023314 | 43 | 43 | Both snapshots |
| GA | 20247418.38 | 20051938.69 | -195479.69 | -0.021059 | 253 | 246 | Both snapshots |
| ID | 3674521.37 | 3499813.39 | -174707.98 | -0.018821 | 49 | 49 | Both snapshots |
| IN | 13281437.70 | 13112189.51 | -169248.19 | -0.018233 | 221 | 220 | Both snapshots |
| SC | 8739711.93 | 8584628.02 | -155083.91 | -0.016707 | 103 | 102 | Both snapshots |
| CT | 15220941.80 | 15071267.83 | -149673.97 | -0.016124 | 159 | 156 | Both snapshots |
| SD | 1092426.67 | 950568.91 | -141857.76 | -0.015282 | 17 | 17 | Both snapshots |
| IA | 5787957.55 | 5673153.88 | -114803.67 | -0.012368 | 91 | 88 | Both snapshots |
| LA | 6159313.55 | 6048508.32 | -110805.23 | -0.011937 | 76 | 76 | Both snapshots |
| AL | 6590849.41 | 6480119.91 | -110729.50 | -0.011929 | 88 | 88 | Both snapshots |
| CO | 14472320.21 | 14370673.70 | -101646.51 | -0.010950 | 145 | 141 | Both snapshots |
| OR | 11352514.91 | 11269954.58 | -82560.33 | -0.008894 | 118 | 117 | Both snapshots |
| TN | 8934889.54 | 8866510.05 | -68379.49 | -0.007367 | 125 | 125 | Both snapshots |
| NH | 8340981.13 | 8279484.88 | -61496.25 | -0.006625 | 79 | 79 | Both snapshots |
| HI | 10565143.20 | 10506048.75 | -59094.45 | -0.006366 | 48 | 48 | Both snapshots |
| UT | 8567303.07 | 8508562.07 | -58741.00 | -0.006328 | 77 | 76 | Both snapshots |
| KS | 5276075.32 | 5220546.87 | -55528.45 | -0.005982 | 84 | 83 | Both snapshots |
| NM | 3998475.39 | 3946994.12 | -51481.27 | -0.005546 | 47 | 47 | Both snapshots |
| NV | 5555875.75 | 5505861.93 | -50013.82 | -0.005388 | 71 | 71 | Both snapshots |
| ME | 4549346.60 | 4509047.55 | -40299.05 | -0.004341 | 53 | 52 | Both snapshots |
| DC | 3655090.15 | 3614876.24 | -40213.91 | -0.004332 | 25 | 25 | Both snapshots |
| RI | 3634806.84 | 3595479.18 | -39327.66 | -0.004237 | 41 | 41 | Both snapshots |
| AR | 3610557.75 | 3580216.92 | -30340.83 | -0.003269 | 52 | 50 | Both snapshots |
| OK | 3611811.35 | 3582843.39 | -28967.96 | -0.003121 | 55 | 55 | Both snapshots |
| DE | 3683743.84 | 3655569.57 | -28174.27 | -0.003035 | 32 | 32 | Both snapshots |
| VT | 3363826.60 | 3336263.70 | -27562.90 | -0.002969 | 43 | 43 | Both snapshots |
| ND | 1509440.60 | 1487497.64 | -21942.96 | -0.002364 | 20 | 20 | Both snapshots |
| AK | 2033828.31 | 2012252.51 | -21575.80 | -0.002324 | 20 | 19 | Both snapshots |
| MS | 1749420.94 | 1732979.67 | -16441.27 | -0.001771 | 24 | 24 | Both snapshots |
| WV | 2176714.57 | 2162307.05 | -14407.52 | -0.001552 | 26 | 26 | Both snapshots |
| MT | 2216614.40 | 2202633.60 | -13980.80 | -0.001506 | 21 | 21 | Both snapshots |
| WY | 907338.41 | 901715.21 | -5623.20 | -0.000606 | 9 | 9 | Both snapshots |
| GU | 612757.76 | 607160.93 | -5596.83 | -0.000603 | 7 | 7 | Both snapshots |
| PR | 930096.27 | 925715.42 | -4380.85 | -0.000472 | 11 | 11 | Both snapshots |

### Chất lượng dữ liệu và phạm vi kiểm tra

exposure-import-57b88e00bedb · 2026-03 · USD/region partition

| Control/KPI | Actual | Formula/support | Diễn giải |
| --- | --- | --- | --- |
| Region record coverage | 100.0000% | 9698 bucket records / 9698 | Partition count reconciliation; không borrower linkage coverage. |
| Source zero-balance share | 1.4539% | 141 / 9698 | Zero là source balance; không missing hoặc bad-debt status. |
| Missing amount share | Unavailable | Requires import-level missing amount profile | Không suy từ zero balances; monitor payload chưa có missing profile. |

- Không cộng currencies hoặc source-overlapping P2/P4. Ownership, EAD/risk qualification không được chứng nhận chỉ vì partition khớp.

#### Portfolio interpretation contract

| Control | Source declaration |
| --- | --- |
| fx_conversion_performed | false |
| borrower_identity_linkage | false |
| ownership_certified | false |
| overlap_identity_certified | false |
| production_pd_qualified | false |
| accounting_ecl | false |
| regulatory_irb | false |
| amount_is_ead | false |
| el_formula | Declared performing point assumptions: cumulative PD × conditional LGD × explicitly declared EAD |
| pool_guard | Exact declared pool keys only; representation conflicts rejected, unknown real-world links not certified |
| concentration_grain | Position/observation segments, not obligor concentration; no borrower identity available |

### Bước phân tích tiếp theo

Mở movement bridge để reconcile entries/exits/shared records, rồi đọc assumptions của scenario/ECL/tail riêng.

### Baseline control

| Field | Value |
| --- | --- |
| requested | auto |
| current_period | 2026-03 |
| resolved_period | 2026-02 |
| status | EXACT_PREVIOUS_CALENDAR_MONTH |
| rule | Auto chỉ lấy đúng tháng lịch trước; manual dùng exact prior period. Không fallback nearest; baseline không áp lifetime/quality/cash-replay scope. |

Baseline chính chỉ áp các delta/decomposition tương ứng, không thay current actual. Chọn manual prior period hoặc tắt baseline trong app; không fallback nearest khi không có exact period. P2 YoY cùng tháng là comparison riêng, overview chart giữ monthly delta; lifetime transitions, data-quality controls và selected cash replay có scopes riêng.

## 7. P5: Structured — cashflow, tranches và source reconciliation

World Omni Auto Receivables Trust 2025-A · collection 2026-08-31 / payment 2026-09-15 · conditional historical replay

### Nhận xét từ dữ liệu

- Latest pool $541,026,330, notes $534,899,521, descriptive surplus $6,126,809. Không tự phân loại OC breach bằng balance difference.
- Principal paid kỳ này $22,705,783; reserve draw $0. Đọc waterfall sequence và tranche allocations cùng collection/payment dates.
- 0 failed / 720 source checks; legal/full-contract qualification vẫn có điều kiện.
- Cash bridge EXACT_CENTS_PASS: 28848358.63 − 28848358.63 = 0.00 USD. Reserve reconciliation 0.00 USD; regime PRE_ACCELERATION, basis CONDITIONAL_REPORTED_REPLAY.

### Định nghĩa và actual của từng KPI

#### 1. Adjusted pool

**Actual:** 541,026,329.81 USD. **Công thức/support:** Reported ending pool.

**Diễn giải:** Không full collateral valuation.

**So sánh 2026-07-31:** baseline 563,732,112.49 USD; thay đổi tuyệt đối -22,705,782.68 USD; tương đối -4.0278%.

#### 2. Ending notes

**Actual:** 534,899,521.27 USD. **Công thức/support:** Σ seven ending tranche balances.

**Diễn giải:** Not equity or total deal enterprise value.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 3. Adjusted pool surplus

**Actual:** 6,126,808.54 USD. **Công thức/support:** Adjusted pool − note balances.

**Diễn giải:** Descriptive balance difference; không chứng nhận contractual OC trigger.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 4. Available funds

**Actual:** 28,848,358.63 USD. **Công thức/support:** Reported funds in period.

**Diễn giải:** Không income/profit hoặc forward forecast.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 5. Principal paid this period

**Actual:** 22,705,782.68 USD. **Công thức/support:** Σ tranche principal_paid.

**Diễn giải:** Actual reported/replayed allocation; phân biệt beginning/ending balances.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 6. Reserve ending

**Actual:** 3,063,404.27 USD. **Công thức/support:** Reported reserve ending.

**Diễn giải:** Đọc legal reserve rules trước compliance inference.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 7. Reserve draw

**Actual:** 0.00 USD. **Công thức/support:** Σ reserve draws in period.

**Diễn giải:** Zero không chứng minh deal risk-free.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 8. Pool runoff vs first reported period

**Actual:** 54.5131%. **Công thức/support:** 1 − latest adjusted pool / first reported adjusted pool.

**Diễn giải:** Không dùng first reported pool làm initial issuance face.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 9. Failed source checks

**Actual:** 0. **Công thức/support:** Failed checks / 720 checks.

**Diễn giải:** All checks passing không xác nhận legal-regime completeness.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 10. Replay interest paid

**Actual:** 2,225,029.41 USD. **Công thức/support:** Σ tranche interest_paid.

**Diễn giải:** Conditional replay; đọc reported source checks và carryover assumptions.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 11. Replay certificate distribution

**Actual:** 3,917,546.54 USD. **Công thức/support:** Reported-replay residual paid to certificate.

**Diễn giải:** Cash allocation; không profit/yield hoặc chứng minh distributions đầy đủ legal terms.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 12. Replay closing available cash

**Actual:** 0.00 USD. **Công thức/support:** Last ledger cash_after.

**Diễn giải:** Zero là allocated cash; không đánh giá liquidity adequacy.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 13. Replay reserve deposit

**Actual:** 0.00 USD. **Công thức/support:** Result reserve_deposit.

**Diễn giải:** Internal reserve funding, không external tranche payout.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 14. Replay unpaid interest

**Actual:** 0.00 USD. **Công thức/support:** Σ tranche interest_unpaid.

**Diễn giải:** Không cộng overlapping priority shortfalls thành realized credit loss.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 15. Replay reviewer fee unpaid

**Actual:** 0.00 USD. **Công thức/support:** Result reviewer_fee_unpaid.

**Diễn giải:** Giữ obligation input assumptions; không suy default legal event.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 16. Cash ledger residual

**Actual:** 0.00 USD. **Công thức/support:** Opening available funds − Σ from_available_funds − closing cash.

**Diễn giải:** Đối soát integer cents; zero không chứng nhận full contractual waterfall.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

#### 17. Reserve ledger residual

**Actual:** 0.00 USD. **Công thức/support:** Opening reserve + Σ credits − Σ draws − ending reserve.

**Diễn giải:** Đối soát reserve ledger của selected replay; không interest-income bridge.

**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline.

### Selected-period cash/reserve bridge

Collection 2026-08-31, payment 2026-09-15, regime PRE_ACCELERATION, basis CONDITIONAL_REPORTED_REPLAY. Reconciliation: EXACT_CENTS_PASS.

Cash: opening available funds − sum(from_available_funds) − ending cash = 0. Reserve: opening + credits − draws − ending = 0. Từng bước đối soát bằng integer cents; nguồn available funds đã net servicing. Reserve replenishment là internal transfer, không cộng như external distribution. Shortfalls ở các priority có thể overlap, không cộng thành loss.

| Step | Cash residual USD exact | Reserve residual USD exact |
| --- | --- | --- |
| 1 | 0.00 | 0.00 |
| 2 | 0.00 | 0.00 |
| 3 | 0.00 | 0.00 |
| 4 | 0.00 | 0.00 |
| 5 | 0.00 | 0.00 |
| 6 | 0.00 | 0.00 |
| 7 | 0.00 | 0.00 |
| 8 | 0.00 | 0.00 |
| 9 | 0.00 | 0.00 |
| 10 | 0.00 | 0.00 |
| 11 | 0.00 | 0.00 |

### Tranche allocations — selected latest period

| Tranche | Ending USD exact | Principal paid USD exact |
| --- | --- | --- |
| A-1 | 0.00 | 0.00 |
| A-2a | 0.00 | 0.00 |
| A-2b | 0.00 | 0.00 |
| A-3 | 390459521.27 | 22705782.68 |
| A-4 | 89300000.00 | 0.00 |
| B | 36760000.00 | 0.00 |
| C | 18380000.00 | 0.00 |

### Reported history — exact values

| Collection end | Payment date | Adjusted pool USD | Available funds USD | Reserve USD | Reserve draw USD |
| --- | --- | --- | --- | --- | --- |
| 2025-01-31 | 2025-02-18 | 1189412104.78 | 44964910.32 | 3063404.27 | 0.00 |
| 2025-02-28 | 2025-03-17 | 1150810145.54 | 47840543.85 | 3063404.27 | 0.00 |
| 2025-03-31 | 2025-04-15 | 1110149142.80 | 49556348.54 | 3063404.27 | 0.00 |
| 2025-04-30 | 2025-05-15 | 1069530243.52 | 48966964.79 | 3063404.27 | 0.00 |
| 2025-05-31 | 2025-06-16 | 1029897980.13 | 47202624.27 | 3063404.27 | 0.00 |
| 2025-06-30 | 2025-07-15 | 989420411.50 | 48252980.83 | 3063404.27 | 0.00 |
| 2025-07-31 | 2025-08-15 | 949557920.09 | 47301065.93 | 3063404.27 | 0.00 |
| 2025-08-31 | 2025-09-15 | 912474057.95 | 44207546.28 | 3063404.27 | 0.00 |
| 2025-09-30 | 2025-10-15 | 875493942.73 | 43646260.50 | 3063404.27 | 0.00 |
| 2025-10-31 | 2025-11-17 | 839224370.24 | 42861004.28 | 3063404.27 | 0.00 |
| 2025-11-30 | 2025-12-15 | 807824313.56 | 36971016.82 | 3063404.27 | 0.00 |
| 2025-12-31 | 2026-01-15 | 773169331.21 | 40728365.07 | 3063404.27 | 0.00 |
| 2026-01-31 | 2026-02-17 | 741388514.17 | 37236490.84 | 3063404.27 | 0.00 |
| 2026-02-28 | 2026-03-16 | 710603223.88 | 35699395.23 | 3063404.27 | 0.00 |
| 2026-03-31 | 2026-04-15 | 678979362.88 | 36657145.84 | 3063404.27 | 0.00 |
| 2026-04-30 | 2026-05-15 | 648400035.65 | 35569692.30 | 3063404.27 | 0.00 |
| 2026-05-31 | 2026-06-15 | 619341746.94 | 33876155.92 | 3063404.27 | 0.00 |
| 2026-06-30 | 2026-07-15 | 590574193.80 | 33836611.56 | 3063404.27 | 0.00 |
| 2026-07-31 | 2026-08-17 | 563732112.49 | 31221932.82 | 3063404.27 | 0.00 |
| 2026-08-31 | 2026-09-15 | 541026329.81 | 28848358.63 | 3063404.27 | 0.00 |

### Selected cash ledger — all priorities, exact USD

| Step | Name | Due | Paid | Shortfall | From available funds | Reserve draw | Reserve credit | Cash before | Cash after | Reserve before | Reserve after | External distribution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | reviewer_within_annual_cap | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 28848358.63 | 28848358.63 | 3063404.27 | 3063404.27 | true |
| 2 | class_a_interest | 1990224.91 | 1990224.91 | 0.00 | 1990224.91 | 0.00 | 0.00 | 28848358.63 | 26858133.72 | 3063404.27 | 3063404.27 | true |
| 3 | first_priority_principal | 0 | 0 | 0 | 0 | 0 | 0.00 | 26858133.72 | 26858133.72 | 3063404.27 | 3063404.27 | true |
| 4 | class_b_interest | 155617.33 | 155617.33 | 0.00 | 155617.33 | 0.00 | 0.00 | 26858133.72 | 26702516.39 | 3063404.27 | 3063404.27 | true |
| 5 | second_priority_principal | 0 | 0 | 0 | 0 | 0 | 0.00 | 26702516.39 | 26702516.39 | 3063404.27 | 3063404.27 | true |
| 6 | class_c_interest | 79187.17 | 79187.17 | 0.00 | 79187.17 | 0.00 | 0.00 | 26702516.39 | 26623329.22 | 3063404.27 | 3063404.27 | true |
| 7 | third_priority_principal | 16578974.14 | 16578974.14 | 0.00 | 16578974.14 | 0.00 | 0.00 | 26623329.22 | 10044355.08 | 3063404.27 | 3063404.27 | true |
| 8 | reserve_replenishment | 0 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | 10044355.08 | 10044355.08 | 3063404.27 | 3063404.27 | false |
| 9 | regular_principal | 6126808.54 | 6126808.54 | 0.00 | 6126808.54 | 0.00 | 0.00 | 10044355.08 | 3917546.54 | 3063404.27 | 3063404.27 | true |
| 10 | remaining_reviewer_fee | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 3917546.54 | 3917546.54 | 3063404.27 | 3063404.27 | true |
| 11 | certificate_residual | 3917546.54 | 3917546.54 | 0.00 | 3917546.54 | 0.00 | 0.00 | 3917546.54 | 0.00 | 3063404.27 | 3063404.27 | true |

### Cash and reserve bridge — independent exact-cent residuals

| Component | Exact USD |
| --- | --- |
| available_funds_exact | 28848358.63 |
| funds_used_exact | 28848358.63 |
| cash_ending_exact | 0.00 |
| cash_residual_exact | 0.00 |
| reserve_beginning_exact | 3063404.27 |
| reserve_credit_exact | 0.00 |
| reserve_draw_exact | 0.00 |
| reserve_ending_exact | 3063404.27 |
| reserve_residual_exact | 0.00 |

### Chất lượng dữ liệu và phạm vi kiểm tra

Source checks across all reported periods; cash/reserve residual controls cho latest selected period riêng

| Control/KPI | Actual | Formula/support | Diễn giải |
| --- | --- | --- | --- |
| Failed source-check share | 0.0000% | 0 failed / 720 checks | Check count không là record error rate hoặc legal certification. |
| Verified cash/reserve ledger steps | 11 | Count steps with both exact residuals zero | Đọc sequence/total reconciliation riêng; không full contractual qualification. |

- Historical replay có conditional assumptions; source reconciliation không xác nhận tất cả obligations/agreements hoặc forward collateral projection.

#### ABS qualification declarations

| Qualification | Value |
| --- | --- |
| full_contractual_waterfall | false |
| legal_regime_certified | false |
| obligation_completeness_certified | false |
| realized_loss_model | false |

### Bước phân tích tiếp theo

Mở waterfall/terms/source checks. Projection/pricing cần collateral forecasts và verified full legal rules.

### Baseline control

| Field | Value |
| --- | --- |
| requested | auto |
| current_period | 2026-08-31 |
| resolved_period | 2026-07-31 |
| status | EXACT_PREVIOUS_CALENDAR_MONTH |
| rule | Auto chỉ lấy đúng tháng lịch trước; manual dùng exact prior period. Không fallback nearest; baseline không áp lifetime/quality/cash-replay scope. |

Baseline chính chỉ áp các delta/decomposition tương ứng, không thay current actual. Chọn manual prior period hoặc tắt baseline trong app; không fallback nearest khi không có exact period. P2 YoY cùng tháng là comparison riêng, overview chart giữ monthly delta; lifetime transitions, data-quality controls và selected cash replay có scopes riêng.

## 8. Các KPI bổ sung và dữ liệu cần thiết

| Domain | KPI/workflow | Cần gì và trạng thái |
| --- | --- | --- |
| P1 | Approval/reject rate; profit; drift/OOT | Decisioned applications gồm rejected population, timestamps, prices/costs/capacity và mature outcomes. UCI booked cohort không đủ; policy preview theo declared costs đã có, chưa actual realized profit. |
| P2 | PD12, LGD, EL; cure/migration | Target/horizon, temporal vintages, censoring và qualified EAD/loss definition. Loss gate đang blocked do support/coverage. Transition/lifecycle workflow đã có riêng; stock change không thay transition. |
| P3 | DSCR, ICR, leverage, covenant; bankruptcy | Filing-specific financials, ratio conventions, debt service và legal covenant terms. SEC và UCI365 là workflows riêng; không tự join với SBA borrowers hoặc gán benchmark PD cho issuer. |
| P4 | Qualified EAD/PD/LGD/EL; ECL; VaR/ES | Institution exposure/risk inputs, SICR/staging, scenario weights, cashflow losses/discounting và dependence assumptions. Scenario/ECL/tail engines có study có điều kiện; geographic HHI không thay economic capital. |
| P5 | Forward cashflows, valuation, OC/IC, DV01 | Collateral forecasts, full verified legal waterfall/trigger rules, instrument cashflows và discount/credit curves. Reported replay không thay forward pricing; Bond scenario workspace dùng assumptions riêng. |

Các mục này cũng xuất hiện dưới từng domain trong app tại **Các KPI cần dữ liệu / workflow bổ sung**. Danh mục 88 dòng là bộ KPI đọc trực tiếp từ các snapshot hiện có, không phải toàn bộ chỉ số cần cho mọi loại hình tổ chức tín dụng.

## 9. Kiểm chứng và cách dùng

KPI QA mới: 19 checks PASS, 88 rendered KPI rows, 22 quality controls independently reconciled, independent arithmetic checks (D3/decomposition/loss, calibration gap, HHI/movement, SBA denominators, ABS surplus), từng vùng/tổng đối soát Decimal, bridge scope/zero/missing/inconsistent-total safeguards, lifetime transition row sums/rates và confirmed follow-up denominators, validation policy action/cost/capacity reconciliation và unavailable-policy safeguards, issuer ratio/period/unit checks và single-issuer outage safeguards, all-step ABS cash/reserve reconciliation và selected-ledger outage, exact/manual/disabled baseline controls, no-nearest fallback, filters/export/reload, mobile 390px và browser exceptions. Monitor regression trước bridge: 10 checks PASS. Không refit/rescore frozen holdout; access ledger giữ nguyên.

Receipts: `artifacts/private/kpi-analysis-qa-cb670b239571/receipt.json` và `artifacts/private/monitor-qa-a6dbe5387a8b/receipt.json`. Export nguồn cho tài liệu: `artifacts/private/kpi-analysis-qa-cb670b239571/analysis-all.json`. Tài liệu được tạo bằng `scripts/build_kpi_analysis_guide.py`.

Khi đọc một biến động: xác nhận nguồn/kỳ/grain → xem support và missingness → đọc actual + baseline → phân rã theo nhóm hoặc bridge → mở workflow nghiệp vụ → ghi nhận định trong review cùng evidence. Giả thuyết nguyên nhân phải được kiểm chứng bằng dữ liệu liên quan; không coi decomposition số học là bằng chứng nhân quả.

Liên quan: [KPI analyst review](KPI_ANALYST_REVIEW_WORKFLOW_VI.md), [Hướng dẫn workbench](WORKBENCH_USER_GUIDE_VI.md), [50 chức năng và kế hoạch](PLAN_WORKBENCH_DETAIL.md), [Trạng thái năm workspace](FIVE_WORKSPACES_STATUS.md).
