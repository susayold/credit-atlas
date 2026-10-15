# Retail — model đã chốt và kết quả holdout

Ngày chạy: 09/10/2026. Đây là benchmark nghiên cứu credit-card behavioral risk
trên UCI 350, chưa phải model được phê duyệt để quyết định cấp tín dụng.

## 1. Dữ liệu và ý nghĩa target

30.000 khách hàng thẻ tín dụng tại Đài Loan, thông tin lịch sử thanh toán và
hóa đơn tháng 4–9/2005. Target của nguồn là `default payment next month`;
không đồng nhất với default theo Basel, PD 12 tháng hoặc default mortgage.
Nguồn chính thức và attribution: [UCI Default of Credit Card Clients](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients),
Yeh, I.-C., CC BY 4.0. Metadata gốc được giữ cùng raw payload.

Case `retail-case-470bdb40682f` đối chiếu toàn bộ 30.000 client facts và
180.000 history rows với raw CSV: không có dòng khác biệt. Source IDs chỉ
dùng cho đối chiếu và chia tập; không dùng làm predictor.

Chia tập ngẫu nhiên có stratification, client-disjoint và seed cố định:

| Tập | Khách hàng | Target = 1 | Công việc |
|---|---:|---:|---|
| Train | 17.999 | 3.981 | Fit encoder và model |
| Calibration | 4.501 | 996 | Fit sigmoid calibration riêng |
| Validation | 4.499 | 995 | So sánh và lựa chọn model |
| Final test | 3.001 | 664 | Đánh giá model sau khi chốt |

Split không theo thời gian. Chưa biết quan hệ hộ gia đình giữa các source
clients. Các nhãn đã được dùng để stratify/reproduce split; raw canonical
facts có tồn tại trước freeze. Vì vậy đây là holdout được giữ riêng trong
pipeline model, không phải dữ liệu chưa từng tiếp cận ở cấp tổ chức.

## 2. Predictor và model

13 biến tiền tệ numeric và sáu PAY status categorical; 81 cột sau encoding.
Mean/std và category vocabulary học chỉ trên train. Có bucket cho category
chưa gặp. Không dùng ID, target, SEX, EDUCATION, MARRIAGE, AGE làm predictor.
Việc bỏ demographic fields không chứng minh model công bằng.

Ba model development dùng cùng dữ liệu: constant prevalence, logistic và
histogram boosting. Boosting có learning rate 0,05; 120 iterations; tối đa
15 leaves; tối thiểu 50 samples/leaf; L2 = 1; random state 71. Không dùng
early stopping, internal validation hoặc hyperparameter search. Xem đầy đủ
[RETAIL_DEVELOPMENT_RESULTS.md](RETAIL_DEVELOPMENT_RESULTS.md).

## 3. Quyết định từ validation

Bundle chốt: `private evidence omitted from public release`.
Model chọn: **boosting/raw**. Không refit khi freeze; encoder/model/settings
được sao chép đúng bytes từ development artifacts đã kiểm tra.

Rubric được thiết lập **sau khi xem kết quả development** và trước khi đánh
giá final test; không phải thử nghiệm confirmatory được preregister. Brier
là chỉ số chính, log loss hỗ trợ. Boosting được chọn khi cải thiện Brier
ít nhất 0,001; paired bootstrap lower bounds của Brier và log loss > 0;
AUC point degradation không quá 0,005. Fallback là logistic nếu Brier và
log loss tốt hơn constant; nếu không thì constant.

Trên validation, raw boosting cải thiện Brier 0,002411 so với raw logistic;
95% exploratory interval [0,000913; 0,003993]. Cải thiện log loss 0,007848,
interval [0,003063; 0,012823]. AUC và average precision improvement intervals
bao gồm zero. Các intervals có điều kiện trên fitted models và class counts;
không điều chỉnh multiple comparisons hoặc training uncertainty. Chi tiết:
[RETAIL_VALIDATION_UNCERTAINTY.md](RETAIL_VALIDATION_UNCERTAINTY.md).

Calibration chỉ được chọn nếu incremental Brier improvement ít nhất 0,0001
và Brier/log-loss lower bounds đều > 0. Calibration của boosting không đạt
tiêu chí này, nên giữ raw probability. Không lựa chọn theo final-test metrics.

## 4. Đánh giá cuối đã chạy thật

Run: `private evidence omitted from public release`.
Chỉ model đã chốt được score; không fit, tune, thay model hoặc chọn threshold
trên final test. Không chạy lại tất cả model để chọn model thắng trên holdout.

| Chỉ số | Validation | Final test |
|---|---:|---:|
| Khách hàng | 4.499 | 3.001 |
| Target = 1 | 995 | 664 |
| ROC AUC | 0,784210 | 0,777878 |
| Average precision | 0,560998 | 0,543521 |
| Brier score | 0,132362 | 0,136377 |
| Log loss | 0,423153 | 0,432887 |

Average precision là `average_precision_score`, không phải trapezoidal PR AUC.
Các giá trị final test trên là point estimates, chưa có confidence intervals
cho holdout. Không diễn giải sự chênh lệch giữa hai tập thành temporal drift.
Reliability bins 0,1-width lưu trong `holdout-metrics.json`; last bin bao gồm
probability = 1 và tổng số khách hàng/events được đối chiếu.

## 5. Bằng chứng và kiểm soát lần mở holdout

- `freeze-complete.json` bind hashes của selection rubric, model, encoder,
  settings cùng lineage comparison/assessment/features/case.
- Frozen evaluation codec kiểm tra parity với development encoder cho toàn
  bộ PAY source codes trước khi đọc holdout. Giữ nguyên mean/std/vocabulary;
  development encoder vẫn từ chối final-test role.
- `access-start.json` ghi mục đích và frozen bundle hash trước predictor query.
  Query chỉ lấy 19 allowlisted fields của final test; không chọn demographic
  predictors hoặc các development clients.
- SQLite ledger private `private evidence omitted from public release` claim
  source hash + partitions hash + protocol hash trước lần mở. Một frozen model
  khác không được score lại cùng source/split qua adapter này. Lần thất bại
  cũng giữ claim; cần điều tra audit thay vì âm thầm mở lại.
- `private-holdout-scores.parquet` chứa 3.001 IDs/labels/probabilities, private.
  Scores reload khớp chính xác và mọi aggregate metric được tính lại từ file.
  Không gửi IDs hoặc scores cho browser/public export.
- Bundle/case/source verification được chạy lại trước completion. Ledger đã
  ghi `completed`. Các kiểm soát là ứng dụng cục bộ; người có quyền sửa files
  hoặc ledger không bị ngăn bằng cryptographic signing/external custody.

## 6. Phạm vi dùng được và phần phải làm tiếp

Dùng để học và so sánh model behavioral risk trên source cohort, xây pipeline
có lineage, train-only preprocessing, persisted scoring parity, validation
uncertainty và đánh giá model đã freeze. Không dùng trực tiếp để approve/deny
tín dụng, pricing, IFRS 9 ECL, Basel capital hoặc gọi là PD 12 tháng.

P1 còn thiếu intended-use review với stakeholder, đánh giá subgroup/fairness,
economic decision policy và costs, dữ liệu mới để kiểm tra thời gian và
population transfer, monitoring/drift design và acceptance đầy đủ theo kế hoạch.
Aggregate app/API/report đã triển khai; xem
[SUITE_APP_AND_RETAIL_WORKFLOW.md](SUITE_APP_AND_RETAIL_WORKFLOW.md).
P2 mortgage vẫn thiếu annual vintages qua
Clarity; kết quả retail không thay thế yêu cầu của mortgage.

## 7. Chạy và tra cứu

Bộ kiểm thử đầy đủ sau bổ sung freeze/holdout: **517 passed** (375 engine,
142 application). Mười checks mới kiểm tra selection fallback/calibration
evidence, codec parity và unseen buckets, từ chối wrong-role/nonfinite/bool,
không gọi fit khi evaluation, ledger chống mở lại source/split và full synthetic
holdout flow với development predictors cố tình không hợp lệ.

Từ `local machine path omitted`, lệnh đã dùng:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/freeze_retail.py --comparison retail-comparison-b560ea676127
.\.venv\Scripts\python.exe -X utf8 scripts/evaluate_retail_holdout.py --freeze retail-freeze-3dc86f5afe01
```

Final test đã được đánh giá: đọc saved metrics/receipts để tra cứu. Lệnh đánh
giá lần nữa sẽ bị ledger từ chối, không cần chạy lại để xem kết quả.
