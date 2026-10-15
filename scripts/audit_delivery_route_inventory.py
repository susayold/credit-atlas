"""Generate a source-only route/reference inventory for M01-028.

This scan finds API path literals in the local server and direct string
references in the UI, tests, and browser QA scripts. It is an inventory aid,
not proof that a referenced route passes an acceptance test.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


def inventory(root: Path) -> list[dict[str, object]]:
    server = root / "src/credit_atlas/server.py"
    tree = ast.parse(server.read_text(encoding="utf-8"))
    routes = sorted({
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.startswith("/api/")
    })
    groups = {
        "ui": sorted((root / "apps/web").rglob("*.js")),
        "tests": sorted((root / "tests").rglob("test_*.py")),
        "browser_qa": sorted((root / "scripts").glob("browser_*.py")),
    }
    text_by_path = {
        path: path.read_text(encoding="utf-8", errors="ignore")
        for paths in groups.values() for path in paths
    }

    result = []
    for route in routes:
        references: dict[str, list[str]] = {}
        for kind, paths in groups.items():
            found = [str(path.relative_to(root)).replace("\\", "/")
                     for path in paths if route in text_by_path[path]]
            references[kind] = found
        result.append({"route": route, "references": references})
    return result


def render_markdown(root: Path, routes: list[dict[str, object]]) -> str:
    lines = [
        "# M01-028 — Inventory route API và reference kiểm thử",
        "",
        "Sinh tự động từ `src/credit_atlas/server.py`, `apps/web`, `tests` và",
        "`scripts/browser_*.py`. Chỉ đọc mã nguồn; không mở artifact hoặc dữ liệu",
        "private. Danh sách cho biết nơi có chuỗi route trực tiếp, không chứng minh",
        "route đã được kiểm thử đầy đủ, đúng payload hay đã qua browser acceptance.",
        "",
        f"- Root được quét: `{root.name}`",
        f"- Path literals trong server: **{len(routes)}**",
        "- `HTTP tests` và `Browser QA` là reference tĩnh; cần đọc evidence/receipt",
        "  riêng trước khi xem là nghiệm thu.",
        "- Report alias thường được tải qua UI link; route base trong browser script",
        "  không tự chứng minh rằng alias trả đúng attachment.",
        "",
        "| API route | UI reference | HTTP-test reference | Browser-QA reference |",
        "|---|---|---|---|",
    ]
    for item in routes:
        refs = item["references"]
        def display(values: list[str]) -> str:
            return ", ".join(f"`{value}`" for value in values) if values else "—"
        lines.append(
            f"| `{item['route']}` | {display(refs['ui'])} | "
            f"{display(refs['tests'])} | {display(refs['browser_qa'])} |"
        )
    lines.extend([
        "",
        "## Evidence review — 16/10/2026",
        "",
        "The API serves 167 distinct path literals. P4 Portfolio catalog routes now",
        "have direct HTTP contract tests for `/api/exposure-imports`,",
        "`/api/exposure-convergence-studies`, `/api/exposure-tail-studies`,",
        "`/api/exposure-ecl-studies`, `/api/exposure-scenarios`, and",
        "`/api/exposure-movements`. The five study catalogs require exactly their",
        "source ID and return the catalog payload unchanged; malformed or extra",
        "filters fail with HTTP 400. Evidence: `tests/test_exposure_views.py` and",
        "`tests/test_exposure_catalog_http.py`.",
        "",
        "Portfolio Excel template/import and source-bound review/report have their",
        "own HTTP or browser checks. New direct HTTP contracts cover the HMDA, SEC,",
        "and Market catalogs plus SEC/Market snapshots. HTTP tests also exercise",
        "HMDA aggregate/labeled reports, SEC issuer reports, Market reports and",
        "daily-series response forwarding, cache headers, and download attachment",
        "behavior; see `tests/test_workspace_catalog_http.py`. These contracts use",
        "controlled service responses and do not replace real-source data QA or",
        "full browser acceptance for every UI download path. M01-028 stays Partial",
        "until remaining report families, real-source failure paths and UI download",
        "flows have independent evidence.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    routes = inventory(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(root, routes), encoding="utf-8")
    print(f"routes={len(routes)} report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
