"""Multi-seed/draw-count diagnostics for a pinned declared tail study."""
import copy
import json
import statistics
import uuid
from pathlib import Path
from . import exposure_tail as tail
from .exposure_movements import guard
from .workspace import contained,read_json,sha256,timestamp,write_new


def methods():
    return {**tail.methods(),'convergence':sha256(Path(__file__))}


def validate(plan):
    if not isinstance(plan,dict) or set(plan)!={'schema_version','tail_id','seeds','draw_counts','visibility','public_release_approved'}:
        raise ValueError('Explicit convergence contract required')
    if type(plan['schema_version']) is not int or plan['schema_version']!=1 or plan['visibility']!='private' or plan['public_release_approved'] is not False:
        raise ValueError('Private convergence contract required')
    seeds=plan['seeds']; counts=plan['draw_counts']
    if not isinstance(seeds,list) or not 2<=len(seeds)<=8 or any(type(s) is not int or not 0<=s<2**63 for s in seeds) or len(set(seeds))!=len(seeds):
        raise ValueError('Two to eight distinct seeds required')
    if not isinstance(counts,list) or not 2<=len(counts)<=4 or any(type(n) is not int or not 128<=n<=65536 for n in counts) or counts!=sorted(set(counts)):
        raise ValueError('Two to four increasing distinct draw counts required')


def source(root,plan):
    validate(plan); folder,receipt,base=tail.verify(root,plan['tail_id'])
    rows,metadata,scenario,pins=tail.inputs(root,base['assumptions'])
    pins.update({str((folder/n).relative_to(root)):d for n,d in receipt['outputs_sha256'].items()})
    pins[str((folder/'tail-complete.json').relative_to(root))]=sha256(folder/'tail-complete.json')
    for n in plan['draw_counts']:
        variant={**base['assumptions'],'draws':n}; tail.parameters(variant,rows,scenario)
    positions=tail.parameters(base['assumptions'],rows,scenario)
    if len(positions)*sum(plan['draw_counts'])*len(plan['seeds'])*len(base['assumptions']['cases'])>2000000000:
        raise ValueError('Aggregate convergence work bound exceeded')
    return base,positions,pins


def calculate(plan,base,positions):
    runs=[]
    for draws in plan['draw_counts']:
        for seed in plan['seeds']:
            variant={**base['assumptions'],'draws':draws,'seed':seed}
            result,_,_=tail.simulate(variant,positions)
            runs.append({'seed':seed,'draws':draws,'results':result['results']})
    diagnostics=[]
    for currency in sorted({r['currency'] for r in positions}):
        for case in base['assumptions']['cases']:
            levels=[]
            for draws in plan['draw_counts']:
                rows=[r for run in runs if run['draws']==draws for r in run['results'] if r['currency']==currency and r['id']==case['id']]
                def summary(values):
                    return {'seed_mean':statistics.mean(values),'seed_sample_sd':statistics.stdev(values),'seed_min':min(values),'seed_max':max(values)}
                levels.append({'draws':draws,'mean_loss':summary([r['mean_loss'] for r in rows]),'tails':[
                    {'alpha':alpha,'tail_mass_per_seed':(1-float(alpha))*draws,
                     'var':summary([next(t['var'] for t in r['tails'] if t['alpha']==alpha) for r in rows]),
                     'es':summary([next(t['es'] for t in r['tails'] if t['alpha']==alpha) for r in rows])}
                    for alpha in base['assumptions']['alphas']]})
            previous,last=levels[-2:]; changes=[]
            for a,b in zip(previous['tails'],last['tails']):
                for metric in ('var','es'):
                    old=a[metric]['seed_mean']; new=b[metric]['seed_mean']
                    changes.append({'alpha':b['alpha'],'metric':metric,'absolute_change':new-old,
                        'relative_change':(new-old)/old if old else None})
            diagnostics.append({'currency':currency,'case_id':case['id'],'levels':levels,'last_two_level_changes':changes})
    return {'source_import_id':base['source_import_id'],'tail_id':plan['tail_id'],'assumptions':plan,'runs':runs,'diagnostics':diagnostics,
        'contract':{'calibrated':False,'statistical_convergence_certified':False,'es_confidence_interval':False,
            'draw_level_independence':False,'cross_currency_total':False,
            'interpretation':'Seed ranges and last-level changes are descriptive diagnostics; few seeds do not certify convergence. Levels within seed share factor prefixes, but idiosyncratic allocation may differ by currency position count.',
            'source_el_available':False},'visibility':'private','public_release_approved':False}


def build(root,relative):
    path=contained(root,relative); digest=sha256(path); plan=read_json(path); frozen=methods()
    base,positions,pins=source(root,plan); report=calculate(plan,base,positions); guard(root,pins)
    if methods()!=frozen or sha256(path)!=digest: raise ValueError('Convergence inputs changed during build')
    identifier='exposure-convergence-'+uuid.uuid4().hex[:12]; folder=contained(root,'artifacts/private/'+identifier); folder.mkdir()
    write_new(folder/'assumptions.json',plan); write_new(folder/'report.json',report)
    receipt={'convergence_id':identifier,'status':'DECLARED_MULTI_SEED_DIAGNOSTICS','methods':frozen,'inputs_sha256':pins,
        'outputs_sha256':{n:sha256(folder/n) for n in ('assumptions.json','report.json')},'completed_at':timestamp(),'visibility':'private','public_release_approved':False}
    guard(root,pins)
    if methods()!=frozen: raise ValueError('Convergence methods changed during write')
    write_new(folder/'convergence-complete.json',receipt); return receipt


def verify(root,identifier):
    import re
    if not isinstance(identifier,str) or not re.fullmatch('exposure-convergence-[0-9a-f]{12}',identifier): raise ValueError('Invalid convergence ID')
    folder=contained(root,'artifacts/private/'+identifier); receipt=read_json(folder/'convergence-complete.json')
    if receipt['convergence_id']!=identifier or receipt['status']!='DECLARED_MULTI_SEED_DIAGNOSTICS' or receipt['methods']!=methods() or receipt['visibility']!='private' or receipt['public_release_approved'] is not False or set(receipt['outputs_sha256'])!={'assumptions.json','report.json'}:
        raise ValueError('Convergence receipt changed')
    for name,digest in receipt['outputs_sha256'].items():
        if sha256(folder/name)!=digest: raise ValueError('Convergence payload changed')
    plan=read_json(folder/'assumptions.json'); base,positions,pins=source(root,plan)
    if pins!=receipt['inputs_sha256']: raise ValueError('Convergence lineage changed')
    report=read_json(folder/'report.json'); expected=calculate(plan,base,positions)
    if json.dumps(report,sort_keys=True)!=json.dumps(expected,sort_keys=True): raise ValueError('Convergence replay differs')
    guard(root,pins)
    if receipt['methods']!=methods(): raise ValueError('Convergence methods changed during replay')
    return folder,receipt,report
