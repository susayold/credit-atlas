"""Independent closed-form identities for all source calendar/lien scopes."""
import hashlib,json,uuid
from fractions import Fraction
from pathlib import Path
from credit_atlas.utility_debt_service import report
root=Path.cwd();out=root/'artifacts/private'/('utility-driver-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
profile=root/'artifacts/private/utility-debt-profile-9b7023d435f2/profile.json'
assert hashlib.sha256(profile.read_bytes()).hexdigest()=='7f159bed4a7e979f8c3afc98d623e8f8aa8c9c46b95920926dec2a9ff5bfacba'
doc=json.loads(profile.read_text(encoding='utf8'));checks=[];issues=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=hashlib.sha256(ledger.read_bytes()).hexdigest()
for current in doc['continuing_rows']:
    prior=next((p for p in doc['continuing_rows'] if p['edition']==current['edition'] and p['system']==current['system'] and p['year']==current['year']-1),None)
    for basis in ['parity','total']:
        query={'edition':str(current['edition']),'year':str(current['year']),'system':current['system'],'basis':basis}
        result=report(root,query)['dscr_driver']
        if prior is None:
            good=result['baseline'] is None and result['effects']==[] and result['status']=='NO_PRIOR_CALENDAR_YEAR'
        else:
            a={k:int(v) for k,v in current['values'].items() if not k.startswith('reported_')};b={k:int(v) for k,v in prior['values'].items() if not k.startswith('reported_')}
            d1,d0=a[basis+'_debt_service'],b[basis+'_debt_service'];n1,n0=a['net_revenues'],b['net_revenues']
            delta=Fraction(n1*d0-n0*d1,d0*d1)
            er1=n1-a['revenue_after_transfers']+a['operation_maintenance'];er0=n0-b['revenue_after_transfers']+b['operation_maintenance']
            expected={'revenue':Fraction(a['revenue_after_transfers']-b['revenue_after_transfers'],d0),
                'maintenance':Fraction(b['operation_maintenance']-a['operation_maintenance'],d0),
                'source_residual':Fraction(er1-er0,d0),'debt_service':Fraction(-n1*(d1-d0),d0*d1)}
            actual={e['key']:Fraction(int(e['effect_times']['numerator']),int(e['effect_times']['denominator'])) for e in result['effects']}
            change=Fraction(int(result['ratio_change']['numerator']),int(result['ratio_change']['denominator']))
            counterfactual=Fraction(int(result['numerator_first_counterfactual_ratio']['numerator']),int(result['numerator_first_counterfactual_ratio']['denominator']))
            good=actual==expected and change==delta and sum(actual.values(),Fraction(0))==delta and counterfactual==Fraction(n1,d0) and result['exact_residual']['numerator']=='0' and not result['causal_attribution_qualified']
        if not good:issues.append(query)
        checks.append({'query':query,'baseline_available':prior is not None,'matches':good})
unchanged=hashlib.sha256(ledger.read_bytes()).hexdigest()==before
receipt={'status':'PASS' if not issues and unchanged else 'ISSUES_FOUND','checks':checks,'issues':issues,
    'supported_bridges':sum(c['baseline_available'] for c in checks),'missing_prior_scopes':sum(not c['baseline_available'] for c in checks),
    'ledger_unchanged':unchanged,'scope':'Closed-form integer/Fraction inputs and driver/counterfactual identities; not causal or legal qualification'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(out);print(receipt['status'],receipt['supported_bridges'],receipt['missing_prior_scopes'])
if receipt['status']!='PASS':raise SystemExit(1)
