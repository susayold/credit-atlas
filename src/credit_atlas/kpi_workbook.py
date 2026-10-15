"""Bounded private KPI workbook export with source capture and saved reviews."""
import json
import os
from pathlib import Path
import subprocess
import uuid


def validate_report(report):
    if not isinstance(report, dict) or set(report) != {'schema_version', 'read_at', 'filters', 'kpi_analysis'}:
        raise ValueError('Invalid KPI report fields')
    if report['schema_version'] != 1 or not isinstance(report['read_at'], str) or len(report['read_at']) > 60:
        raise ValueError('Invalid KPI report version/date')
    filters = report['filters']
    if not isinstance(filters, dict) or filters.get('domain') not in {'all', 'P1', 'P2', 'P3', 'P4', 'P5'}:
        raise ValueError('Invalid KPI report scope')
    domains = report['kpi_analysis']
    if not isinstance(domains, dict) or not domains or set(domains)-{'P1', 'P2', 'P3', 'P4', 'P5'}:
        raise ValueError('Invalid KPI domains')
    if filters['domain'] != 'all' and set(domains) != {filters['domain']}:
        raise ValueError('KPI domain filter mismatch')
    # Reject non-finite values, excessive recursive structures and text sizes.
    encoded = json.dumps(report, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode('utf-8')) > 2*1024**2:
        raise ValueError('KPI report exceeds limit')
    def bounded(v, depth=0):
        if depth > 14 or isinstance(v, str) and len(v) > 12000:
            raise ValueError('Oversize KPI value')
        if isinstance(v, (dict, list)):
            if len(v) > 3000:
                raise ValueError('Oversize KPI collection')
            for item in (v.values() if isinstance(v, dict) else v):
                bounded(item, depth+1)
    bounded(report)
    for d, r in domains.items():
        if not isinstance(r, dict) or not isinstance(r.get('title'), str) or not isinstance(r.get('scope'), str):
            raise ValueError('Invalid KPI readout')
        q = r.get('data_quality')
        snap = r.get('review_snapshot')
        if not isinstance(q, dict) or not isinstance(snap, dict) or snap.get('domain') != d:
            raise ValueError('Missing source-bound KPI context')
        if any(snap.get(k) != value for k, value in [('scope',r['scope']), ('metrics',r.get('metrics')), ('quality_metrics',q.get('metrics')), ('filters',filters)]):
            raise ValueError('KPI capture mismatch')
        for m in r['metrics']+q['metrics']:
            if set(m) != {'name','value','unit','formula','interpretation','comparison'} or m['unit'] not in {'count','share','USD','decimal','declared_cost_units'}:
                raise ValueError('Invalid KPI metric')
            if any(not isinstance(m[k], str) for k in ['name','formula','interpretation']):
                raise ValueError('Invalid KPI text')
            if m['value'] is not None and (isinstance(m['value'], bool) or not isinstance(m['value'], (int,float))):
                raise ValueError('Invalid KPI actual')
            c=m['comparison']
            if c is not None and (not isinstance(c,dict) or set(c)!={'period','value','absolute_change','relative_change','unit'} or c['unit']!=m['unit'] or not isinstance(c['period'],str) or any(isinstance(c[k],bool) or not isinstance(c[k],(int,float)) for k in ['value','absolute_change']) or c['relative_change'] is not None and not isinstance(c['relative_change'],(int,float))):
                raise ValueError('Invalid KPI comparison')
        for t in r.get('tables',[])+q.get('tables',[]):
            if not isinstance(t,dict) or set(t)!={'title','columns','rows'} or not isinstance(t['title'],str) or not 1<=len(t['columns'])<=15 or any(not isinstance(x,str) for x in t['columns']):
                raise ValueError('Invalid source table')
            if any(not isinstance(row,list) or len(row)!=len(t['columns']) or any(not isinstance(x,(str,int,float,bool,type(None))) for x in row) for row in t['rows']):
                raise ValueError('Invalid source table row')
    return report


def export_workbook(service, reviews, report):
    validate_report(report)
    captures=[reviews.capture(r['review_snapshot']) for r in report['kpi_analysis'].values()]
    histories=[reviews.report(r['id']) for d in report['kpi_analysis'] for r in reviews.list(d)['reviews']]
    document={**report, 'source_captures':captures, 'reviews':histories}
    identifier='kpi-workbook-'+uuid.uuid4().hex[:12]
    directory=service.root/'artifacts/private'/identifier
    directory.mkdir()
    input_path=directory/'report.json'
    input_path.write_text(json.dumps(document,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
    default=Path(os.environ.get('LOCALAPPDATA','')).parent/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    # The app can use a configured bundled runtime on other machines.
    node=Path(os.environ.get('CREDIT_ATLAS_NODE',str(default)))
    if not node.is_file():
        node=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    if not node.is_file():
        raise ValueError('Bundled Node runtime unavailable')
    output=directory/'CreditAtlas-KPI.xlsx'
    tmp=service.root/'artifacts/private/tmp'
    tmp.mkdir(exist_ok=True)
    environment={**os.environ,'TEMP':str(tmp),'TMP':str(tmp)}
    subprocess.run([str(node),str(service.root/'scripts/build_kpi_workbook.mjs'),str(input_path),str(output)],cwd=service.root,env=environment,check=True,capture_output=True,timeout=180)
    # No client path or executable is ever accepted.
    return output.read_bytes()
