"""Loopback-only application API and UI for the private research workspace."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .reviews import ReviewConflict
from .monitor_reviews import MonitorReviews
from .corporate_memos import CorporateMemos
from .service import EvidenceChanged, ResearchService, TOKEN_PATTERN, filters_from

STATIC = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
          "/nsmo": "nsmo.html", "/nsmo.html": "nsmo.html",
          "/nsmo.js": "nsmo.js", "/nsmo.css": "nsmo.css",
          "/workspace-content.js": "workspace-content.js",
          "/monitor.js": "monitor.js",
          "/kpi-analysis.js": "kpi-analysis.js",
          "/monitor-reviews.js": "monitor-reviews.js",
          "/corporate-memos.js": "corporate-memos.js",
          "/style.css": "style.css", "/favicon.svg": "favicon.svg",
          "/assets/credit-atlas-world-v1.png": "assets/credit-atlas-world-v1.png",
          **{f"/assets/credit-{name}-banner-v2.png": f"assets/credit-{name}-banner-v2.png"
             for name in ("retail", "mortgage", "business", "portfolio", "structured")}}


def handler_for(service: ResearchService):
    from .sec_read_cache import VerifiedSecReadCache
    from .sec_views import SecViews
    if isinstance(getattr(service, 'sec_views', None), SecViews) and not isinstance(service.sec_views, VerifiedSecReadCache):
        service.sec_views = VerifiedSecReadCache(service.sec_views)
    web = service.root / "apps/web"
    from .nsmo_views import NsmoViews
    nsmo_views = NsmoViews(service.root)
    monitor_reviews = MonitorReviews(service)
    corporate_memos = CorporateMemos(service)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # No private query parameters, pseudonymous keys or note text in logs.
            return

        def allowed(self, mutation=False):
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if host not in allowed or self.headers.get("Sec-Fetch-Site") == "cross-site":
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin not in {"http://" + item for item in allowed}:
                return False
            if mutation and (origin is None or self.headers.get("X-CreditAtlas-Client") != "local"):
                return False
            return True

        def send(self, code, body, content_type="application/json; charset=utf-8", filename=None, head=False):
            # Drain bounded rejected POST bodies before closing the HTTP/1.0
            # socket. Windows may otherwise reset it before the client reads
            # the error response. Never drain an unbounded advertised body.
            if self.command == "POST" and code >= 400 and not getattr(self, "_body_read", False):
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if 0 < length <= 65536:
                        self.connection.settimeout(5)
                        self.rfile.read(length)
                        self._body_read = True
                except (ValueError, OSError):
                    pass
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def do_HEAD(self):
            self.get(True)

        def do_GET(self):
            self.get(False)

        def get(self, head):
            if not self.allowed():
                self.send(403, {"error": "Local research origin required"}, head=head)
                return
            try:
                url = urlsplit(self.path)
                # Page URLs carry independent workspace/comparison state;
                # data API requests retain their smaller bounded contract.
                values = parse_qs(url.query, keep_blank_values=True, max_num_fields=32 if url.path in STATIC else 16)
                if any(len(v) != 1 for v in values.values()):
                    raise ValueError("Duplicate query parameter")
                query = {k: v[0] for k, v in values.items()}
                if url.path == "/downloads/nsmo-reference.xlsx":
                    if query:
                        raise ValueError("NSMO Excel reference accepts no filters")
                    workbook = service.root / "apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx"
                    if not workbook.is_file():
                        self.send(404, {"error": "NSMO Excel reference is not built"}, head=head)
                        return
                    self.send(200, workbook.read_bytes(),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              filename="CreditAtlas-NSMO-Reference.xlsx", head=head)
                    return
                if url.path == "/downloads/d02-data-reference.xlsx":
                    if query:
                        raise ValueError("D02 Excel reference accepts no filters")
                    workbook = service.root / "apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx"
                    if not workbook.is_file():
                        self.send(404, {"error": "D02 Excel reference is not built"}, head=head)
                        return
                    self.send(200, workbook.read_bytes(),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              filename="CreditAtlas-D02-Data-Reference.xlsx", head=head)
                    return
                if url.path == "/downloads/hud-fha-performance.xlsx":
                    if query:
                        raise ValueError("HUD FHA Excel reference accepts no filters")
                    workbook = service.root / "apps/excel/templates/CreditAtlas-HUD-FHA-Performance.xlsx"
                    if not workbook.is_file():
                        self.send(404, {"error": "HUD FHA Excel reference is not built"}, head=head)
                        return
                    self.send(200, workbook.read_bytes(),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              filename="CreditAtlas-HUD-FHA-Performance.xlsx", head=head)
                    return
                if url.path == "/downloads/nmdb-performance.xlsx":
                    if query:
                        raise ValueError("NMDB performance Excel reference accepts no filters")
                    workbook = service.root / "apps/excel/templates/CreditAtlas-NMDB-Performance.xlsx"
                    if not workbook.is_file():
                        self.send(404, {"error": "NMDB performance Excel reference is not built"}, head=head)
                        return
                    self.send(200, workbook.read_bytes(),
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              filename="CreditAtlas-NMDB-Performance.xlsx", head=head)
                    return
                if url.path == "/api/nmdb-performance":
                    if query:
                        raise ValueError("NMDB performance aggregate accepts no filters")
                    from .nmdb_performance import nmdb_performance_report
                    self.send(200, nmdb_performance_report(service.root), head=head)
                    return
                if url.path == "/api/hud-fha-performance":
                    if query:
                        raise ValueError("HUD FHA aggregate accepts no filters")
                    from .hud_fha_performance import hud_fha_performance_report
                    self.send(200, hud_fha_performance_report(service.root), head=head)
                    return
                if url.path == "/api/nsmo-profile":
                    if query:
                        raise ValueError("NSMO profile accepts no filters")
                    self.send(200, nsmo_views.report(), head=head)
                    return
                if url.path == "/api/nsmo-dictionary":
                    if query:
                        raise ValueError("NSMO dictionary accepts no filters")
                    self.send(200, nsmo_views.dictionary(), head=head)
                    return
                if url.path == "/api/nsmo-survey-returns":
                    if query:
                        raise ValueError("NSMO survey-return table accepts no filters")
                    self.send(200, nsmo_views.survey_returns(), head=head)
                    return
                if url.path == "/api/nsmo-domains":
                    if query:
                        raise ValueError("NSMO domain profile accepts no filters")
                    self.send(200, nsmo_views.domains(), head=head)
                    return
                if url.path == "/api/nsmo-target-feasibility":
                    if query:
                        raise ValueError("NSMO target feasibility accepts no filters")
                    self.send(200, nsmo_views.target_feasibility(), head=head)
                    return
                if url.path == "/api/nsmo-origination-feasibility":
                    if query:
                        raise ValueError("NSMO origination feasibility accepts no filters")
                    self.send(200, nsmo_views.origination_feasibility(), head=head)
                    return
                if url.path == "/api/nsmo-first-observed-transition-support":
                    if query:
                        raise ValueError("NSMO transition support accepts no filters")
                    self.send(200, nsmo_views.first_observed_transition_support(), head=head)
                    return
                if url.path in STATIC:
                    file = web / STATIC[url.path]
                    content = file.read_bytes()
                    types = {".html": "text/html", ".css": "text/css", ".js": "text/javascript",
                             ".svg": "image/svg+xml", ".png": "image/png"}
                    content_type = types[file.suffix]
                    if file.suffix != ".png":
                        content_type += "; charset=utf-8"
                    self.send(200, content, content_type, head=head)
                    return
                run = query.get("run", "")
                if url.path == '/api/monitor-reviews':
                    if set(query)!={'domain'}: raise ValueError('Review domain required')
                    result=monitor_reviews.list(query['domain'])
                elif url.path in {'/api/monitor-review','/api/monitor-review-report'}:
                    if set(query)!={'id'}: raise ValueError('Review identifier required')
                    result=monitor_reviews.report(query['id'])
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-KPI-review.json',head=head)
                        return
                elif url.path=='/api/corporate-memos':
                    result=corporate_memos.list(query)
                elif url.path in {'/api/corporate-memo','/api/corporate-memo-report'}:
                    if set(query)!={'id'}:raise ValueError('Memo ID required')
                    result=corporate_memos.report(query['id'])
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-corporate-memo.json',head=head)
                        return
                elif url.path == "/api/health":
                    result = {"status": "running", "mode": "local_private_research", "module": "P2/D01"}
                elif url.path == "/api/suite-views":
                    result = service.suite_views.catalog()
                elif url.path == '/api/retail-policies':
                    if set(query)!={'freeze_id'}: raise ValueError('Frozen-model policy catalog scope required')
                    result=service.retail_policy_views.catalog(query['freeze_id'])
                elif url.path == '/api/retail-subgroups':
                    result=service.retail_subgroup_views.catalog(query)
                elif url.path == '/api/retail-explanations':
                    result=service.retail_explanation_views.catalog(query)
                elif url.path == '/api/retail-cohort-explanations':
                    result=service.retail_cohort_explanation_views.catalog(query)
                elif url.path == '/api/retail-explanation-clients':
                    result=service.retail_cohort_explanation_views.clients(query)
                elif url.path in {'/api/retail-client-explanation','/api/retail-client-explanation-report'}:
                    result=service.retail_cohort_explanation_views.report(query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-client-explanation.json',head=head)
                        return
                elif url.path in {'/api/retail-explanation', '/api/retail-explanation-report'}:
                    result=service.retail_explanation_views.report(query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-retail-explanation.json',head=head)
                        return
                elif url.path in {'/api/retail-subgroup','/api/retail-subgroup-report'}:
                    result=service.retail_subgroup_views.report(query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-retail-subgroups.json',head=head)
                        return
                elif url.path in {'/api/retail-policy','/api/retail-policy-report','/api/retail-policy-preview'}:
                    result=service.retail_policy_views.preview(query) if url.path.endswith('-preview') else service.retail_policy_views.report(query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-retail-policy.json',head=head)
                        return
                elif url.path == "/api/bank-views":
                    if query:
                        raise ValueError('Bank catalog has no filters')
                    result = service.bank_views.catalog()
                elif url.path == '/api/hmda-views':
                    if query: raise ValueError('HMDA catalog has no filters')
                    result = service.hmda_views.catalog()
                elif url.path == '/api/hmda-references':
                    if set(query) != {'source_id'}: raise ValueError('Reference catalog accepts source_id only')
                    result = service.hmda_reference_views.catalog(query['source_id'])
                elif url.path == '/api/hmda-cohorts':
                    if set(query) != {'case_id'}: raise ValueError('Cohort catalog accepts case_id only')
                    result = service.hmda_cohort_views.catalog(query['case_id'])
                elif url.path in {'/api/observed-loss-details','/api/observed-loss-details-report'}:
                    from .observed_loss_details import report
                    result=report(service,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-observed-loss-details.json',head=head)
                        return
                elif url.path in {'/api/mortgage-provenance','/api/mortgage-provenance-report'}:
                    from .mortgage_provenance import report
                    result=report(service,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-mortgage-provenance.json',head=head)
                        return
                elif url.path in {'/api/fannie-samples','/api/fannie-samples-report'}:
                    from .fannie_samples import report
                    result=report(service.root,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-Fannie-samples.json',head=head)
                        return
                elif url.path == '/api/affordability-excel-template':
                    if query: raise ValueError('Affordability template has no filters')
                    from .affordability_excel import template_bytes
                    self.send(200,template_bytes(service.root),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='CreditAtlas-Affordability-Input.xlsx',head=head)
                    return
                elif url.path == '/api/exposure-excel-template':
                    if query: raise ValueError('Excel template has no filters')
                    self.send(200,service.excel_workbench.template(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='CreditAtlas-Portfolio-Input.xlsx',head=head)
                    return
                elif url.path == '/api/exposure-excel-report':
                    self.send(200,service.excel_workbench.report(query),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='CreditAtlas-Portfolio-Review.xlsx',head=head)
                    return
                elif url.path == '/api/exposure-convergence-studies':
                    if set(query)!={'source_import_id'}: raise ValueError('Convergence catalog requires source')
                    result=service.exposure_convergence_views.catalog(query['source_import_id'])
                elif url.path in {'/api/exposure-convergence','/api/exposure-convergence-report'}:
                    result=service.exposure_convergence_views.report(query)
                    if url.path=='/api/exposure-convergence-report':
                        self.send(200,result,filename=f"CreditAtlas-{result['convergence_id']}-private.json",head=head)
                        return
                elif url.path == '/api/portfolio-reviews':
                    if set(query)!={'source_import_id'}: raise ValueError('Review catalog requires source')
                    result=service.portfolio_reviews.list(query['source_import_id'])
                elif url.path in {'/api/portfolio-review','/api/portfolio-review-report'}:
                    if set(query)-{'source_import_id','id','revision'} or not {'source_import_id','id'}<=set(query): raise ValueError('Review requires bound source/id')
                    result=service.portfolio_reviews.report(query['source_import_id'],query['id'],int(query['revision']) if 'revision' in query else None)
                    if url.path=='/api/portfolio-review-report':
                        self.send(200,result,filename=f"CreditAtlas-{result['id']}-revision-{result['revision']}-private.json",head=head)
                        return
                elif url.path == '/api/exposure-tail-studies':
                    if set(query) != {'source_import_id'}: raise ValueError('Tail catalog requires source_import_id only')
                    result = service.exposure_tail_views.catalog(query['source_import_id'])
                elif url.path in {'/api/exposure-tail', '/api/exposure-tail-report'}:
                    result = service.exposure_tail_views.report(query)
                    if url.path == '/api/exposure-tail-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['tail_id']}-private-tail-research.json", head=head)
                        return
                elif url.path == '/api/exposure-ecl-studies':
                    if set(query) != {'source_import_id'}: raise ValueError('ECL catalog requires source_import_id only')
                    result = service.exposure_ecl_views.catalog(query['source_import_id'])
                elif url.path in {'/api/exposure-ecl', '/api/exposure-ecl-report'}:
                    result = service.exposure_ecl_views.report(query)
                    if url.path == '/api/exposure-ecl-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['ecl_id']}-private-research-cash-shortfalls.json", head=head)
                        return
                elif url.path == '/api/exposure-scenarios':
                    if set(query) != {'source_import_id'}: raise ValueError('Scenario catalog requires source_import_id only')
                    result = service.exposure_scenario_views.catalog(query['source_import_id'])
                elif url.path in {'/api/exposure-scenario', '/api/exposure-scenario-report'}:
                    result = service.exposure_scenario_views.report(query)
                    if url.path == '/api/exposure-scenario-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['scenario_id']}-private-declared-scenarios.json", head=head)
                        return
                elif url.path == '/api/exposure-movements':
                    if set(query) != {'closing_import_id'}: raise ValueError('Bridge catalog requires closing_import_id only')
                    result = service.exposure_movement_views.catalog(query['closing_import_id'])
                elif url.path in {'/api/exposure-movement', '/api/exposure-movement-report'}:
                    result = service.exposure_movement_views.report(query)
                    if url.path == '/api/exposure-movement-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['movement_id']}-private-observation-bridge.json", head=head)
                        return
                elif url.path == '/api/exposure-imports':
                    if query: raise ValueError('Exposure catalog accepts no filters')
                    result = service.exposure_views.catalog()
                elif url.path in {'/api/exposure-aggregates', '/api/exposure-report'}:
                    result = service.exposure_views.report(query)
                    if url.path == '/api/exposure-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['import_id']}-private-exposure-aggregates.json", head=head)
                        return
                elif url.path in {'/api/hmda-cohort', '/api/hmda-cohort-report'}:
                    result = service.hmda_cohort_views.report(query)
                    if url.path == '/api/hmda-cohort-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['cohort_id']}-private-cohort-comparison.json", head=head)
                        return
                elif url.path == '/api/hmda-reference':
                    if set(query) != {'reference_id', 'source_id'}: raise ValueError('Reference accepts exact source/reference IDs')
                    result = service.hmda_reference_views.reference(query['reference_id'], query['source_id'])
                elif url.path in {'/api/hmda-labeled-aggregates', '/api/hmda-labeled-report'}:
                    if 'reference_id' not in query: raise ValueError('Explicit reference_id required')
                    result = service.hmda_reference_views.report(query['reference_id'], query)
                    if url.path == '/api/hmda-labeled-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['case_id']}-private-hmda-labeled-aggregates.json", head=head)
                        return
                elif url.path in {'/api/hmda-view', '/api/hmda-aggregates', '/api/hmda-report'}:
                    if url.path == '/api/hmda-view':
                        if set(query) != {'view_id'}: raise ValueError('HMDA snapshot accepts only view_id')
                        result = service.hmda_views.view(query['view_id'])
                    else:
                        result = service.hmda_views.report(query.get('view_id', ''), query)
                        if url.path == '/api/hmda-report':
                            self.send(200, result, filename=f"CreditAtlas-{result['case_id']}-private-hmda-aggregates.json", head=head)
                            return
                elif url.path == '/api/abs-views':
                    if query:
                        raise ValueError('ABS catalog has no filters')
                    result = service.abs_views.catalog()
                elif url.path in {'/api/abs-view', '/api/abs-period', '/api/abs-report'}:
                    if url.path == '/api/abs-view':
                        if set(query) != {'view_id'}:
                            raise ValueError('ABS snapshot accepts only view_id')
                        result = service.abs_views.view(query['view_id'])
                    else:
                        result = service.abs_views.report(query.get('view_id', ''), query)
                        if url.path == '/api/abs-report':
                            self.send(200, result, filename=f"CreditAtlas-{result['waterfall_id']}-private-abs-period.json", head=head)
                            return
                elif url.path == '/api/sec-views':
                    if query:
                        raise ValueError('SEC catalog has no filters')
                    result = service.sec_views.catalog()
                elif url.path in {'/api/sec-coverage','/api/sec-coverage-report'}:
                    from .sec_coverage import report as sec_coverage_report
                    result=sec_coverage_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-SEC-coverage.json',head=head)
                        return
                elif url.path in {'/api/sec-note-rules','/api/sec-note-rules-report'}:
                    from .note_rules import report as note_rules_report
                    result=note_rules_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-note-rules.json',head=head)
                        return
                elif url.path in {'/api/sec-note-schedule','/api/sec-note-schedule-report'}:
                    from .note_schedules import report as note_schedule_report
                    result=note_schedule_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-note-schedule.json',head=head)
                        return
                elif url.path in {'/api/sec-facilities','/api/sec-facilities-report'}:
                    from .facilities import report as facility_report
                    result=facility_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-facilities.json',head=head)
                        return
                elif url.path in {'/api/sec-events','/api/sec-events-report'}:
                    from .sec_events import report as sec_events_report
                    result=sec_events_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-SEC-filings.json',head=head)
                        return
                elif url.path in {'/api/sec-annual-debt-bridge','/api/sec-annual-debt-bridge-report'}:
                    from .annual_debt_bridge import report as annual_debt_bridge_report
                    result=annual_debt_bridge_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-annual-debt-bridge.json',head=head)
                        return
                elif url.path in {'/api/sec-debt','/api/sec-debt-report'}:
                    from .sec_debt import report as sec_debt_report
                    result=sec_debt_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-SEC-maturities.json',head=head)
                        return
                elif url.path in {'/api/sec-trend', '/api/sec-trend-report'}:
                    from .sec_trends import report as sec_trend_report
                    result=sec_trend_report(service.sec_views,query.get('view_id',''),query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-SEC-trend.json',head=head)
                        return
                elif url.path in {'/api/sec-view', '/api/sec-report'}:
                    if url.path == '/api/sec-view':
                        if set(query) != {'view_id'}:
                            raise ValueError('SEC snapshot accepts only view_id')
                        result = service.sec_views.view(query['view_id'])
                    else:
                        result = service.sec_views.report(query.get('view_id', ''), query)
                        self.send(200, result, filename=f"CreditAtlas-{result['case_id']}-private-issuer-report.json", head=head)
                        return
                elif url.path in {'/api/utility-debt-service','/api/utility-debt-service-report'}:
                    from .utility_debt_service import report as utility_debt_report
                    result=utility_debt_report(service.root,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-utility-debt-service.json',head=head)
                        return
                elif url.path in {'/api/sovereign-defaults','/api/sovereign-defaults-report'}:
                    from .sovereign_defaults import report as sovereign_defaults_report
                    result=sovereign_defaults_report(service.root,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-sovereign-defaults.json',head=head)
                        return
                elif url.path == '/api/country-views':
                    if query:
                        raise ValueError('Country catalog has no filters')
                    result = service.country_views.catalog()
                elif url.path in {'/api/country-view', '/api/country-report'}:
                    if url.path == '/api/country-view':
                        if set(query) != {'view_id'}:
                            raise ValueError('Country snapshot accepts only view_id')
                        result = service.country_views.view(query['view_id'])
                    else:
                        result = service.country_views.report(query.get('view_id', ''), query)
                        self.send(200, result, filename=f"CreditAtlas-{result['case_id']}-private-country-report.json", head=head)
                        return
                elif url.path == '/api/bankruptcy-model-views':
                    if query:
                        raise ValueError('Model aggregate catalog has no filters')
                    result = service.bankruptcy_model_views.catalog()
                elif url.path in {'/api/bankruptcy-model-view', '/api/bankruptcy-model-report'}:
                    if set(query) != {'view_id'}:
                        raise ValueError('Model aggregate accepts only view_id; no inference/score filters')
                    result = service.bankruptcy_model_views.view(query['view_id'])
                    if url.path == '/api/bankruptcy-model-report':
                        self.send(200, result, filename=f"CreditAtlas-{result['evaluation_id']}-private-model-aggregates.json", head=head)
                        return
                elif url.path == '/api/bankruptcy-views':
                    if query:
                        raise ValueError('Bankruptcy catalog has no filters')
                    result = service.bankruptcy_views.catalog()
                elif url.path in {'/api/bankruptcy-view', '/api/bankruptcy-report'}:
                    if url.path == '/api/bankruptcy-view':
                        if set(query) != {'view_id'}:
                            raise ValueError('Bankruptcy snapshot accepts only view_id')
                        result = service.bankruptcy_views.view(query['view_id'])
                    else:
                        result = service.bankruptcy_views.report(query.get('view_id', ''), query)
                        self.send(200, result, filename=f"CreditAtlas-{result['case_id']}-private-bankruptcy-ratios.json", head=head)
                        return
                elif url.path == '/api/market-views':
                    if query:
                        raise ValueError('Market catalog has no filters')
                    result = service.market_views.catalog()
                elif url.path in {'/api/market-view', '/api/market-report', '/api/market-daily', '/api/bond-scenario', '/api/bond-report'}:
                    identifier = query.get('view_id', '')
                    if url.path == '/api/market-view':
                        if set(query) != {'view_id'}:
                            raise ValueError('Market snapshot accepts only view_id')
                        result = service.market_views.view(identifier)
                    elif url.path == '/api/market-daily':
                        result = service.market_views.daily(identifier, query)
                    elif url.path in {'/api/bond-scenario', '/api/bond-report'}:
                        result = service.market_views.bond(identifier, query)
                        if url.path == '/api/bond-report':
                            self.send(200, result, filename=f"CreditAtlas-{identifier}-private-bond-scenario.json", head=head)
                            return
                    else:
                        result = service.market_views.report(identifier, query)
                        self.send(200, result, filename=f"CreditAtlas-{identifier}-private-market-series.json", head=head)
                        return
                elif url.path in {"/api/bank-view", "/api/bank-report", "/api/bank-timeline"}:
                    from .bank_views import bank_report
                    if url.path == '/api/bank-timeline':
                        if set(query) != {'view_id', 'cert'}:
                            raise ValueError('Bank timeline accepts only snapshot and certificate')
                        result = service.bank_views.timeline(query['view_id'], query['cert'])
                    else:
                        if url.path == '/api/bank-view' and set(query) != {'view_id'}:
                            raise ValueError('Bank snapshot accepts only view_id')
                        result = service.bank_views.view(query.get('view_id', ''))
                        if url.path == '/api/bank-report':
                            result = bank_report(result, query)
                            self.send(200, result, filename=f"CreditAtlas-{result['panel_id']}-private-bank-aggregates.json", head=head)
                            return
                elif url.path in {'/api/business-archive', '/api/business-archive-report'}:
                    from .business_archive import view_report
                    result = view_report(service.suite_views, query)
                    if url.path.endswith('-report'):
                        self.send(200, result, filename='CreditAtlas-private-SBA-2026-03-31-archive.json', head=head)
                        return
                elif url.path == "/api/business-report":
                    from .suite_snapshot import business_report
                    result = business_report(service.suite_views.view(query.get("view_id", "")), query)
                    self.send(200, result, filename=f"CreditAtlas-{result['business_id']}-private-business-aggregates.json", head=head)
                    return
                elif url.path in {'/api/lendingclub-full-source','/api/lendingclub-full-source-report'}:
                    from .lendingclub_full_source import report as lendingclub_full_report
                    result=lendingclub_full_report(service.root,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-LendingClub-full-source.json',head=head)
                        return
                elif url.path in {'/api/lendingclub-source','/api/lendingclub-source-report'}:
                    from .lendingclub_source import report as lendingclub_report
                    result=lendingclub_report(service.root,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-LendingClub-source.json',head=head)
                        return
                elif url.path in {"/api/retail-source-quality", "/api/retail-source-quality-report"}:
                    from .retail_source_quality import report as retail_quality_report
                    result = retail_quality_report(service.suite_views, query.get("view_id", ""), query)
                    if url.path.endswith('-report'):
                        self.send(200, result, filename='CreditAtlas-private-retail-source-quality.json', head=head)
                        return
                elif url.path in {"/api/absee-dictionary", "/api/absee-dictionary-report"}:
                    from .absee_dictionary import report as dictionary_report
                    result = dictionary_report(service.root, query)
                    if url.path.endswith('-report'):
                        self.send(200, result, filename='CreditAtlas-private-absee-field-definitions.json', head=head)
                        return
                elif url.path in {"/api/absee-profile", "/api/absee-profile-report"}:
                    from .absee_profile import saved_report
                    result = saved_report(service.root, query)
                    if url.path.endswith('-report'):
                        self.send(200, result, filename='CreditAtlas-private-absee-mirror-profile.json', head=head)
                        return
                elif url.path in {"/api/managed-pool", "/api/managed-pool-report"}:
                    from .managed_pool import report as managed_pool_report
                    result = managed_pool_report(service.root, query)
                    if url.path.endswith('-report'):
                        self.send(200, result, filename='CreditAtlas-private-managed-pool.json', head=head)
                        return
                elif url.path in {"/api/pool-history", "/api/pool-history-report"}:
                    from .pool_history import report as pool_history_report
                    result = pool_history_report(service.root, query)
                    if url.path.endswith('-report'):
                        self.send(200, result, filename='CreditAtlas-private-pool-history.json', head=head)
                        return
                elif url.path in {"/api/abs-benchmark", "/api/abs-benchmark-report"}:
                    from .abs_benchmark import report as abs_benchmark_report
                    result = abs_benchmark_report(service.abs_views, query.get("view_id", ""), query)
                    if url.path.endswith('-report'):
                        self.send(200, result, filename='CreditAtlas-private-ABS-benchmark.json', head=head)
                        return
                elif url.path in {"/api/suite-view", "/api/suite-report"}:
                    result = service.suite_views.view(query.get("view_id", ""))
                    if url.path == "/api/suite-report":
                        self.send(200, result, filename=f"CreditAtlas-{result['view_id']}-private-aggregates.json", head=head)
                        return
                elif url.path == "/api/runs":
                    result = service.runs()
                elif url.path == "/api/snapshot":
                    result = service.snapshot(run)
                elif url.path == "/api/evidence":
                    result = service.evidence(run)
                elif url.path == "/api/monitoring":
                    result = service.monitoring(run)
                elif url.path in {"/api/fhfa-nmdb-performance", "/api/fhfa-nmdb-performance-report"}:
                    result = service.fhfa_nmdb_performance()
                    if url.path.endswith("-report"):
                        self.send(200, result, filename="FHFA-NMDB-public-aggregate-performance.json", head=head)
                        return
                elif url.path in {"/api/cfpb-mortgage-trends", "/api/cfpb-mortgage-trends-report"}:
                    result = service.cfpb_mortgage_trends(query)
                    if url.path.endswith("-report"):
                        self.send(200, result, filename="CFPB-Mortgage-Performance-Trends-private-context.json", head=head)
                        return
                elif url.path in {"/api/fhfa-pudb-profile", "/api/fhfa-pudb-profile-report"}:
                    if query:
                        raise ValueError("FHFA PUDB profile accepts no filters")
                    result = service.fhfa_pudb_profile()
                    if url.path.endswith("-report"):
                        self.send(200, result, filename="FHFA-Enterprise-PUDB-2025-private-acquisition-profile.json", head=head)
                        return
                elif url.path in {"/api/hud-fha-iif-profile", "/api/hud-fha-iif-profile-report"}:
                    if query:
                        raise ValueError("HUD FHA tract profile accepts no filters")
                    result = service.hud_fha_iif_profile()
                    if url.path.endswith("-report"):
                        self.send(200, result, filename="HUD-FHA-private-insurance-in-force-tract-profile.json", head=head)
                        return
                elif url.path == "/api/studies":
                    result = service.studies(run)
                elif url.path == "/api/episode-followup":
                    result = service.episode_followup(run)
                elif url.path == "/api/period-transitions":
                    result = service.period_transitions(run)
                elif url.path == "/api/report":
                    result = service.report(run, query)
                    self.send(200, result, filename=f"CreditAtlas-{run}-private-report.json", head=head)
                    return
                elif url.path == "/api/loans":
                    result = service.loans(run, query)
                elif url.path == "/api/timeline":
                    result = service.timeline(run, query.get("loan_key", ""))
                elif url.path == "/api/findings":
                    service.case(run)
                    result = {"case_id": run, "findings": service.reviews.list(run)}
                elif url.path in {'/api/retail-dossier','/api/retail-dossier-report'}:
                    from .retail_dossier import report
                    result=report(service.suite_views,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-retail-model-dossier.json',head=head)
                        return
                elif url.path in {'/api/retail-data-contract','/api/retail-data-contract-report'}:
                    from .retail_data_contract import report
                    result=report(service.suite_views,query)
                    if url.path.endswith('-report'):
                        self.send(200,result,filename='CreditAtlas-private-retail-data-contract.json',head=head)
                        return
                elif url.path == '/api/finding-report':
                    from .finding_reports import report
                    result=report(service,query)
                    self.send(200,result,filename='CreditAtlas-private-finding-review.json',head=head)
                    return
                elif url.path == "/api/finding-history":
                    service.case(run)
                    result = {"case_id": run, "history": service.reviews.history(run, query.get("id", ""))}
                else:
                    self.send(404, {"error": "Route not found"}, head=head)
                    return
                self.send(200, result, head=head)
            except KeyError:
                self.send(404, {"error": "Case or research record not found"}, head=head)
            except EvidenceChanged:
                self.send(503, {"error": "Frozen evidence or serving code changed; verify artifacts and restart with reviewed code"}, head=head)
            except (ValueError, TypeError):
                self.send(400, {"error": "Invalid request or evidence contract"}, head=head)
            except Exception:
                self.send(503, {"error": "Research evidence is unavailable; inspect the local run receipt"}, head=head)

        def do_POST(self):
            if not self.allowed(mutation=True):
                self.send(403, {"error": "Same-origin local research client required"})
                return
            try:
                if self.path not in {"/api/findings", "/api/corporate-memos", "/api/sec-workbook", "/api/sec-debt-workbook", "/api/monitor-reviews", "/api/kpi-workbook", "/api/portfolio-reviews", "/api/exposure-excel-import", "/api/retail-policies", "/api/retail-subgroups", "/api/affordability-assess", "/api/affordability-report", "/api/affordability-excel-import"}:
                    self.send(404, {"error": "Route not found"})
                    return
                if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                    self.send(415, {"error": "JSON content type required"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                max_body=28*1024**2 if self.path=="/api/exposure-excel-import" else 3*1024**2 if self.path=="/api/affordability-excel-import" else 2*1024**2 if self.path=="/api/kpi-workbook" else 65536
                if not 0 < length <= max_body:
                    self.send(413, {"error": "Finding request exceeds allowed size"})
                    return
                raw_body = self.rfile.read(length)
                self._body_read = True
                payload = json.loads(raw_body)
                if not isinstance(payload, dict):
                    raise ValueError("Object required")
                if self.path == '/api/affordability-excel-import':
                    from .affordability_excel import import_upload
                    self.send(200, import_upload(payload))
                    return
                if self.path in {'/api/affordability-assess','/api/affordability-report'}:
                    from .affordability import assess
                    result=assess(payload)
                    self.send(200,result,filename='CreditAtlas-private-affordability.json' if self.path.endswith('-report') else None)
                    return
                if self.path=='/api/corporate-memos':
                    self.send(200 if payload.get('id') else 201,corporate_memos.save(payload))
                    return
                if self.path=='/api/kpi-workbook':
                    from .kpi_workbook import export_workbook
                    content=export_workbook(service,monitor_reviews,payload)
                    self.send(200,content,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='CreditAtlas-KPI.xlsx')
                    return
                if self.path=='/api/sec-workbook':
                    from .sec_workbook import export_workbook
                    content=export_workbook(service,payload)
                    self.send(200,content,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='CreditAtlas-SEC.xlsx')
                    return
                if self.path=='/api/sec-debt-workbook':
                    from .sec_debt_workbook import export_workbook
                    content=export_workbook(service,payload)
                    self.send(200,content,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='CreditAtlas-Maturities.xlsx')
                    return
                if self.path=='/api/monitor-reviews':
                    record=monitor_reviews.save(payload)
                    self.send(200 if payload.get('id') else 201,record)
                    return
                if self.path=="/api/exposure-excel-import":
                    self.send(201,service.excel_workbench.upload(payload))
                    return
                if self.path=="/api/retail-policies":
                    self.send(201,service.retail_policy_views.save(payload))
                    return
                if self.path=="/api/retail-subgroups":
                    self.send(201,service.retail_subgroup_views.save(payload))
                    return
                if self.path=="/api/portfolio-reviews":
                    record=service.portfolio_reviews.save(payload)
                    self.send(200 if payload.get('id') else 201,record)
                    return
                case_id = payload.get("case_id", "")
                service.case(case_id)
                selected = payload.get("filters", {})
                if not isinstance(selected, dict):
                    raise ValueError("Invalid filter context")
                canonical = filters_from({k: str(v) for k, v in selected.items()})
                if selected.get("loan_key"):
                    token = selected["loan_key"]
                    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
                        raise ValueError("Invalid private loan-key context")
                    if service.loans(case_id, {"q": token, "limit": "1"})["total_matching"] != 1:
                        raise KeyError("Private loan context does not belong to this run")
                    canonical["loan_key"] = token
                if set(selected) - {"segment", "basis", "horizon", "from", "to", "loan_key", "transition_year"}:
                    raise ValueError("Unknown filter context")
                payload["filters"] = canonical
                record = service.reviews.save(case_id, payload, payload.get("id"))
                self.send(200 if payload.get("id") else 201, record)
            except ReviewConflict:
                self.send(409, {"error": "Finding changed; reload its latest revision before editing"})
            except KeyError:
                self.send(404, {"error": "Case or finding not found"})
            except EvidenceChanged:
                self.send(503, {"error": "Frozen evidence changed; finding was not saved"})
            except (ValueError, TypeError) as error:
                if self.path in {'/api/affordability-assess','/api/affordability-report','/api/affordability-excel-import'}:
                    self.send(400,{'error':'Invalid affordability intake;use explicit amounts,periods,scope,coverage and policy references'})
                elif self.path == '/api/exposure-excel-import':
                    # Expose only fixed validation messages, never arbitrary exception text.
                    messages = {
                        'Numeric Excel cells support up to 15 significant digits; use text for exact larger amounts/IDs',
                        'Input formulas must be replaced with explicit values; cached formula values are not trusted',
                        'XLSX file must be at most 20MB',
                        'Input row bound exceeded',
                        'Use InputPositions and InputControl sheets from the template',
                    }
                    message = str(error)
                    self.send(400, {'error': message if message in messages else
                        'Invalid Excel workbook; use the InputPositions/InputControl template and explicit values'})
                else:
                    self.send(400, {"error": "Invalid research finding"})
            except Exception:
                self.send(503, {"error": "Research finding could not be saved"})

    return Handler


class LocalResearchServer(ThreadingHTTPServer):
    # Browsers fetch scripts, styles and nine banner images concurrently.
    request_queue_size = 64


def serve(root: Path, port: int = 8770):
    if root.resolve().drive.upper() != "D:":
        raise ValueError("CreditAtlas private storage must remain on D:")
    service = ResearchService(root)
    # Warm verification before opening the listener. No raw data in browser bundles.
    service.runs()
    with LocalResearchServer(("127.0.0.1", port), handler_for(service)) as server:
        server.daemon_threads = True
        print(f"CreditAtlas P2/D01 · local private research · http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()
