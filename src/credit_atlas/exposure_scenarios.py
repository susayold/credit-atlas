"""Versioned, explicitly declared factorized risk scenarios on observed amounts."""
import json
import re
import shutil
import uuid
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from .exposure_imports import methods as import_methods, normalize, numeric, text, verify_import
from .exposure_movements import guard, methods as movement_methods
from .workspace import contained, read_json, sha256, timestamp, write_new

DIMENSIONS=('segment','region','source_state')
KEYS={'schema_version','name','version','basis','source_import_id','horizon_months','default_definition',
      'eligible_source_states','ead_basis','lgd_boundary_policy','segment_assumptions','scenarios',
      'visibility','public_release_approved'}


def methods():
    return {**movement_methods(),'exposure_scenarios':sha256(Path(__file__))}


def exact(value):
    value=Fraction(value)
    with localcontext() as context:
        context.prec=50
        decimal=str(Decimal(value.numerator)/Decimal(value.denominator))
    return {'numerator':str(value.numerator),'denominator':str(value.denominator),'decimal_50':decimal}


def signed(value):
    if not isinstance(value,str): raise ValueError('Decimal string required')
    return -Fraction(numeric(value[1:])) if value.startswith('-') else Fraction(numeric(value))


def validate(plan, rows):
    if (not isinstance(plan,dict) or set(plan)!=KEYS or type(plan['schema_version']) is not int or plan['schema_version']!=1
        or not all(text(plan[k]) for k in ('name','version','default_definition'))
        or plan['basis']!='declared_research_assumptions' or plan['visibility']!='private' or plan['public_release_approved'] is not False
        or type(plan['horizon_months']) is not int or not 1<=plan['horizon_months']<=1200
        or plan['ead_basis']!='reported_amount_times_declared_factor' or plan['lgd_boundary_policy']!='clip_and_report'):
        raise ValueError('Explicit versioned private scenario assumption contract required')
    states=plan['eligible_source_states']
    if (not isinstance(states,list) or not states or len(states)!=len(set(states))
        or any(s not in ('CURRENT','DECLARED_PERFORMING') for s in states)):
        raise ValueError('Only explicitly selected CURRENT/DECLARED_PERFORMING observations supported')
    eligible=[r for r in rows if r['source_state'] in states]
    if not eligible: raise ValueError('No eligible source observations')
    if any(r['representation']!='DIRECT_ASSET' for r in rows): raise ValueError('Direct asset observation scenario only')
    segments={r['segment'] for r in eligible}; assumptions=plan['segment_assumptions']
    if not isinstance(assumptions,dict) or set(assumptions)!=segments: raise ValueError('Exact eligible-segment assumption coverage required')
    for assumption in assumptions.values():
        if not isinstance(assumption,dict) or set(assumption)!={'pd','lgd','ead_factor'}: raise ValueError('PD/LGD/EAD factor assumptions required')
        p,l,e=(Fraction(numeric(assumption[k])) for k in ('pd','lgd','ead_factor'))
        if p>1 or l>1 or e>1000: raise ValueError('PD/LGD fractions and EAD factor in [0,1000] required')
    scenarios=plan['scenarios']
    if not isinstance(scenarios,list) or not 1<=len(scenarios)<=12: raise ValueError('One to twelve declared scenarios required')
    ids=set()
    for scenario in scenarios:
        if (not isinstance(scenario,dict) or set(scenario)!={'id','label','pd_odds_multiplier','lgd_addition','ead_multiplier'}
            or not text(scenario['label']) or not isinstance(scenario['id'],str)
            or not re.fullmatch('[a-z][a-z0-9_]{0,39}',scenario['id']) or scenario['id']=='baseline' or scenario['id'] in ids):
            raise ValueError('Unique non-baseline scenario ID/label and exact shock contract required')
        odds=Fraction(numeric(scenario['pd_odds_multiplier'])); ead=Fraction(numeric(scenario['ead_multiplier'])); lgd=signed(scenario['lgd_addition'])
        if not 0<odds<=1000 or not 0<=ead<=1000 or not -1<=lgd<=1: raise ValueError('Scenario shock bounds exceeded')
        ids.add(scenario['id'])
    return eligible


def project(rows, metadata, plan):
    if metadata['risk_contract'] is not None: raise ValueError('Scenario assumptions cannot overwrite source risk inputs')
    eligible=validate(plan,rows); selected={r['position_id'] for r in eligible}
    scope=defaultdict(lambda: {'source_records':0,'eligible_records':0,'excluded_records':0,
        'source_amount':Fraction(0),'eligible_amount':Fraction(0),'excluded_amount':Fraction(0)})
    exclusions=defaultdict(lambda:[0,Fraction(0)])
    for row in rows:
        c=row['currency']; amount=Fraction(row['reported_amount_major_exact']); item=scope[c]
        item['source_records']+=1; item['source_amount']+=amount
        status='eligible' if row['position_id'] in selected else 'excluded'
        item[status+'_records']+=1; item[status+'_amount']+=amount
        if status=='excluded': exclusions[(c,row['source_state'])][0]+=1; exclusions[(c,row['source_state'])][1]+=amount
    scenarios=[{'id':'baseline','label':'Declared baseline assumptions','pd_odds_multiplier':'1','lgd_addition':'0','ead_multiplier':'1'}]+plan['scenarios']
    results=[]
    for scenario in scenarios:
        groups=defaultdict(lambda:{'records':0,'zero_source_amount_records':0,'lgd_clipped_records':0,
            'reported_amount':Fraction(0),'declared_ead':Fraction(0),'research_el':Fraction(0),
            'baseline_research_el':Fraction(0),'pd_effect':Fraction(0),'lgd_effect':Fraction(0),'ead_effect':Fraction(0)})
        for row in eligible:
            assumption=plan['segment_assumptions'][row['segment']]
            p,l,e=(Fraction(assumption[k]) for k in ('pd','lgd','ead_factor'))
            amount=Fraction(row['reported_amount_major_exact']); e*=amount
            multiplier=Fraction(scenario['pd_odds_multiplier'])
            sp=p*multiplier/(1-p+p*multiplier); raw_l=l+signed(scenario['lgd_addition']); sl=max(Fraction(0),min(Fraction(1),raw_l)); se=e*Fraction(scenario['ead_multiplier'])
            for dim,bucket in [('total','ALL')]+[(d,row[d]) for d in DIMENSIONS]:
                item=groups[(row['currency'],dim,bucket)]
                item['records']+=1; item['zero_source_amount_records']+=amount==0; item['lgd_clipped_records']+=raw_l!=sl
                for key,value in {'reported_amount':amount,'declared_ead':se,'research_el':sp*sl*se,'baseline_research_el':p*l*e,
                    'pd_effect':(sp-p)*l*e,'lgd_effect':sp*(sl-l)*e,'ead_effect':sp*sl*(se-e)}.items(): item[key]+=value
        records=[]
        for (currency,dim,bucket),item in sorted(groups.items()):
            delta=item['research_el']-item['baseline_research_el']; residual=delta-item['pd_effect']-item['lgd_effect']-item['ead_effect']
            records.append({'currency':currency,'dimension':dim,'bucket':bucket,
                **{k:(exact(v) if isinstance(v,Fraction) else v) for k,v in item.items()},'el_change':exact(delta),'attribution_residual':exact(residual)})
        results.append({**scenario,'aggregates':records})
    return {'source_import_id':plan['source_import_id'],'as_of':metadata['as_of'],'date_grain':metadata['date_grain'],
        'source_namespace':metadata['source_namespace'],'name':plan['name'],'version':plan['version'],'basis':plan['basis'],
        'horizon_months':plan['horizon_months'],'default_definition':plan['default_definition'],
        'assumptions':plan,'scope':[{'currency':c,**{k:exact(v) if isinstance(v,Fraction) else v for k,v in item.items()}} for c,item in sorted(scope.items())],
        'exclusions':[{'currency':c,'source_state':s,'records':n,'reported_amount':exact(v)} for (c,s),(n,v) in sorted(exclusions.items())],
        'scenarios':results,'attribution_order':['PD odds shock','LGD addition with disclosed clipping','EAD multiplier','residual'],
        'contract':{'calibrated_pd':False,'calibrated_macro_relationship':False,'observed_ead':False,'observed_lgd':False,
            'accounting_ecl':False,'regulatory_irb':False,'risk_inputs_overwrite_source':False,'fx_conversion':False,
            'ead_basis':'Reported amount × declared factor; assumption only',
            'pd_transform':'p × odds_multiplier / (1 − p + p × odds_multiplier)',
            'lgd_boundary_policy':'clip_and_report: every clipped eligible record counted',
            'eligibility':'Explicit source state selection; not a validated performing/default classifier',
            'precision':'Exact rational numerator/denominator authoritative; decimal_50 is display projection'},
        'global_cross_currency_total':None,'visibility':'private','public_release_approved':False}


def source(root, identifier):
    folder,receipt,_=verify_import(root,identifier); metadata=read_json(folder/'metadata.json')
    rows=normalize(folder/'source.csv',metadata)
    pins={str((folder/name).relative_to(root)):digest for name,digest in receipt['outputs_sha256'].items()}
    pins[str((folder/'import-complete.json').relative_to(root))]=sha256(folder/'import-complete.json')
    pins.update({row['path']:row['sha256'] for row in metadata['source_lineage']})
    return rows,metadata,pins


def read_plan(path):
    if not 0<path.stat().st_size<=100000: raise ValueError('Scenario assumption file exceeds bound')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: raise ValueError('Duplicate assumption JSON key')
            result[k]=v
        return result
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=pairs)


def build(root, relative):
    path=contained(root,relative); digest=sha256(path); plan=read_plan(path); frozen=methods()
    rows,metadata,pins=source(root,plan['source_import_id']); report=project(rows,metadata,plan)
    identifier='exposure-scenario-'+uuid.uuid4().hex[:12]; folder=contained(root,'artifacts/private/'+identifier); folder.mkdir(parents=True)
    shutil.copyfile(path,folder/'assumptions.json'); write_new(folder/'report.json',report)
    guard(root,pins)
    if methods()!=frozen or sha256(path)!=digest or sha256(folder/'assumptions.json')!=digest: raise ValueError('Scenario inputs/methods changed during build')
    receipt={'scenario_id':identifier,'source_import_id':plan['source_import_id'],'status':'DECLARED_RESEARCH_SCENARIO_SET',
        'methods':frozen,'inputs_sha256':pins,'outputs_sha256':{name:sha256(folder/name) for name in ('assumptions.json','report.json')},
        'completed_at':timestamp(),'visibility':'private','public_release_approved':False}
    write_new(folder/'scenario-complete.json',receipt); return receipt


def verify(root, identifier):
    if not isinstance(identifier,str) or not re.fullmatch('exposure-scenario-[0-9a-f]{12}',identifier): raise ValueError('Invalid scenario ID')
    folder=contained(root,'artifacts/private/'+identifier); receipt=read_json(folder/'scenario-complete.json')
    if (receipt['scenario_id']!=identifier or receipt['methods']!=methods() or receipt['status']!='DECLARED_RESEARCH_SCENARIO_SET'
        or receipt['visibility']!='private' or receipt['public_release_approved'] is not False
        or set(receipt['outputs_sha256'])!={'assumptions.json','report.json'}): raise ValueError('Scenario receipt contract changed')
    for name,digest in receipt['outputs_sha256'].items():
        if sha256(folder/name)!=digest: raise ValueError('Scenario payload changed')
    plan=read_plan(folder/'assumptions.json')
    if receipt['source_import_id']!=plan['source_import_id']: raise ValueError('Scenario source mismatch')
    rows,metadata,pins=source(root,receipt['source_import_id']); guard(root,pins)
    if pins!=receipt['inputs_sha256']: raise ValueError('Scenario source pins changed')
    expected=project(rows,metadata,plan); report=read_json(folder/'report.json')
    guard(root,pins)
    if methods()!=receipt['methods']: raise ValueError('Scenario methods changed during verification')
    if json.dumps(report,sort_keys=True)!=json.dumps(expected,sort_keys=True): raise ValueError('Scenario source rederivation differs')
    return folder,receipt,report
