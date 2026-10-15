"""Build a Vietnamese, source-bound KPI handbook from a verified monitor export."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/private/kpi-analysis-qa-cb670b239571/analysis-all.json"
DEST = ROOT / "docs/KPI_ANALYSIS_GUIDE_VI.md"

def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")

def display(value, unit):
    if value is None:
        return "Unavailable"
    if unit == "share":
        return f"{value * 100:,.4f}%"
    if unit == "USD":
        return f"{value:,.2f} USD"
    if unit == "count":
        return f"{value:,}"
    if unit == "declared_cost_units":
        return f"{value:.6f} declared cost units"
    return f"{value:.6f}"

def table(columns, rows):
    return "\n".join(["| " + " | ".join(map(cell, columns)) + " |",
                      "| " + " | ".join(["---"] * len(columns)) + " |"] +
                     ["| " + " | ".join(map(cell, row)) + " |" for row in rows])

def main():
    export = json.loads(SOURCE.read_text(encoding="utf-8"))
    out = ["# CreditAtlas — dữ liệu, phân tích và 88 KPI theo năm domain",
           "Bản kiểm tra ngày 10/10/2026. Đây là bản chụp từ các nguồn đã lưu, không phải feed thời gian thực. Trong app: **Risk monitor → Phân tích KPI chi tiết → P1–P5**. Có thể đổi domain, cửa sổ lịch sử và count/UPB; xuất JSON riêng tư lưu cả kết quả, filters và provenance.",
           "## 1. Cách đọc và phạm vi",
           "Mỗi KPI gồm actual, công thức/mẫu số, so sánh khi có kỳ tương thích và cách diễn giải. Chưa có target, risk appetite hoặc giới hạn được phê duyệt của một tổ chức cụ thể; app không tự gán mức tốt/xấu. Null giữ là Unavailable; zero chỉ được dùng khi nguồn thực sự ghi zero.",
           "Các nguồn khác nhau về thời gian, population và grain. Retail là Taiwan 2005; Mortgage là annual sample Freddie vintage 2012 theo dõi đến tháng 3/2026; SBA là source-record stock; Portfolio dùng chính snapshot Freddie đó; ABS là reported periods của World Omni 2025-A. Không cộng dữ liệu các domain thành một danh mục ngân hàng, đặc biệt P2/P4 có source overlap.",
           "Amount nguồn trong backend và các bảng exact được giữ theo Decimal/string. KPI mô tả trong trình duyệt dùng số floating point; số USD hiển thị trên monitor làm tròn whole dollars. Bảng dưới giữ hai chữ số thập phân của phép tính mô tả, không thay ledger kế toán. Không cộng các monthly stock để suy ra unique loans.",
           "## 2. Nguồn và snapshot",
           table(["Domain", "API đã đọc", "Evidence ID", "Phạm vi"],
                 [[p["domain"], p["query"], p["identifier"], p["scope"]] for p in export["provenance"]]),
           "P4 so sánh import `exposure-import-57b88e00bedb` (2026-03) với `exposure-import-facfbef3f419` (2026-02), cùng USD/region. Thời điểm đọc export: " + export["read_at"] + "."]
    for i, (domain, r) in enumerate(sorted(export["kpi_analysis"].items()), 3):
        out += [f"## {i}. {domain}: {r['title']}", r["scope"], "### Nhận xét từ dữ liệu", "\n".join("- " + f for f in r["findings"]), "### Định nghĩa và actual của từng KPI"]
        for j, m in enumerate(r["metrics"], 1):
            out += [f"#### {j}. {m['name']}",
                    f"**Actual:** {display(m['value'], m['unit'])}. **Công thức/support:** {m['formula']}.",
                    "**Diễn giải:** " + m["interpretation"]]
            c = m["comparison"]
            if c:
                delta = f"{c['absolute_change'] * 100:+.4f} điểm phần trăm" if c["unit"] == "share" else display(c["absolute_change"], c["unit"])
                rel = "không xác định khi baseline bằng 0" if c["relative_change"] is None else f"{c['relative_change'] * 100:+.4f}%"
                out += [f"**So sánh {c['period']}:** baseline {display(c['value'], c['unit'])}; thay đổi tuyệt đối {delta}; tương đối {rel}."]
            else:
                out += ["**So sánh:** chưa lưu kỳ/metric tương thích trong readout này; không tự tạo baseline."]
        if r.get("decomposition"):
            d = r["decomposition"]
            out += ["### Phân rã biến động D3", d["formula"], d["convention"],
                    table(["Thành phần", "Điểm phần trăm"], [[k, f"{d[k] * 100:+.6f}"] for k in ("numerator_effect", "denominator_effect", "total_change")]),
                    "Giữ mẫu số kỳ trước cho bước đổi tử số, rồi giữ tử số kỳ hiện tại cho bước đổi mẫu số. Hai phần cộng đúng thay đổi tỷ lệ; đổi thứ tự có thể đổi phân bổ. Phép tính không chứng minh cure, deterioration hoặc tác động chính sách."]
        if r.get("issuer_scopes"):
            out += ["### Scope từng issuer và đường dẫn evidence", table(["Issuer", "CIK", "Accession", "Report date", "Filed", "Cutoff", "SEC filing"], [[x["ticker"], x["cik"], x.get("accession", "Unavailable"), x["report_date"], x["filing_date"], x["asof"], x["filing_url"]] for x in r["issuer_scopes"]]), "Ratio source giữ exact values; current ratio dùng current assets/current liabilities, liabilities/assets không thay debt/EBITDA, net margin không thay interest coverage, OCF/revenue không thay DSCR. Các fields missing/ambiguous làm ratio Unavailable. SEC snapshot không phải issuer default dataset hoặc historical-vintage snapshot."]
        if r.get("cash_bridge"):
            b = r["cash_bridge"]
            out += ["### Selected-period cash/reserve bridge", f"Collection {b['period']}, payment {b['payment_date']}, regime {b['regime']}, basis {b['basis']}. Reconciliation: {b['reconciliation']}.",
                    "Cash: opening available funds − sum(from_available_funds) − ending cash = 0. Reserve: opening + credits − draws − ending = 0. Từng bước đối soát bằng integer cents; nguồn available funds đã net servicing. Reserve replenishment là internal transfer, không cộng như external distribution. Shortfalls ở các priority có thể overlap, không cộng thành loss.",
                    table(["Step", "Cash residual USD exact", "Reserve residual USD exact"], [[x["sequence"], x["cash_delta_exact"], x["reserve_delta_exact"]] for x in b["steps"]])]
        if r.get("region_bridge"):
            b = r["region_bridge"]
            out += ["### Bridge địa lý và đối soát tổng", b["formula"], b["interpretation"],
                    f"Prior {b['prior_period']}: {b['prior_total_exact']} USD; current {b['current_period']}: {b['current_total_exact']} USD; delta {b['total_delta_exact']} USD. Đối soát {b['reconciliation']} bằng integer cents. Contribution dùng prior total để các vùng cộng ra total relative change, không chia cho net delta."]
        for t in r["tables"]:
            out += ["### " + t["title"], table(t["columns"], t["rows"])]
        if r.get("data_quality"):
            q = r["data_quality"]
            out += ["### Chất lượng dữ liệu và phạm vi kiểm tra", q["scope"],
                    table(["Control/KPI", "Actual", "Formula/support", "Diễn giải"], [[x["name"], display(x["value"], x["unit"]), x["formula"], x["interpretation"]] for x in q["metrics"]]),
                    "\n".join("- " + f for f in q["findings"])]
            for t in q["tables"]:
                out += ["#### " + t["title"], table(t["columns"], t["rows"])]
        out += ["### Bước phân tích tiếp theo", r["next"]]
        if r.get("comparison_control"):
            c = r["comparison_control"]
            out += ["### Baseline control", table(["Field", "Value"], [[k, c[k]] for k in ["requested", "current_period", "resolved_period", "status", "rule"]]),
                    "Baseline chính chỉ áp các delta/decomposition tương ứng, không thay current actual. Chọn manual prior period hoặc tắt baseline trong app; không fallback nearest khi không có exact period. P2 YoY cùng tháng là comparison riêng, overview chart giữ monthly delta; lifetime transitions, data-quality controls và selected cash replay có scopes riêng."]
    out += ["## 8. Các KPI bổ sung và dữ liệu cần thiết",
            table(["Domain", "KPI/workflow", "Cần gì và trạng thái"], [
                ["P1", "Approval/reject rate; profit; drift/OOT", "Decisioned applications gồm rejected population, timestamps, prices/costs/capacity và mature outcomes. UCI booked cohort không đủ; policy preview theo declared costs đã có, chưa actual realized profit."],
                ["P2", "PD12, LGD, EL; cure/migration", "Target/horizon, temporal vintages, censoring và qualified EAD/loss definition. Loss gate đang blocked do support/coverage. Transition/lifecycle workflow đã có riêng; stock change không thay transition."],
                ["P3", "DSCR, ICR, leverage, covenant; bankruptcy", "Filing-specific financials, ratio conventions, debt service và legal covenant terms. SEC và UCI365 là workflows riêng; không tự join với SBA borrowers hoặc gán benchmark PD cho issuer."],
                ["P4", "Qualified EAD/PD/LGD/EL; ECL; VaR/ES", "Institution exposure/risk inputs, SICR/staging, scenario weights, cashflow losses/discounting và dependence assumptions. Scenario/ECL/tail engines có study có điều kiện; geographic HHI không thay economic capital."],
                ["P5", "Forward cashflows, valuation, OC/IC, DV01", "Collateral forecasts, full verified legal waterfall/trigger rules, instrument cashflows và discount/credit curves. Reported replay không thay forward pricing; Bond scenario workspace dùng assumptions riêng."]]),
            "Các mục này cũng xuất hiện dưới từng domain trong app tại **Các KPI cần dữ liệu / workflow bổ sung**. Danh mục 88 dòng là bộ KPI đọc trực tiếp từ các snapshot hiện có, không phải toàn bộ chỉ số cần cho mọi loại hình tổ chức tín dụng.",
            "## 9. Kiểm chứng và cách dùng",
            "KPI QA mới: 19 checks PASS, 88 rendered KPI rows, 22 quality controls independently reconciled, independent arithmetic checks (D3/decomposition/loss, calibration gap, HHI/movement, SBA denominators, ABS surplus), từng vùng/tổng đối soát Decimal, bridge scope/zero/missing/inconsistent-total safeguards, lifetime transition row sums/rates và confirmed follow-up denominators, validation policy action/cost/capacity reconciliation và unavailable-policy safeguards, issuer ratio/period/unit checks và single-issuer outage safeguards, all-step ABS cash/reserve reconciliation và selected-ledger outage, exact/manual/disabled baseline controls, no-nearest fallback, filters/export/reload, mobile 390px và browser exceptions. Monitor regression trước bridge: 10 checks PASS. Không refit/rescore frozen holdout; access ledger giữ nguyên.",
            "Receipts: `artifacts/private/kpi-analysis-qa-cb670b239571/receipt.json` và `artifacts/private/monitor-qa-a6dbe5387a8b/receipt.json`. Export nguồn cho tài liệu: `" + str(SOURCE.relative_to(ROOT)).replace('\\', '/') + "`. Tài liệu được tạo bằng `scripts/build_kpi_analysis_guide.py`.",
            "Khi đọc một biến động: xác nhận nguồn/kỳ/grain → xem support và missingness → đọc actual + baseline → phân rã theo nhóm hoặc bridge → mở workflow nghiệp vụ → ghi nhận định trong review cùng evidence. Giả thuyết nguyên nhân phải được kiểm chứng bằng dữ liệu liên quan; không coi decomposition số học là bằng chứng nhân quả.",
            "Liên quan: [KPI analyst review](KPI_ANALYST_REVIEW_WORKFLOW_VI.md), [Hướng dẫn workbench](WORKBENCH_USER_GUIDE_VI.md), [50 chức năng và kế hoạch](PLAN_WORKBENCH_DETAIL.md), [Trạng thái năm workspace](FIVE_WORKSPACES_STATUS.md)."]
    DEST.write_text("\n\n".join(out) + "\n", encoding="utf-8")
    print(DEST)

if __name__ == "__main__":
    main()
