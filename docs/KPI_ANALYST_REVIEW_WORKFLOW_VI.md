# CreditAtlas — review của analyst gắn với KPI

## 1. Mục đích và phạm vi

Review giúp lưu điều analyst đang quan sát, giả thuyết cần kiểm chứng và người phụ trách cùng evidence. Đây là nghiên cứu riêng tư, không là credit approval, model validation sign-off hoặc xác nhận waterfall pháp lý. Owner là tên tự khai báo; app chưa có xác thực danh tính hay maker/checker của tổ chức.

## 2. Tạo review từ app

1. Risk monitor → Phân tích KPI chi tiết → chọn domain. Kiểm tra actuals, source scope, quality controls và baseline.
2. Trong **Analyst review gắn với KPI**, bấm **Tạo KPI review**. Điền tiêu đề, owner, nhận định, giả thuyết tùy chọn và bước kiểm chứng. Required fields được kiểm tra trước lưu.
3. Snapshot lấy tại lúc mở form: domain/scope, metric actuals/formulas/support/comparisons, quality controls, filters, baseline requested/resolved/status và source references. Phạm vi lifetime/quality/replay vẫn tách khỏi current-period comparisons.
4. Bấm **Lưu KPI review**. Server xác minh các nguồn tham chiếu bằng services hiện có; nguồn unavailable/changed thì không tạo record thay thế. Snapshot KPI được tính từ màn hình; server không tính lại độc lập mọi metric. Hai điều này được ghi riêng trong export.
5. Mở **Review đã lưu** để xem record. **Lịch sử & snapshot** hiển thị context, source digests và mọi revision; **Xuất KPI review JSON** tải package riêng tư.

## 3. Sửa nhận định và giữ evidence

Bấm **Sửa KPI review** để đổi title/owner/judgement/hypothesis/next_action/status. `draft`, `reviewed`, `archived` là trạng thái analyst review; reviewed không tự thay data/model/legal gates. Mỗi lần lưu tăng revision; revision cũ vẫn tồn tại.

Captured snapshot, thời điểm capture và source digests bất biến giữa các revisions. Khi muốn dùng baseline hoặc evidence mới, tạo một review mới. Server từ chối update chứa snapshot mới. Nếu một cửa sổ khác đã sửa record, bản revision cũ trả conflict; đọc lại record mới trước khi sửa tiếp, không ghi đè âm thầm.

## 4. Data contract và lưu trữ

Storage: `artifacts/private/monitor-reviews.sqlite3` dưới D:\data\Codex\credit-atlas. SQLite transaction giữ record mới nhất và lịch sử revision atomically. Không thay source/model files hoặc holdout access ledger. Snapshot JSON được hash; nguồn được verify và hash riêng tại capture. Digest là dấu vết nội dung, không phải chữ ký của analyst.

Source kinds theo domain: P1 suite + saved policy khi có; P2 verified mortgage run; P3 suite + SEC view; P4 exposure imports theo current/baseline; P5 ABS view. Không dùng review này để join SBA/SEC/UCI thành borrower identity.

API local/same-origin: GET `/api/monitor-reviews?domain=P1`; GET `/api/monitor-review?id=…` và `/api/monitor-review-report?id=…`; POST `/api/monitor-reviews`. Mutations cần JSON, local Origin/client header và bounded body; source IDs được xử lý bởi verified services, không là đường dẫn tùy ý.

## 5. Cách viết nhận định có thể kiểm chứng

Ghi số liệu và scope trước, rồi giả thuyết riêng, sau đó bước kiểm chứng. Ví dụ: “D3 stock share giảm giữa hai kỳ trên usable active denominator; cần đọc transitions và exits để hiểu movement.” Không đổi nhận xét đó thành “policy đã cải thiện cure” khi chưa có dữ liệu xác định tác động.

Các record có tiêu đề `QA monitor-review-qa-…` do kiểm tra giao diện tạo sẽ giữ status archived; đây là test evidence, không phải nhận định kinh doanh.

## 6. Nghiệm thu checkpoint B3

Actual browser: `artifacts/private/monitor-review-qa-f0bc7bae609e/receipt.json`, **7 PASS** qua năm domain, persisted reload/private export, mobile và unchanged holdout ledger. API/unit review tests **6 PASS**; 15 legacy HTTP/Excel/suite tests PASS (21 distinct). Receipts JUnit: `artifacts/private/monitor-review-api-20261010.xml` và `artifacts/private/monitor-review-http-20261010.xml` (overlap năm tests).

KPI/source/baseline regression sau integration: `artifacts/private/kpi-analysis-qa-cb670b239571/receipt.json`, **19 PASS**, 88 nghiệp vụ KPIs + 22 quality controls. Kiểm tra này không phải independent recomputation của mọi snapshot review do client khác gửi; scope capture đã ghi ở contract.

Liên quan: [KPI handbook](KPI_ANALYSIS_GUIDE_VI.md), [Plan phát triển](PLAN_KPI_ANALYTICS_NEXT_VI.md), [Trạng thái và receipts](FIVE_WORKSPACES_STATUS.md).
