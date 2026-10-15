from pathlib import Path
import hashlib
import re

source = Path("D:/data/Codex/research/credit-risk-master/2026-10-08/CREDIT_RISK_MASTER_RESEARCH.md")
target = Path("D:/data/Codex/credit-atlas/docs/PLAN_MODULE_01.md")
text = source.read_text(encoding="utf-8")
chapter = text[text.index('<a id="chuong-47"></a>'):]
headings = re.findall(r"^### (47\.\d+)\. (.+)$", chapter, re.MULTILINE)
assert len(headings) == 26
assert len(re.findall(r"^\| M01-\d{3} \|", chapter, re.MULTILINE)) == 30

def reference(match):
    anchor = match.group(1)
    if anchor == "chuong-47" or anchor.startswith("chuong-47-"):
        return "(#" + anchor + ")"
    return "(" + source.as_posix() + "#" + anchor + ")"

chapter = re.sub(r"\(#(chuong-[a-zA-Z0-9-]+)\)", reference, chapter)
intro = """# CreditAtlas — Plan chi tiết module đầu tiên

**Module:** P2 — Mortgage & Real Estate.  
**Case:** D01 — Residential Mortgage Lifecycle & Loss Lab.  
**Ngày:** 08/10/2026.  
**Workspace:** D:/data/Codex/credit-atlas.

## Quyết định triển khai

Xây một app CreditAtlas; triển khai một case mortgage đủ sâu trước, rồi mở rộng các workspace khác. D01 nghiên cứu vòng đời khoản vay nhà ở: trạng thái trả nợ, chuyển trạng thái, cure/redefault, competing exits, vintage và observed loss. Phần model được nghiệm thu sau khi dữ liệu và protocol đủ điều kiện.

Nguồn chính là Freddie Mac annual loan-performance samples. Reuse engine credit-risk-strategy-lab qua commit pin và kiểm tra parity. FRED/ALFRED, FHFA, Fannie, HMDA và multifamily có thứ tự mở rộng riêng trong kế hoạch.

## Thứ tự triển khai

| Mốc | Làm gì | Khi nào đạt |
|---|---|---|
| R0 | Xác nhận source/code/schema/hashes; clean rebuild; đo tài nguyên | Pipeline có receipts, totals và đối chiếu giải thích được |
| R1 | Source/DQ, danh mục, timeline, transitions, episodes, vintage, loss và findings | Cùng frozen run; số liệu reconcile; user flow và export được kiểm tra |
| R2 | Qualify nhiều năm; chốt features và temporal splits | Coverage, support, maturity và leakage checks đạt protocol |
| R3 | Constant/logistic baseline, boosting challenger, calibration và OOT | Cùng cohort; selection freeze; model card và serving parity |
| R4 | Reproduction toàn case, QA và tài liệu bàn giao | Người khác chạy lại và đọc được question/data/method/results/limits |

**Budget dự kiến:** 160–232 giờ chủ động; khoảng 6–12 tuần nếu dành 20–30 giờ/tuần. R0+R1 khoảng 56–80 giờ. Estimate chưa bao gồm thời gian chờ access; support của nguồn có thể kéo dài phần model.

## Điểm xuất phát đã kiểm tra trong workspace

Kế hoạch gốc bên dưới được giữ như specification tại thời điểm lập. Các câu “chưa chạy trong lượt lập plan” là ghi nhận lịch sử. Bảng này bổ sung evidence local hiện có, không thay thế checklist nghiệm thu từng release.

| Phần | Evidence hiện có | Việc còn phải làm |
|---|---|---|
| Foundation | Engine pin 8d9994cfcb91fe871d66a4238c3f56053d71e920; sample 2012: 50.000 loans, 4.510.559 loan-months | Hoàn thiện semantic audit và dependency/resource documentation |
| Tests engine | 375 tests chạy đạt trong môi trường mới | Tests adapter/service/privacy/review/error handling |
| Reproduction | Hai pipeline đối chiếu 13 tables và 4 stable summaries; không có row differences | Final reproduction gồm app/report và model khi đã có |
| Descriptive app | Code views, frozen snapshot, timeline private, report và findings đã có | Browser QA chưa đạt hoàn toàn: console resource 404; cần sửa và kiểm tra lại |
| Model | Chỉ có annual vintage 2012; 102 positive early-entry D3: 89 Relief, 13 non-Relief | Qualify vintages khác; support/protocol review; chưa fit model mortgage đủ điều kiện |

Công việc tiếp theo là hoàn thiện R0/R1 và chuẩn bị R2. Số lượng loan-month không phải số lượng independent positive outcomes.

## Sprint tiếp theo

1. Hoàn thiện inventory/semantic audit; lưu code/source/dependency/resource receipts.
2. Xử lý lỗi browser; kiểm tra run/segment/basis/timeline/export/finding/mobile.
3. Kiểm tra adapter/service: không trộn run; không lộ source loan IDs; artifact bị sửa phải bị từ chối.
4. Đối chiếu portfolio/transition/vintage/loss; bổ sung follow-up audit cure/redefault.
5. Hoàn thiện freshness/missingness/support monitoring và investigation runbook.
6. Lưu findings có evidence; viết run instructions và R1 acceptance memo.
7. Pilot annual vintage bổ sung khi có quyền truy cập; ghi schema/support/footprint trước mở rộng protocol.

## Mục lục chi tiết

"""
toc = "\n".join("- [" + number + ". " + title + "](#chuong-" + number.replace(".", "-") + ")" for number, title in headings)
provenance = "\n\nGiữ đủ 26 mục và 30 task của chương 47. Research gốc: [" + source.name + "](" + source.as_posix() + "). SHA-256 lúc trích: " + hashlib.sha256(source.read_bytes()).hexdigest() + ".\n\n---\n\n"
target.write_text(intro + toc + provenance + chapter, encoding="utf-8")
result = target.read_text(encoding="utf-8")
anchors = set(re.findall(r'<a id="([^"]+)"></a>', result))
local_links = re.findall(r"\]\(#([^)]+)\)", result)
assert all(anchor in anchors for anchor in local_links)
assert len(re.findall(r"^\| M01-\d{3} \|", result, re.MULTILINE)) == 30
print(target.as_posix())
print(f"{len(result.split())} words; 26 sections; 30 tasks; {len(local_links)} internal links checked")
