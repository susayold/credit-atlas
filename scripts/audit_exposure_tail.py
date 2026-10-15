"""Independent CSV/Fraction scope, quadrature and empirical-tail audit."""
import argparse
import csv
import json
import math
import statistics
import uuid
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pyarrow.parquet as pq
from credit_atlas.exposure_tail import verify
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new


def analytic(pd,lgd,ead,rho,spread):
    if pd==0 or ead==0: return 0.0
    if spread==0: return pd*lgd*ead
    normal=NormalDist(); threshold=normal.inv_cdf(pd) if 0<pd<1 else None
    nodes,weights=np.polynomial.legendre.leggauss(128)
    cuts=[-10.0,10.0]
    for bound in (0,1):
        probability=(lgd+spread-bound)/(2*spread)
        if 0<probability<1: cuts.append(normal.inv_cdf(probability))
    integral=0.0
    for left,right in zip(sorted(cuts)[:-1],sorted(cuts)[1:]):
        for node,weight in zip(nodes,weights):
            z=(left+right)/2+(right-left)*float(node)/2
            cp=1.0 if pd==1 else normal.cdf((threshold-math.sqrt(rho)*z)/math.sqrt(1-rho))
            severity=max(0,min(1,lgd+spread*(1-2*normal.cdf(z))))
            integral+=float(weight)*(right-left)/2*cp*severity*math.exp(-z*z/2)/math.sqrt(2*math.pi)
    return ead*integral


def audit(root,identifier):
    folder,receipt,report=verify(root,identifier); checks=0
    def check(condition,label):
        nonlocal checks
        if not condition: raise ValueError('Independent tail audit failed: '+label)
        checks+=1
    def near(actual,expected,label):
        check(math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-7),label)
    plan=read_json(folder/'assumptions.json')
    scene=read_json(root/'artifacts/private'/plan['scenario_set_id']/'report.json')
    scenario=next(s for s in scene['scenarios'] if s['id']==plan['scenario_case_id'])
    source_folder=root/'artifacts/private'/receipt['source_import_id']
    records=list(csv.DictReader((source_folder/'source.csv').open(encoding='utf-8-sig',newline='')))
    selected=[r for r in records if r['source_state'] in scene['assumptions']['eligible_source_states']]
    amounts=defaultdict(list); groups=defaultdict(lambda:Fraction(0)); regions=defaultdict(lambda:Fraction(0)); risk={}
    units={'major':1,'thousand':1000,'million':1000000}
    for row in selected:
        a=scene['assumptions']['segment_assumptions'][row['segment']]
        e=Fraction(row['reported_amount'])*units[row['amount_unit']]*Fraction(a['ead_factor'])*Fraction(scenario['ead_multiplier'])
        p=Fraction(a['pd']); odds=Fraction(scenario['pd_odds_multiplier']); p=p*odds/(1-p+p*odds)
        lgd=max(Fraction(0),min(Fraction(1),Fraction(a['lgd'])+Fraction(scenario['lgd_addition'])))
        key=(row['currency'],row['segment']); groups[key]+=e; amounts[row['currency']].append(e)
        regions[(row['currency'],row['region'])]+=e; risk[key]=(float(p),float(lgd))
    for scope in report['scope']:
        currency=scope['currency']; values=amounts[currency]; total=sum(values)
        check(scope['eligible_position_records']==len(values),'source count')
        check(scope['zero_ead_records']==values.count(0),'zero EAD')
        check(Fraction(int(scope['declared_ead_exact']['numerator']),int(scope['declared_ead_exact']['denominator']))==total,'exact EAD')
        near(scope['declared_ead_float'],float(total),'float EAD')
        shares=[v/total for v in values] if total else []
        if shares:
            near(scope['position_ead_hhi'],float(sum(v*v for v in shares)),'HHI')
            near(scope['top10_position_ead_share'],float(sum(sorted(shares,reverse=True)[:10])),'top 10')
        for region,value in scope['regional_declared_ead'].items(): near(value,float(regions[(currency,region)]),'regional EAD')
    currency_totals={currency:float(sum(values)) for currency,values in amounts.items()}
    totals=pq.read_table(folder/'total-draws.parquet').to_pylist()
    segments=pq.read_table(folder/'segment-draws.parquet').to_pylist()
    parts=defaultdict(dict)
    for row in segments:
        key=(row['case_id'],row['currency'],row['draw_index'])
        check(row['segment'] not in parts[key],'unique segment draw'); parts[key][row['segment']]=row
    by_case=defaultdict(list); factors={}
    for row in totals:
        key=(row['case_id'],row['currency'],row['draw_index']); pieces=parts.pop(key)
        near(row['total_loss'],math.fsum(r['segment_loss'] for r in pieces.values()),'draw reconciliation')
        check(row['default_count']==sum(r['default_count'] for r in pieces.values()),'default reconciliation')
        check(math.isfinite(row['total_loss']) and 0<=row['total_loss']<=currency_totals[row['currency']]+1e-6,'bounded loss')
        factor_key=(row['currency'],row['draw_index'])
        if factor_key in factors: check(row['factor_z']==factors[factor_key],'common factor draws')
        factors[factor_key]=row['factor_z']; row['parts']=pieces
        by_case[(row['case_id'],row['currency'])].append(row)
    check(not parts,'no orphan segment draws')
    for result in report['results']:
        currency=result['currency']; rows=by_case.pop((result['id'],currency)); n=plan['draws']
        check(len(rows)==n and sorted(r['draw_index'] for r in rows)==list(range(n)),'complete draw ordinals')
        losses=[r['total_loss'] for r in rows]; ordered=sorted(losses)
        mean=statistics.mean(losses); sd=statistics.stdev(losses); se=sd/math.sqrt(n)
        near(result['mean_loss'],mean,'mean'); near(result['loss_standard_deviation'],sd,'sample SD'); near(result['mean_standard_error'],se,'SE')
        for value,expected in zip(result['mean_normal_approx_95_interval'],[mean-1.96*se,mean+1.96*se]): near(value,expected,'mean interval')
        near(result['maximum_loss'],max(losses),'maximum'); near(result['mean_default_count'],statistics.mean(r['default_count'] for r in rows),'default mean')
        check(result['lgd_clipped_segment_draws']==sum(r['clipped_segments'] for r in rows),'clipping')
        independent=sum(analytic(*risk[k],float(e),float(result['asset_correlation']),float(result['lgd_systemic_spread'])) for k,e in groups.items() if k[0]==currency)
        near(result['analytic_expected_loss'],independent,'independent Gaussian quadrature')
        near(result['factorized_constant_lgd_reference'],sum(p*l*float(groups[k]) for k,(p,l) in risk.items() if k[0]==currency),'factorized reference')
        near(result['mean_minus_analytic'],mean-independent,'mean residual')
        histogram=[0]*20; edges=result['histogram']['edges']
        for loss in losses:
            bucket=min(19,int(loss/(edges[-1]/20))); histogram[bucket]+=1
        check(histogram==result['histogram']['counts'],'histogram counts')
        for tail in result['tails']:
            alpha=Fraction(tail['alpha']); mass=(1-alpha)*n; rank=math.ceil(alpha*n)
            near(tail['var'],ordered[rank-1],'VaR'); near(tail['tail_mass_draws'],float(mass),'tail mass')
            # Integrate descending empirical quantile cells, including partial cell.
            descending=sorted(losses,reverse=True); whole=int(mass); remainder=mass-whole
            es=(math.fsum(descending[:whole])+float(remainder)*(descending[whole] if remainder else 0))/float(mass)
            near(tail['es'],es,'ES quantile integral')
            boundary=descending[math.ceil(mass)-1]; strict=sum(v>boundary for v in losses); tied=sum(v==boundary for v in losses)
            boundary_weight=float((mass-strict)/tied)
            check(tail['strict_tail_draws']==strict and tail['boundary_tied_draws']==tied,'tail ties')
            near(tail['boundary_tie_weight'],boundary_weight,'tie weight')
            for segment,value in tail['es_segment_contributions'].items():
                numerator=math.fsum(r['parts'][segment]['segment_loss']*(1 if r['total_loss']>boundary else boundary_weight if r['total_loss']==boundary else 0) for r in rows)
                near(value,numerator/float(mass),'joint tail segment attribution')
            near(math.fsum(tail['es_segment_contributions'].values()),es,'ES contributions sum')
            lower,upper=tail['var_interval_order_ranks']
            interval=[ordered[lower-1] if lower else 0.0,ordered[upper-1] if upper<=n else None]
            check(tail['var_order_stat_95_interval']==interval,'VaR interval endpoints')
    check(not by_case and report['global_cross_currency_total'] is None,'native scope completeness')
    return {'status':'PASS','tail_id':identifier,'source_import_id':receipt['source_import_id'],'checks':checks,
        'methods':'CSV Fraction source scope; math/statistics empirical quantile integral; split Gauss-Legendre analytic mean; joint-draw conservation',
        'completed_at':timestamp(),'visibility':'private','public_release_approved':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--tail-id',required=True); args=parser.parse_args(); root=app_root()
    result=audit(root,args.tail_id); output=root/'artifacts/private'/('exposure-tail-audit-'+uuid.uuid4().hex[:12]); output.mkdir()
    result['audit_script_sha256']=sha256(Path(__file__)); write_new(output/'receipt.json',result)
    print(json.dumps({**result,'directory':str(output)},indent=2))
