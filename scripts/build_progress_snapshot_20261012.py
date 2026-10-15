"""Create a read-only accounting snapshot; never promote requirement statuses."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'docs/COMPLETION_REQUIREMENTS_50.json'
raw = source.read_bytes()
data = json.loads(raw)
requirements = data['requirements']
counts = Counter(r['checkpoint_status'] for r in requirements)
assert len(requirements) == 50
assert counts == {'Đã có': 21, 'Có điều kiện': 9, 'Một phần': 12, 'Cần dữ liệu': 8}

lines = [
    '# CreditAtlas — đối chiếu chi tiết với plan ngày 12/10/2026',
    '',
    'Bản kiểm kê đọc từ sổ 50 yêu cầu, plan KPI và các receipt đã lưu. Không chạy lại toàn bộ hệ thống trong lần kiểm kê này. Không thay đổi trạng thái nghiệm thu hoặc mở lại frozen holdout.',
    '',
    '## 1. Tỷ lệ có thể báo cáo',
    '',
    '| Cách đo | Số mục | Tỷ lệ |',
    '|---|---:|---:|',
    '| Trạng thái Đã có trong checkpoint |21/50|42%|',
    '| Đã có và Có điều kiện |30/50|60%|',
    '| Có triển khai theo ba trạng thái đầu |42/50|84%|',
    '| Một phần |12/50|24%|',
    '| Cần dữ liệu để đạt scope đầy đủ |8/50|16%|',
    '',
    f'Các tỷ lệ tính đều từng capability, không theo giờ công. 60% và 84% là coverage, không phải tỷ lệ hoàn thành hoàn toàn. Nghiệm thu theo toàn bộ yêu cầu hiện tại: {sum(bool(r["full_completion_proven"]) for r in requirements)}/50 mục có full_completion_proven. Đây là số mục đã đóng bằng evidence, không phải tỷ lệ giờ công hoặc production readiness. Một số mục Cần dữ liệu đã có thêm sub-workflow nhưng chưa đủ điều kiện nâng trạng thái.',
    '',
    '## 2. Theo domain',
    '',
    '| Domain | Đã có | Có điều kiện | Một phần | Cần dữ liệu | Đã có | Có workflow gồm điều kiện |',
    '|---|---:|---:|---:|---:|---:|---:|',
]
names = {'P1': 'Retail', 'P2': 'Mortgage', 'P3': 'Business', 'P4': 'Portfolio & observatory', 'P5': 'Structured & market'}
for prefix, name in names.items():
    c = Counter(r['checkpoint_status'] for r in requirements if r['id'].startswith(prefix))
    lines.append(f'|{prefix} {name}|{c["Đã có"]}|{c["Có điều kiện"]}|{c["Một phần"]}|{c["Cần dữ liệu"]}|{c["Đã có"] * 10}%|{(c["Đã có"] + c["Có điều kiện"]) * 10}%|')

lines += [
    '', '## 3. Bổ sung mới và giới hạn còn lại', '',
    '- **P1.02 LendingClub:** đã tải nguồn công khai gồm 2.260.701 accepted và 27.648.741 rejected records, profile 151/9 cột, dictionary và temporal evidence. API, app, lọc cohort, quality tables, JSON export đã có. Receipt browser `lendingclub-full-source-qa-b7ce59b0f371/receipt.json`: PASS 4 nhóm, ledger không đổi. Chưa chứng minh application-time feature availability, cutoff quan sát, mature PD12 labels, borrower identity và intended-use/OOT; không tính approval rate từ hai population chưa đối sánh.',
    '- **P1.05 Affordability:** đã có schema, engine, API và form nhập trong app; quy đổi kỳ thu nhập/nghĩa vụ, total DTI, residual income, policy khai báo và sensitivity; private JSON export. Bổ sung XLSX adapter/API/file picker, source cell lineage, form hydration và blank guided template/download: 53 adapter/engine/HTTP tests PASS, browser `affordability-excel-qa-5db4d5f8f7f8/receipt.json` PASS 5 nhóm; form regression `affordability-qa-560a56b59b5a` PASS 4; native Excel 38 cells/2workbooks PASS. Ledger không đổi. Hồ sơ QA là synthetic. Chưa có verified income, chứng từ nghĩa vụ thực, source-document verification và người chịu trách nhiệm xác minh; chưa trả quyết định tín dụng.',
    '- **P2.01/P2.02 public Fannie samples:** thêm7files/1217459bytes,Single-Family8loans/757monthly rows108positions,Multifamily4loans/241monthly rows62fields và17annual DSCR rows. Independent96749positions/173fields PASS,27backend/HTTP tests và4browsergroups PASS. Source/API/UI/export đã có,không thêm Freddie annual vintage hoặc qualify PD12;sample được cung cấp để thiết lập database.',
    '- **P3.03/P3.07/P3.08 DSCR và covenant:** đã có EBMUD actual historical debt-service/DSCR và driver bridge; Ford facility versions, Apple nominal note schedules, nguồn clause/covenant. Actual historical DSCR không tự đóng toàn bộ covenant workbench: còn effective amendment chain, adjusted definitions, actual balances và supported headroom/compliance.',
    '- **P4.09 Sovereign:** thêm 4 editions 2023–2026, 42.519 entity-year rows; có archive/API/app/export và audit. Chưa là calibrated sovereign PD/LGD hoặc validated macro stress model.',
    '- **P5 dữ liệu collateral:** thêm mirror ABS-EE 488.219 asset-period rows, field definitions, static-pool 21 cohorts, managed-pool 7 kỳ và SOFR benchmark 443 observations. Còn source fidelity, loan-level targets, full legal waterfall, forecast và independent valuation benchmark.',
    '- **Excel/KPI:** catalogue 88 KPI và 22 quality controls; 6 workbooks, 9.264 cells/746 formulas đã có native baseline checks và 18 ca đại diện/59 checks PASS. Chưa chứng minh mọi KPI có actual đủ đầu vào hoặc full native/production qualification.',
    '', '## 4. Chi tiết 50 yêu cầu', '',
    'Cột đầu ra dưới đây là **đích yêu cầu trong plan**, không khẳng định mọi đầu ra đã nghiệm thu. Trạng thái là checkpoint hiện ghi; partial evidence và các cập nhật trên giải thích phần đã bổ sung. “Bước tiếp theo” trong sổ có thể là câu cũ, cần đọc cùng remaining của checkpoint mới nhất.',
]
for prefix, name in names.items():
    lines += ['', f'### {prefix} — {name}', '']
    for r in requirements:
        if not r['id'].startswith(prefix):
            continue
        lines += [f'#### {r["id"]} — {r["title"]}', '', f'**Checkpoint:** {r["checkpoint_status"]}. **Toàn bộ yêu cầu hiện tại đã nghiệm thu:** {"Có" if r["full_completion_proven"] else "Chưa chứng minh"}.', '', f'**Đầu vào yêu cầu:** {r["required_inputs"]}', '', f'**Đầu ra đích của plan:** {r["required_outputs"]}', '', f'**Điều kiện nghiệm thu:** {r["acceptance"]}', '', f'**Bước tiếp theo ghi trong sổ:** {r["next"]}', '']
        for e in r.get('completion_evidence', []):
            lines += [f'- Nghiệm thu: {e.get("checkpoint")}. {e.get("scope", "")}', f'  Báo cáo: [{Path(e["document"]).name}]({Path(e["document"]).name}).']
        for e in r.get('partial_evidence', []) + r.get('partial_delivery_evidence', []):
            lines += [f'- Evidence: {e.get("checkpoint", e.get("as_of", "checkpoint"))}. {e.get("scope", "")}' ]
            if e.get('remaining'):
                lines += [f'  Phần còn thiếu tại checkpoint: {e["remaining"]}']
            if e.get('document'):
                lines += [f'  Tài liệu: [{Path(e["document"]).name}]({Path(e["document"]).name}).']
        lines += ['']

lines += [
    '## 5. Plan KPI/phân tích riêng', '',
    '11/17 = 64,7% về delivery coverage: A1–A5 và B1–B6 đã triển khai trong scope hiện có. Không cộng 17 mục này vào 50 vì có overlap.', '',
    '| Nhóm | Nội dung | Tình trạng |', '|---|---|---|',
    '|A1–A5|Regional movement; mortgage migration/cure; policy economics; issuer ratios; structured cash bridge|Đã triển khai trong scope dữ liệu/assumptions|',
    '|B1–B6|Quality controls; comparable baseline; analyst review; KPI Excel; corporate Excel; maturity Excel|Đã triển khai; qualification mở rộng còn thiếu|',
    '|C1|Retail temporal/OOT validation|Có dữ liệu mới và temporal profile; chưa có study OOT đủ điều kiện|',
    '|C2|Mortgage horizon PD12|Thiếu authorized multi-vintage data và model/calibration/OOT|',
    '|C3|Qualified LGD|Thiếu recovery timing, cost/discount conventions và mature support|',
    '|C4|Full DSCR/covenants|Actual DSCR/clause evidence đã bổ sung; chưa đóng full debt-service/legal scope|',
    '|C5|Decision-grade EL/ECL|Engines conditional; thiếu qualified parameters, contracts/EIR/staging và governance|',
    '|C6|Forward structured valuation|Replay/assumption studies; thiếu forecast/full waterfall/curves/benchmark|',
    '', '## 6. Thứ tự để tiến tới hoàn thành', '',
    '1. Nghiệm thu lại từng capability theo source, phép tính độc lập, runtime, browser, export và intended-use; ghi completion evidence trước khi nâng trạng thái.',
    '2. Retail: qualify temporal/application sources, xác minh income/obligations và mở rộng Affordability intake; sau đó OOT, limit/pricing, collections.',
    '3. Mortgage: lấy annual vintages hợp lệ, chốt temporal/entity-safe splits, PD12/calibration và recovery/LGD conventions.',
    '4. Business: actual debt-service inputs, effective legal terms, adjustment ledger, headroom và complete memo/review.',
    '5. Portfolio: qualified PD/LGD/EAD, actual positions/EIR/staging, validated stress/dependence và authenticated review.',
    '6. Structured: original collateral provenance, complete contractual regimes, cashflow forecasts, security curves và independent pricing benchmark.',
    '', '## 7. Nguồn đối chiếu', '',
    '- [Sổ 50 yêu cầu](COMPLETION_REQUIREMENTS_50.json)',
    '- [Plan workbench](PLAN_WORKBENCH_DETAIL.md)',
    '- [Plan KPI](PLAN_KPI_ANALYTICS_NEXT_VI.md)',
    '- [Kiểm kê trước ngày 11/10](PROGRESS_VS_PLAN_2026-10-11_VI.md)',
    '- [Affordability contract](AFFORDABILITY_INTAKE_VI.md) — phần UI còn ghi cần làm trong tài liệu này đã được bổ sung; receipt UI nêu ở mục 3 là cập nhật mới hơn.',
]
target = ROOT / 'docs/PROGRESS_VS_PLAN_2026-10-12_VI.md'
target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
assert source.read_bytes() == raw
print(json.dumps({'report': str(target), 'requirements': len(requirements), 'counts': dict(counts), 'full_completion_proven': sum(bool(r['full_completion_proven']) for r in requirements), 'requirements_unchanged': True}, ensure_ascii=False))
