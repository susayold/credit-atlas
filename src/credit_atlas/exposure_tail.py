"""Declared finite-position one-factor Monte Carlo with recovery sensitivities."""
import hashlib
import json
import math
import re
import shutil
import uuid
from fractions import Fraction
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import scipy
from scipy.integrate import quad
from scipy.special import ndtr,ndtri
from scipy.stats import binom

from .exposure_scenarios import methods as scenario_methods,read_plan,source,verify as verify_scenario
from .exposure_movements import guard
from .exposure_imports import numeric,text
from .workspace import contained,read_json,sha256,timestamp,write_new

KEYS={'schema_version','name','version','basis','scenario_set_id','scenario_case_id','seed','draws','alphas','cases','visibility','public_release_approved'}
BATCH=128


def methods():
    return {**scenario_methods(),'exposure_tail':sha256(Path(__file__)),'numpy_version':np.__version__,'scipy_version':scipy.__version__,
        'rng':'PCG64 independent factor/idiosyncratic streams; batch128; sorted positions'}


def parameters(plan,rows,scenario_report):
    if (not isinstance(plan,dict) or set(plan)!=KEYS or type(plan['schema_version']) is not int or plan['schema_version']!=1
        or not all(text(plan[k]) for k in ('name','version')) or plan['basis']!='declared_research_dependence_and_recovery'
        or plan['visibility']!='private' or plan['public_release_approved'] is not False
        or type(plan['seed']) is not int or not 0<=plan['seed']<2**63 or type(plan['draws']) is not int or not 128<=plan['draws']<=65536):
        raise ValueError('Explicit bounded reproducible private tail scenario contract required')
    if not isinstance(plan['alphas'],list) or not 1<=len(plan['alphas'])<=4 or len(set(plan['alphas']))!=len(plan['alphas']): raise ValueError('Unique tail levels required')
    for value in plan['alphas']:
        if not Fraction('0.5')<=Fraction(numeric(value))<=Fraction('0.999'): raise ValueError('Tail levels in [0.5,0.999] required')
    cases=plan['cases']
    if not isinstance(cases,list) or not 1<=len(cases)<=8: raise ValueError('One to eight sensitivity cases required')
    ids=set()
    for case in cases:
        if (not isinstance(case,dict) or set(case)!={'id','label','asset_correlation','lgd_systemic_spread'} or not text(case['label'])
            or not isinstance(case['id'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,39}',case['id']) or case['id'] in ids):
            raise ValueError('Unique sensitivity ID and explicit correlation/recovery spread required')
        ids.add(case['id'])
        if Fraction(numeric(case['asset_correlation']))>Fraction('0.95') or Fraction(numeric(case['lgd_systemic_spread']))>1:
            raise ValueError('Asset correlation [0,0.95], LGD spread [0,1] required')
    assumption=scenario_report['assumptions']; selected=[r for r in rows if r['source_state'] in assumption['eligible_source_states']]
    if len(selected)*plan['draws']*len(cases)>300000000: raise ValueError('Simulation work bound exceeded; reduce draws/cases')
    scene=next((s for s in scenario_report['scenarios'] if s['id']==plan['scenario_case_id']),None)
    if scene is None: raise ValueError('Scenario case absent from pinned scenario set')
    result=[]
    for row in sorted(selected,key=lambda r:r['position_id']):
        a=assumption['segment_assumptions'][row['segment']]; p=Fraction(a['pd']); m=Fraction(scene['pd_odds_multiplier'])
        pd=p*m/(1-p+p*m); lgd=max(Fraction(0),min(Fraction(1),Fraction(a['lgd'])+Fraction(scene['lgd_addition'])))
        ead=Fraction(row['reported_amount_major_exact'])*Fraction(a['ead_factor'])*Fraction(scene['ead_multiplier'])
        result.append({'currency':row['currency'],'segment':row['segment'],'region':row['region'],
            'pd':float(pd),'lgd':float(lgd),'ead':float(ead),'ead_exact':ead})
    return result


def streams(seed,currency):
    def rng(tag):
        digest=hashlib.sha256((str(seed)+':'+currency+':'+tag).encode()).digest()
        return np.random.Generator(np.random.PCG64(int.from_bytes(digest[:16],'big')))
    return rng('factor'),rng('idiosyncratic')


def expected_loss(pd,lgd,ead,rho,spread):
    if pd==0 or ead==0: return 0.0
    if spread==0: return pd*lgd*ead
    threshold=float(ndtri(pd)); sr=math.sqrt(rho); residual=math.sqrt(1-rho)
    def integrand(z):
        conditional=1.0 if pd==1 else float(ndtr((threshold-sr*z)/residual))
        severity=min(1.0,max(0.0,lgd+spread*(2*float(ndtr(-z))-1)))
        return conditional*severity*math.exp(-z*z/2)/math.sqrt(2*math.pi)
    value,_=quad(integrand,-10,10,epsabs=1e-11,epsrel=1e-11,limit=200)
    return ead*value


def tail_summary(losses,segment_losses,alpha):
    n=len(losses); fraction=Fraction(alpha); tail_mass=(1-fraction)*n; whole=int(tail_mass); boundary=float(tail_mass-whole)
    order=np.argsort(-losses,kind='stable'); weights=np.zeros(n,dtype=np.float64)
    boundary_value=losses[order[math.ceil(float(tail_mass))-1]]
    strict=losses>boundary_value; ties=losses==boundary_value
    weights[strict]=1.0; tie_weight=(float(tail_mass)-int(np.sum(strict)))/int(np.sum(ties)); weights[ties]=tie_weight
    quantile_rank=(fraction.numerator*n+fraction.denominator-1)//fraction.denominator
    ordered=np.sort(losses); value=float(ordered[quantile_rank-1]); mass=float(tail_mass)
    es=float(np.sum(weights*losses)/mass)
    lower=int(binom.ppf(.025,n,float(fraction))); upper=int(binom.ppf(.975,n,float(fraction)))+1
    return {'alpha':alpha,'var':value,'es':es,'tail_mass_draws':mass,'full_tail_draws':whole,'boundary_draw_weight':boundary,
        'strict_tail_draws':int(np.sum(strict)),'boundary_tied_draws':int(np.sum(ties)),'boundary_tie_weight':tie_weight,
        'var_rank':quantile_rank,'var_interval_order_ranks':[lower,upper],
        'var_order_stat_95_interval':[float(ordered[lower-1]) if lower else 0.0,float(ordered[upper-1]) if upper<=n else None],
        'es_segment_contributions':{key:float(np.sum(weights*values)/mass) for key,values in segment_losses.items()}}


def simulate(plan,positions):
    total_rows=[]; segment_rows=[]; summaries=[]; scope=[]
    for currency in sorted({r['currency'] for r in positions}):
        rows=[r for r in positions if r['currency']==currency]; segments=sorted({r['segment'] for r in rows})
        eads=np.asarray([r['ead'] for r in rows],dtype=np.float64); thresholds=ndtri(np.asarray([r['pd'] for r in rows]))
        masks={s:np.asarray([r['segment']==s for r in rows]) for s in segments}; draws=plan['draws']
        factor_rng,idio_rng=streams(plan['seed'],currency); factors=factor_rng.standard_normal(draws)
        output={c['id']:{s:np.zeros(draws) for s in segments} for c in plan['cases']}
        counts={c['id']:{s:np.zeros(draws,dtype=np.int64) for s in segments} for c in plan['cases']}
        clipping={c['id']:np.zeros(draws,dtype=np.int64) for c in plan['cases']}
        for start in range(0,draws,BATCH):
            stop=min(draws,start+BATCH); eps=idio_rng.standard_normal((stop-start,len(rows))); z=factors[start:stop,None]
            for case in plan['cases']:
                rho=float(case['asset_correlation']); spread=float(case['lgd_systemic_spread']); identifier=case['id']
                defaults=math.sqrt(rho)*z+math.sqrt(1-rho)*eps<=thresholds[None,:]
                for s in segments:
                    mask=masks[s]; baseline=rows[int(np.flatnonzero(mask)[0])]['lgd']
                    raw=baseline+spread*(2*ndtr(-factors[start:stop])-1); severity=np.clip(raw,0,1)
                    exposure=np.sum(defaults[:,mask]*eads[mask][None,:],axis=1)
                    output[identifier][s][start:stop]=exposure*severity
                    counts[identifier][s][start:stop]=np.sum(defaults[:,mask],axis=1)
                    clipping[identifier][start:stop]+=(raw!=severity).astype(np.int64)
        exact_ead=sum((r['ead_exact'] for r in rows),Fraction(0))
        max_conversion=max((abs(Fraction.from_float(r['ead'])-r['ead_exact']) for r in rows),default=Fraction(0))
        total_ead=float(np.sum(eads))
        shares=[r['ead']/total_ead for r in rows] if total_ead>0 else []
        regions={region:sum(r['ead'] for r in rows if r['region']==region) for region in sorted({r['region'] for r in rows})}
        scope.append({'currency':currency,'eligible_position_records':len(rows),'zero_ead_records':int(np.sum(eads==0)),
            'declared_ead_exact':{'numerator':str(exact_ead.numerator),'denominator':str(exact_ead.denominator)},
            'declared_ead_float':float(np.sum(eads)),'max_absolute_ead_float_conversion_error':float(max_conversion),
            'position_ead_hhi':sum(v*v for v in shares) if shares else None,'top10_position_ead_share':sum(sorted(shares,reverse=True)[:10]) if shares else None,
            'regional_declared_ead':regions})
        for case in plan['cases']:
            identifier=case['id']; losses=np.sum(np.asarray(list(output[identifier].values())),axis=0)
            default_counts=np.sum(np.asarray(list(counts[identifier].values())),axis=0)
            analytical=0.0; factorized=0.0
            for s in segments:
                row=next(r for r in rows if r['segment']==s); value=float(np.sum(eads[masks[s]]))
                analytical+=expected_loss(row['pd'],row['lgd'],value,float(case['asset_correlation']),float(case['lgd_systemic_spread']))
                factorized+=row['pd']*row['lgd']*value
            mean=float(np.mean(losses)); sd=float(np.std(losses,ddof=1)); se=sd/math.sqrt(draws)
            histogram,bounds=np.histogram(losses,bins=20,range=(0,max(1,float(np.max(losses)))))
            summaries.append({**case,'currency':currency,'draws':draws,'mean_loss':mean,'loss_standard_deviation':sd,'mean_standard_error':se,
                'mean_normal_approx_95_interval':[mean-1.96*se,mean+1.96*se],'analytic_expected_loss':analytical,
                'factorized_constant_lgd_reference':factorized,'mean_minus_analytic':mean-analytical,
                'mean_standard_error_units':(mean-analytical)/se if se else None,'lgd_clipped_segment_draws':int(np.sum(clipping[identifier])),
                'mean_default_count':float(np.mean(default_counts)),'maximum_loss':float(np.max(losses)),
                'tails':[tail_summary(losses,output[identifier],alpha) for alpha in plan['alphas']],
                'histogram':{'counts':histogram.tolist(),'edges':bounds.tolist()}})
            for draw in range(draws):
                total_rows.append({'case_id':identifier,'currency':currency,'draw_index':draw,'factor_z':float(factors[draw]),
                    'total_loss':float(losses[draw]),'default_count':int(default_counts[draw]),'clipped_segments':int(clipping[identifier][draw])})
                for s in segments: segment_rows.append({'case_id':identifier,'currency':currency,'draw_index':draw,'segment':s,
                    'segment_loss':float(output[identifier][s][draw]),'default_count':int(counts[identifier][s][draw])})
    return {'scope':scope,'results':summaries,'contract':{'calibrated_correlation':False,'calibrated_recovery':False,'borrower_linkage':False,
        'regulatory_capital':False,'accounting_ecl':False,'fx_conversion':False,'latent_model':'sqrt(rho) Z + sqrt(1-rho) epsilon <= Phi^-1(PD)',
        'lgd_model':'clip(base LGD + spread*(2 Phi(-Z)-1),0,1); bad factor couples higher defaults and severity',
        'asset_correlation':'rho is latent asset correlation, not default-indicator correlation',
        'tail_measure':'Inverse empirical CDF VaR; ES integrates top (1-alpha)*N probability mass, equally averaged boundary ties',
        'replication':'Common random numbers across sensitivity cases within each currency; independent currencies, no joint FX loss',
        'concentration_grain':'Position/observation shares, not obligor concentration',
        'uncertainty':'Mean interval is normal approximation; VaR interval uses binomial order ranks; ES tail mass is finite simulation support'},
        'global_cross_currency_total':None,'visibility':'private','public_release_approved':False},total_rows,segment_rows


TOTAL_SCHEMA=pa.schema([pa.field('case_id',pa.string(),False),pa.field('currency',pa.string(),False),pa.field('draw_index',pa.int64(),False),
    pa.field('factor_z',pa.float64(),False),pa.field('total_loss',pa.float64(),False),pa.field('default_count',pa.int64(),False),pa.field('clipped_segments',pa.int64(),False)])
SEGMENT_SCHEMA=pa.schema([pa.field('case_id',pa.string(),False),pa.field('currency',pa.string(),False),pa.field('draw_index',pa.int64(),False),
    pa.field('segment',pa.string(),False),pa.field('segment_loss',pa.float64(),False),pa.field('default_count',pa.int64(),False)])


def inputs(root,plan):
    folder,receipt,scenario=verify_scenario(root,plan['scenario_set_id']); rows,metadata,pins=source(root,receipt['source_import_id'])
    pins.update({str((folder/n).relative_to(root)):d for n,d in receipt['outputs_sha256'].items()})
    pins[str((folder/'scenario-complete.json').relative_to(root))]=sha256(folder/'scenario-complete.json')
    return rows,metadata,scenario,pins


def build(root,relative):
    path=contained(root,relative); digest=sha256(path); plan=read_plan(path); frozen=methods()
    rows,metadata,scenario,pins=inputs(root,plan); positions=parameters(plan,rows,scenario)
    report,totals,segments=simulate(plan,positions); report.update(assumptions=plan,source_import_id=scenario['source_import_id'],
        as_of=metadata['as_of'],horizon_months=scenario['horizon_months'],default_definition=scenario['default_definition'],name=plan['name'],version=plan['version'])
    identifier='exposure-tail-'+uuid.uuid4().hex[:12]; folder=contained(root,'artifacts/private/'+identifier); folder.mkdir(parents=True)
    shutil.copyfile(path,folder/'assumptions.json'); write_new(folder/'report.json',report)
    pq.write_table(pa.Table.from_pylist(totals,schema=TOTAL_SCHEMA),folder/'total-draws.parquet',compression='zstd')
    pq.write_table(pa.Table.from_pylist(segments,schema=SEGMENT_SCHEMA),folder/'segment-draws.parquet',compression='zstd')
    guard(root,pins)
    if methods()!=frozen or sha256(path)!=digest or sha256(folder/'assumptions.json')!=digest: raise ValueError('Tail inputs/methods changed during build')
    receipt={'tail_id':identifier,'source_import_id':scenario['source_import_id'],'status':'DECLARED_FINITE_POSITION_TAIL_RESEARCH',
        'methods':frozen,'inputs_sha256':pins,'outputs_sha256':{n:sha256(folder/n) for n in ('assumptions.json','report.json','total-draws.parquet','segment-draws.parquet')},
        'completed_at':timestamp(),'visibility':'private','public_release_approved':False}
    write_new(folder/'tail-complete.json',receipt); return receipt


def verify(root,identifier,replay=True):
    if not isinstance(identifier,str) or not re.fullmatch('exposure-tail-[0-9a-f]{12}',identifier): raise ValueError('Invalid tail ID')
    folder=contained(root,'artifacts/private/'+identifier); receipt=read_json(folder/'tail-complete.json')
    if (receipt['tail_id']!=identifier or receipt['methods']!=methods() or receipt['status']!='DECLARED_FINITE_POSITION_TAIL_RESEARCH'
        or receipt['visibility']!='private' or receipt['public_release_approved'] is not False
        or set(receipt['outputs_sha256'])!={'assumptions.json','report.json','total-draws.parquet','segment-draws.parquet'}): raise ValueError('Tail receipt contract changed')
    for n,d in receipt['outputs_sha256'].items():
        if sha256(folder/n)!=d: raise ValueError('Tail payload changed')
    plan=read_plan(folder/'assumptions.json'); rows,metadata,scenario,pins=inputs(root,plan); positions=parameters(plan,rows,scenario)
    if pins!=receipt['inputs_sha256'] or receipt['source_import_id']!=scenario['source_import_id']: raise ValueError('Tail source binding changed')
    report=read_json(folder/'report.json')
    if report['assumptions']!=plan or report['source_import_id']!=receipt['source_import_id']: raise ValueError('Tail report contract changed')
    if replay:
        expected,total,segments=simulate(plan,positions); expected.update(assumptions=plan,source_import_id=scenario['source_import_id'],as_of=metadata['as_of'],
            horizon_months=scenario['horizon_months'],default_definition=scenario['default_definition'],name=plan['name'],version=plan['version'])
        if json.dumps(expected,sort_keys=True)!=json.dumps(report,sort_keys=True): raise ValueError('Tail simulation replay differs')
        for name,data,schema in [('total-draws.parquet',total,TOTAL_SCHEMA),('segment-draws.parquet',segments,SEGMENT_SCHEMA)]:
            table=pq.read_table(folder/name)
            if table.schema!=schema or table.to_pylist()!=data: raise ValueError('Tail draw replay differs')
    guard(root,pins)
    if methods()!=receipt['methods']: raise ValueError('Tail method changed during verification')
    return folder,receipt,report
