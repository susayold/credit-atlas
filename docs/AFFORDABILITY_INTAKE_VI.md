# Affordability — intake và tính toán theo policy khai báo

Ngày 12/10/2026. Phần này bổ sung data contract/calculation cho P1.05, chưa thay thế verified-income data hoặc household obligation evidence còn thiếu. Không tạo hồ sơ giả trong app để tuyên bố đã hoàn thành capability.

## 1. Câu hỏi và định nghĩa

Assessment dùng gross income, net income, recurring non-debt expenses, existing debt payments và proposed payments trong cùng currency/scope/date.

- Total DTI = (existing debt payments + proposed payments) / gross monthly income.
- Residual = net monthly income − recurring non-debt expenses − existing debt payments − proposed payments.

Gross và net không được cộng chung. Không suy thu nhập từ credit limit. Không dùng DTI LendingClub làm total-obligation DTI vì định nghĩa của issuer loại mortgage và requested loan.

[CFPB giải thích DTI](https://www.consumerfinance.gov/ask-cfpb/what-is-a-debt-to-income-ratio-en-1791/) dùng monthly debt/gross monthly income. [Quy định cho covered dwelling transactions](https://www.consumerfinance.gov/rules-policy/regulations/1026/43/) cung cấp bối cảnh income/debt verification và residual income. Đây là nguồn tham khảo về định nghĩa; engine không chứng nhận compliance với quy định này hoặc quy định Việt Nam, và không tự đặt ngưỡng pháp lý/universal threshold.

## 2. Contract intake

Top-level fields: case_ref, as_of, currency, scope, scope_ref, members; năm nhóm gross_income/net_income/recurring_expenses/debt_payments/proposed_payments; coverage attestation cho từng nhóm; policy; optional stress.

Mỗi item gồm ref, amount, period, evidence_ref, valid_through. Amount là decimal string không âm hoặc null nếu thiếu. Không nhận NaN, infinity, exponent notation, currency symbols hoặc numeric floats. Ref là pseudonymous reference, không dùng tên/ngày sinh hoặc credentials.

Period conventions được ghi rõ: monthly ×1, annual ÷12, quarterly ÷3, weekly ×52/12, biweekly ×26/12, semimonthly ×2. Các factors là Fraction chính xác. Đây là average-month convention, chưa là dự báo dòng tiền theo lịch payroll/calendar.

Coverage attestation là khai báo của người nhập, không phải chứng nhận completeness. Empty list với coverage true có nghĩa khai báo known zero; coverage false giữ total unavailable. Amount null hoặc validity đã hết hạn chặn các phép tính phụ thuộc. Known partial sums nằm riêng khỏi usable total. Item row giữ source amount/period, factor, monthly amount và source validity date.

Expense/debt/proposed obligation refs không được trùng nhau để chặn double counting rõ ràng. Nghĩa vụ giống nhau nhưng đặt ref khác vẫn cần semantic review.

## 3. Policy và sensitivity

Policy gồm policy_ref, max_total_dti_fraction và min_monthly_residual. Không có threshold thì policy comparison unavailable, không tự dùng 43% hoặc threshold từ nơi khác. Có threshold phải có policy reference; policy_confirmed vẫn false.

So sánh toán học trả WITHIN/EXCEEDS_DECLARED_LIMIT hoặc MEETS/BELOW_DECLARED_FLOOR. Không trả Approved/Rejected. DTI denominator zero giữ unavailable; residual âm được giữ để thấy shortfall.

Optional sensitivity nhận gross/net income reduction fractions và extra monthly expense. Baseline giữ nguyên, stress ghi là assumptions, không gọi là actual outcomes hoặc validated macro stress. Reduction phải nằm 0–1.

## 4. API

POST `/api/affordability-assess` trả assessment; POST `/api/affordability-report` trả private JSON attachment. Cùng intake tạo cùng kết quả. Endpoint yêu cầu local same-origin, application/json và X-CreditAtlas-Client: local, dùng size bound 64KB của handler. Không ghi dữ liệu vào URL hoặc fit/rescore model.

Kết quả gồm normalized input rows, exact rational/Decimal50 values, baseline, declared stress và missing evidence references. Không persist hồ sơ trong database ở checkpoint này.

Assessment kind là DECLARED_INPUT_ARITHMETIC_ASSESSMENT. evidence references, income verification, coverage verification, policy confirmation và legal compliance chưa qualified; credit_decision null. Tính đúng không chứng minh chứng từ đúng hoặc khả năng trả nợ đã được xác minh.

## 5. Tests và phần còn lại

Unit cases kiểm tra independent arithmetic examples, policy boundary bằng ngưỡng, period factors, sensitivity, zero/missing/expired inputs, partial coverage, duplicate obligations, household scope và invalid encodings. Synthetic inputs chỉ ở QA tests, không thay data thật cho app.

HTTP checks kiểm tra same-origin/local-client guard, JSON contract, error sanitization, no-store và exact private export. Hai lỗi test setup đầu được sửa: import fixture module và thiếu local-client header; không nới security guard.

Giao diện intake không prefill số liệu giả đã bổ sung: form context, năm nhóm inputs, coverage, declared policy, sensitivity, missing/expiry evidence và private export. UI receipt `affordability-qa-9809fc5f778e/receipt.json`: 4 nhóm PASS, ledger không đổi. Editing/tab change chặn stale assessment/export, kể cả export trả chậm.

Excel adapter/API/file picker và template có hướng dẫn/dropdowns đã bổ sung sau checkpoint engine; xem [Excel intake](AFFORDABILITY_EXCEL_INTAKE_VI.md). Còn source-document verification, verification ownership, completeness/overlap review và dữ liệu income/obligation thực. P1.05 chưa hoàn thành đầy đủ và 50 capability states chưa được nâng từ các sub-workflows này.

Receipt cuối: `private evidence omitted from public release`, 34 tests PASS. Targeted engine/HTTP run có 17 tests PASS; engine riêng có 16 tests PASS. Failed test XML trước sửa vẫn được giữ. Đây là numerical/HTTP validation, không là verified-income hoặc production qualification.
