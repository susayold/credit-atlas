"""Promote only original P3.04 after current saved evidence audit."""
from pathlib import Path
import xml.etree.ElementTree as ET
from credit_atlas.workspace import read_json, sha256, write_new
import json

ROOT = Path(__file__).resolve().parents[1]
paths = {
 'lineage':'artifacts/private/bankruptcy-frozen-lineage-audit-907872a3548a/receipt.json',
 'numerical':'artifacts/private/bankruptcy-saved-metrics-audit-0c01be07f13b/receipt.json',
 'browser':'artifacts/private/bankruptcy-model-browser-qa-390102285f73/receipt.json',
 'tests':'artifacts/private/bankruptcy-model-acceptance-tests.xml',
 'model_card':'docs/BANKRUPTCY_FINAL_MODEL_CARD.md',
 'document':'docs/P3_BANKRUPTCY_BENCHMARK_ACCEPTANCE_VI.md',
}
for role, method in [('lineage','audit_bankruptcy_frozen_lineage.py'),('numerical','audit_bankruptcy_saved_metrics.py')]:
    receipt = read_json(ROOT/paths[role]);assert receipt['status']=='PASS'
    assert receipt['method_sha256']==sha256(ROOT/'scripts'/method)
    assert all(sha256(ROOT/p)==h for p,h in receipt['inputs_sha256'].items())
    assert all(sha256(ROOT/p)==h for p,h in receipt['ledger_sha256_unchanged'].items())
    assert not receipt['final_predictor_reads'] and not receipt['model_inference']
numerical=read_json(ROOT/paths['numerical'])
assert numerical['validation_candidates']==5 and numerical['validation_score_rows']==4435
assert numerical['final_score_rows']==591 and numerical['metric_draw_cells_checked']==24000
assert numerical['paired_point_and_percentile_cells_checked']==180
browser=read_json(ROOT/paths['browser']);assert browser['status']=='PASS' and len(browser['checks'])==8 and not browser['browser_errors']
folder=(ROOT/paths['browser']).parent;export=read_json(folder/'model-export.json')
assert not export['can_rescore'] and not export['production_qualified'] and not export['temporal_out_of_time']
for key,value in numerical['final_metrics'].items():assert abs(value-export['final'][key])<2e-12
assert export['candidate']=='boosting_platt' and export['horizon_years']==1
visual_path=folder/'visual-review.json'
visual={'status':'PASS','scope':'Actual saved model desktop/mobile full-page images viewed directly',
        'pngs':{p.name:sha256(p) for p in folder.glob('*.png')},'browser_receipt_sha256':sha256(folder/'receipt.json')}
assert len(visual['pngs'])==2
if visual_path.exists():assert read_json(visual_path)==visual
else:write_new(visual_path,visual)
paths['visual']=str(visual_path.relative_to(ROOT));paths['export']=str((folder/'model-export.json').relative_to(ROOT))
suite=ET.parse(ROOT/paths['tests']).getroot().find('testsuite')
assert suite.attrib['tests']=='36' and suite.attrib['errors']==suite.attrib['failures']=='0'
card=' '.join((ROOT/paths['model_card']).read_text(encoding='utf-8').split())
assert all(anchor in card for anchor in ['0,962793792','0,863689087','0,021610995','0,087159890','591','41','Not yet supported:', 'production loan-default qualification remain unproven'])
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';ledger=read_json(path)
original=[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in ledger['requirements']]
r=next(r for r in ledger['requirements'] if r['id']=='P3.04')
entry={'checkpoint':'p3-bankruptcy-benchmark-full-current-requirement',**paths,
       'scope':'Original UCI365 one-year source-statement benchmark; frozen source/split/selection/ledger graph, five validation candidates and one saved final, independent 24000 bootstrap metric cells/180 paired interval cells, actual aggregate UI/export and model card. No new final predictor reads, refit or inference; entity/OOT/production qualification remains false.',
       'evidence_sha256':{p:sha256(ROOT/p) for p in paths.values()},'full_completion_proven':True,
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md')}
if not any(e.get('checkpoint')==entry['checkpoint'] for e in r['completion_evidence']):r['completion_evidence'].append(entry)
r['full_completion_proven']=True
assert original==[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in ledger['requirements']]
path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Accepted:',sum(bool(r['full_completion_proven']) for r in ledger['requirements']),'/50')
