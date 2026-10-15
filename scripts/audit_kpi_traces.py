import json,urllib.request,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
root=Path.cwd();out=root/'artifacts/private'/('kpi-trace-qa-'+uuid.uuid4().hex[:12]);out.mkdir();report=json.loads((root/'artifacts/private/kpi-inspector-qa-9479d922c579/monitor.json').read_text());suite=json.load(urllib.request.urlopen('http://127.0.0.1:8770/api/suite-view?view_id=suite-view-74e07524f6d0'));mortgage=json.load(urllib.request.urlopen('http://127.0.0.1:8770/api/snapshot?run=d01-a24484b21a21'));sources={**report['data'],**report.get('trace_sources',{}),'suite':suite,'mortgage':mortgage};checks=[];total=0;derived=0
for d,r in report['kpi_analysis'].items():
 assert r['input_trace_coverage']['mapped']==len(r['metrics']) and r['input_trace_coverage']['arithmetic_mismatches']==0
 for m in r['metrics']:
  detail=r['metric_details'][m['name']];total+=1;derived+=detail['trace_kind']=='derived'
  for x in detail['inputs']:
   if x['source_path'] is None:assert x['value_exact'] is None;continue
   v=sources[x['source']]
   for k in x['source_path'].split('/')[1:]:
    k=k.replace('~1','/').replace('~0','~')
    try:v=v[int(k)] if isinstance(v,list) else v[k]
    except Exception:print(d,m['name'],x);raise
   assert x['value_exact']==(None if v is None else str(v))
  if m['value'] is not None:assert detail['source_check'] in ['ARITHMETIC_MATCH','SUPPLIED_AGGREGATE']
 checks.append(d+': all metric source pointers match original API values; every supported derived value reconciles')
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page();page.goto('http://127.0.0.1:8770/?view=monitor');expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
 boundary=page.evaluate('''({payloads,suite,mortgage,options})=>{
 const run=(change)=>{const p=structuredClone(payloads);change(p);return buildKpiReadouts(p,suite,mortgage,options);};
 const policy=run(p=>{p.P1.policy=null}),replay=run(p=>{p.P5.period_report=null}),transitions=run(p=>{p.P2.migration=null;p.P2.followup=null}),issuer=run(p=>{p.P3.issuers=p.P3.issuers.filter(x=>x.filters.cik!=='0000320193');});
 return {policy:policy.P1.metrics.slice(9).every(m=>m.value==null)&&policy.P1.input_trace_coverage.arithmetic_mismatches===0,replay:replay.P5.metrics.slice(9).every(m=>m.value==null)&&replay.P5.input_trace_coverage.arithmetic_mismatches===0,transition:transitions.P2.metrics.filter(m=>m.name.includes('adjacent share')||m.name.includes('follow-up share')).every(m=>m.value==null),issuer:issuer.P3.metrics.filter(m=>m.name.startsWith('AAPL')).every(m=>m.value==null),schema:policy.P1.metrics.every(m=>Object.keys(m).length===6)};
}''',{'payloads':{**report['data'],'P2':{**report['data']['P2'],'monthly':mortgage['snapshot']['monthly']}},'suite':suite,'mortgage':mortgage,'options':report['filters']});assert all(boundary.values()),boundary;checks.append('Policy/replay/transition/followup/issuer missing sources preserve unavailable and original metric schema');b.close()
assert total==88;result={'status':'PASS','mapped_metrics':total,'derived':derived,'checks':checks,'boundary':boundary};(out/'receipt.json').write_text(json.dumps(result,indent=2));print(out);print(json.dumps(result))
