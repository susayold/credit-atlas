"""Independent diagnostics-only reconciliation from saved seed/run summaries."""
import argparse
import json
import math
import uuid
from pathlib import Path
from fractions import Fraction
from credit_atlas.exposure_convergence import methods
from credit_atlas.exposure_movements import guard
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new


def audit(root,identifier):
    import re
    if not re.fullmatch('exposure-convergence-[0-9a-f]{12}',identifier): raise ValueError('Invalid convergence ID')
    folder=root/'artifacts/private'/identifier; receipt=read_json(folder/'convergence-complete.json'); report=read_json(folder/'report.json')
    if receipt['methods']!=methods() or receipt['convergence_id']!=identifier: raise ValueError('Convergence methods/binding changed')
    guard(root,receipt['inputs_sha256'])
    for name,digest in receipt['outputs_sha256'].items():
        if sha256(folder/name)!=digest: raise ValueError('Convergence payload changed')
    checks=0
    def check(test):
        nonlocal checks
        if not test: raise ValueError('Independent convergence diagnostic audit failed')
        checks+=1
    def near(a,b): check(math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7))
    def summary(values,stored):
        mean=math.fsum(values)/len(values); variance=math.fsum((v-mean)**2 for v in values)/(len(values)-1)
        near(stored['seed_mean'],mean); near(stored['seed_sample_sd'],math.sqrt(variance)); near(stored['seed_min'],min(values)); near(stored['seed_max'],max(values))
    plan=read_json(folder/'assumptions.json'); check(report['assumptions']==plan)
    check({(r['seed'],r['draws']) for r in report['runs']}=={(s,n) for s in plan['seeds'] for n in plan['draw_counts']})
    check(len(report['runs'])==len(plan['seeds'])*len(plan['draw_counts']))
    for diagnostic in report['diagnostics']:
        for level in diagnostic['levels']:
            results=[r for run in report['runs'] if run['draws']==level['draws'] for r in run['results'] if r['currency']==diagnostic['currency'] and r['id']==diagnostic['case_id']]
            check(len(results)==len(plan['seeds'])); summary([r['mean_loss'] for r in results],level['mean_loss'])
            for t in level['tails']:
                near(t['tail_mass_per_seed'],float((1-Fraction(t['alpha']))*level['draws']))
                for metric in ('var','es'): summary([next(row[metric] for row in r['tails'] if row['alpha']==t['alpha']) for r in results],t[metric])
        old,new=diagnostic['levels'][-2:]
        for delta in diagnostic['last_two_level_changes']:
            a=next(t[delta['metric']]['seed_mean'] for t in old['tails'] if t['alpha']==delta['alpha'])
            b=next(t[delta['metric']]['seed_mean'] for t in new['tails'] if t['alpha']==delta['alpha'])
            near(delta['absolute_change'],b-a)
            if a: near(delta['relative_change'],(b-a)/a)
            else: check(delta['relative_change'] is None)
    check(report['contract']['statistical_convergence_certified'] is False)
    guard(root,receipt['inputs_sha256'])
    return {'status':'PASS','convergence_id':identifier,'checks':checks,'scope':'Diagnostic aggregates only; full simulation replay is separately required',
        'completed_at':timestamp(),'visibility':'private','public_release_approved':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--convergence-id',required=True); args=parser.parse_args(); root=app_root()
    result=audit(root,args.convergence_id); folder=root/'artifacts/private'/('exposure-convergence-audit-'+uuid.uuid4().hex[:12]); folder.mkdir()
    result['script_sha256']=sha256(Path(__file__)); write_new(folder/'receipt.json',result); print(json.dumps({**result,'directory':str(folder)},indent=2))
