# P4 — Tail risk, dependence và recovery sensitivity

## 1. Câu hỏi module này trả lời

Hai danh mục có cùng PD × LGD × EAD kỳ vọng vẫn có thể có tail loss rất khác
nhau nếu default xảy ra cùng lúc. Module này mô phỏng phân phối tổn thất trên
từng position, so sánh dependence/recovery, tính VaR, Expected Shortfall (ES)
và đóng góp của segment vào cùng portfolio tail.

Đây là **declared research simulation**. PD, LGD, EAD, correlation, recovery
coupling và định nghĩa default là assumptions khai báo, chưa được hiệu chỉnh
từ observed defaults/recoveries. Module chưa qualified regulatory capital,
accounting ECL hoặc dự báo tổn thất thực tế. Source EL tiếp tục unavailable.

Mô hình Gaussian một factor có nền tảng lý thuyết trong
[BIS: IRB risk-weight functions](https://www.bis.org/bcbs/irbriskweight.pdf).
Implementation ở đây mô phỏng danh mục hữu hạn, dùng assumptions minh họa;
không triển khai một IRB capital calculation hay tuyên bố Basel compliance.

## 2. Source và đầu vào

- Snapshot March 2026: `exposure-import-57b88e00bedb`, tổng 9.698 observations.
- Pinned scenario set: `exposure-scenario-9655e30419ec`, chọn case `adverse`.
- Chỉ 9.602 CURRENT positions đủ điều kiện; 96 records ngoài phạm vi.
- Số dư đủ điều kiện: USD 906.367.109,80. EAD factor adverse 1,1 làm
  declared EAD thành USD 997.003.820,78. UPB không tự động là observed EAD.
- Segment non_relief: base PD 0,01, LGD 0,25; relief: PD 0,02, LGD 0,35.
  Adverse dùng PD odds ×3, LGD +0,15, EAD ×1,1; horizon 12 tháng.
- Default definition của scenario được giữ trong report; target 90+ delinquency
  giả định chưa phải validated regulatory-default mapping.

File input: `data/private/exposure-tail-plan-20261009.json`.
Schema exact keys, private visibility và public_release_approved=false.
Một plan phải chỉ rõ scenario_set_id/case, seed, draws, alphas và sensitivity
cases. Correlation 0–0,95; LGD systemic spread 0–1; levels 0,5–0,999.
Draws 128–65.536; tối đa 8 cases/4 levels. Work bound: eligible positions ×
draws × cases ≤300 triệu. Không tự ý downsample để vượt qua giới hạn.

## 3. Công thức và ý nghĩa

Với từng position i, PD adverse là `p*m/(1-p+p*m)`; LGD base của simulation
là `clip(LGD + scenario addition,0,1)`; EAD lấy source amount exact nhân các
factor khai báo. Nhận dạng source được dùng để sắp xếp positions ổn định.

Mỗi draw sinh common factor Z và independent position noise epsilon_i:

    A_i = sqrt(rho)*Z + sqrt(1-rho)*epsilon_i
    D_i = 1[A_i <= Phi^-1(PD_i)]
    LGD_s(Z) = clip(base_LGD_s + spread*(2*Phi(-Z)-1),0,1)
    L = sum_i D_i * EAD_i * LGD_segment(i)(Z)

Z xấu làm nhiều defaults và tăng LGD khi spread>0. rho đo correlation của
latent asset factor, **không phải correlation của binary default indicator**.
Position noise độc lập có điều kiện là giả định; chưa có borrower linkage
để gộp các observations thuộc cùng obligor.

Constant LGD có analytical expectation Σ PD_i × LGD_i × EAD_i, không đổi
theo rho. Khi coupling LGD, expectation được tích phân theo Z cùng conditional
default probability. Vì vậy không dùng constant-LGD reference để kết luận
Monte Carlo bị bias trong case coupled recovery.

Simulation uses float64. Exact source EAD numerator/denominator được lưu;
report công bố maximum absolute per-position conversion error. EAD source
và assumptions vẫn được xử lý bằng Fraction trước khi chuyển sang float.

## 4. Seed và tái lập

PCG64; hai stream độc lập cho factor và idiosyncratic noise trên mỗi currency.
Seed của stream là 16 bytes đầu SHA256 của `seed:currency:tag`, big-endian.
Factor draws sinh một lần. Position noise sinh batch cố định 128, theo
position_id đã sort. Các sensitivity cases cùng currency dùng **common random
numbers**, giúp so sánh rõ hơn; reorder cases không đổi kết quả từng case.
Các currencies có streams riêng và giữ native units, không joint FX total.

Receipt pin source import, upstream lineage, factorized scenario assumptions,
report/receipt, method hashes, NumPy/SciPy versions và RNG convention.
Sau tính toán và sau verification đều kiểm lại input hashes để phát hiện
nguồn bị thay đổi trong lúc chạy. Chỉ receipt hoàn tất mới được catalog.

## 5. VaR, ES và uncertainty

VaR alpha dùng order statistic rank `ceil(alpha*N)` của empirical loss CDF.
ES tích phân chính xác phần probability mass `(1-alpha)*N` lớn nhất; phần
draw cuối được dùng trọng số lẻ. Nếu các draw ở ranh giới đồng hạng, trọng
số còn lại được chia đều cho tất cả ties. Điều này tránh chọn segment
contribution tùy ý theo thứ tự record. ES contributions dùng cùng joint
portfolio tail và cộng lại bằng portfolio ES, trong floating tolerance.

Output ghi tail mass, full tail draws, boundary fraction, strict/tied counts,
tie weight và VaR rank. N=4.096 chỉ cho **40,96 effective draws ở tail 99%**;
không coi ES là ước lượng có precision cao vì in thêm nhiều chữ số.

Mean standard error = sample SD / sqrt(N). Khoảng mean ±1,96 SE là normal
approximation. VaR interval dùng binomial order-statistic ranks; nếu upper
rank vượt N, upper endpoint là null/Unavailable, không dùng maximum loss
làm upper bound. Các intervals mô tả Monte Carlo sampling uncertainty khi
assumptions cố định; không bao gồm calibration/model/data uncertainty.
Chưa có ES confidence interval, bootstrap/convergence study nhiều seeds.

## 6. Actual run đã lưu

Receipt: `exposure-tail-10a079f18dc9`, version illustrative-tail-v1-20261009.
Seed 20261009, N=4.096, levels 97,5% và 99%; work 157.319.168 position draws.

| Case | rho | LGD spread | MC mean USD | Analytic mean USD | VaR 99% USD | ES 99% USD |
|---|---:|---:|---:|---:|---:|---:|
| Independent | 0 | 0 | 17.322.683,22 | 17.313.511,80 | 19.948.065,52 | 20.251.726,31 |
| Correlation 0,15 | 0,15 | 0 | 17.328.554,58 | 17.313.511,80 | 75.811.664,12 | 93.177.643,79 |
| Correlation 0,35 | 0,35 | 0 | 17.184.474,93 | 17.313.511,80 | 137.664.509,66 | 176.304.790,16 |
| Coupled LGD | 0,35 | 0,10 | 19.710.742,58 | 19.892.033,66 | 168.072.005,52 | 215.933.346,47 |

Những chênh lệch này minh họa dependence và wrong-way recovery assumptions;
không chứng minh danh mục thật có rho 0,35 hoặc tail losses trên.

Private payloads: assumptions.json, report.json, total-draws.parquet,
segment-draws.parquet và tail-complete.json. Không lưu per-position default
draws, không API raw Parquet, không phát hành public.

## 7. Verification, independent audit và app

`verify` mặc định chạy lại toàn bộ simulation và đối chiếu exact report,
schema/all rows của hai Parquets, nguồn và method pins. Views lần đầu dùng
full replay; mỗi lần đọc cache kiểm hashes của tất cả inputs/payloads/receipt
và trả deep copy. Đổi runtime/method yêu cầu restart, không silently reseal.

Independent audit đọc source CSV, tính EAD/concentration bằng Fraction,
đối soát segment-to-total từng draw, ordinals/default counts/bounded losses,
mean/sample SD/histogram/ES contribution và common factor parity. Analytical
mean được kiểm bằng split Gauss-Legendre quadrature thay cho adaptive quad;
ES dùng empirical quantile integral và Python math/statistics độc lập.
Kiểm thử có fault injection ES sai và sửa private draw dù giữ timestamp.

Actual independent audit `exposure-tail-audit-6fe926d3a1ab`: 94.393 checks
PASS. Focused engine/views/API/audit tests: 16 PASS. Full suite: 1.019 PASS
(375 engine +644 application), 181,19 giây. Combined actual exposure browser
`exposure-browser-qa-124c0e921076`: 16 checks PASS, gồm desktop/mobile 390px,
tail support, scoped private export, reload và không JavaScript errors.

API catalog `/api/exposure-tail-studies?source_import_id=...`.
`/api/exposure-tail` và `/api/exposure-tail-report` bắt buộc tail_id và
source_import_id; optional currency. Không có seed/rho edits qua API; sửa
assumptions tạo run mới. Origin/Host loopback, no-store, no raw position IDs.
UI nằm trong exposure workspace, có version selection, concentration,
sensitivity comparison, VaR/ES support và joint segment contributions.
Dimension exposure khác không thay scope của tail portfolio; currency filter
giữ source binding. Tail version selection chưa persist URL.

    .\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_tail.py --assumptions data/private/exposure-tail-plan-20261009.json
    .\.venv\Scripts\python.exe -X utf8 scripts/build_exposure_tail.py --verify exposure-tail-10a079f18dc9
    .\.venv\Scripts\python.exe -X utf8 scripts/audit_exposure_tail.py --tail-id exposure-tail-10a079f18dc9
    .\.venv\Scripts\python.exe -X utf8 scripts/browser_exposure_qa.py
    .\scripts\test.ps1

## 8. Phần tiếp theo

Multi-seed/draw-count convergence; calibrated default dependence và recovery
evidence; obligor/linkage/consolidation contracts; maturity/cash-flow-aware
loss distributions; exposure finance/review/version rationale; actual contract
adapters và accounting qualification vẫn là việc mở. Các module và targets
khác trong plan 5 workspaces/50 capabilities tiếp tục giữ nguyên phạm vi.
