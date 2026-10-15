"""Independent rational movement checks over deterministic synthetic boundaries."""
from pathlib import Path
from fractions import Fraction
from collections import defaultdict
from random import Random
from uuid import uuid4
from credit_atlas.exposure_movements import bridge
from credit_atlas.workspace import sha256,write_new

ROOT=Path(__file__).resolve().parents[1];rng=Random(40615);checks=0;cases=[]
dimensions=['region','segment','source_state','representation']
fields=['opening_amount','removed_amount','continuing_amount_change','transfer_in','transfer_out','added_amount','closing_amount','residual']
before={'source_namespace':'SYNTHETIC-QA','dataset_kind':'declared_portfolio','amount_kind':'declared_position_amount','date_grain':'day','as_of':'2026-10-14'}
after={**before,'as_of':'2026-10-15'}
def value():
    # Exact decimal source values including zero and sub-cent precision.
    return '0' if rng.randrange(5)==0 else str(rng.randrange(100000))+'.'+str(rng.randrange(10**18)).zfill(18)
def row(key):
    return {'position_id':str(key),'pool_key':'pool-'+str(key%2),'representation':'DIRECT_ASSET' if key%2==0 else 'SECURITY_POSITION',
            'currency':rng.choice(['USD','VND','EUR']), 'region':rng.choice(['N','S','E']), 'segment':rng.choice(['A','B']),
            'source_state':rng.choice(['CURRENT','D1','D3']), 'reported_amount_major_exact':value()}
for case in range(100):
    old={k:row(k) for k in range(1,25)};new={}
    for k in range(13,37):
        new[k]=row(k)
        if k in old:
            for name in ['pool_key','representation']:new[k][name]=old[k][name]
    result=bridge(list(old.values()),list(new.values()),before,after)
    shared=set(old)&set(new);same={k for k in shared if old[k]['currency']==new[k]['currency']};migrated=shared-same
    assert result['identity_counts']=={'opening_only':12,'closing_only':12,'matched_same_currency':len(same),'matched_currency_migration':len(migrated)}
    checks+=1
    for item in result['currencies']+result['groups']:
        currency=item['currency'];dimension=item.get('dimension');bucket=item.get('bucket')
        inside=lambda r:r['currency']==currency and (dimension is None or r[dimension]==bucket)
        amount=lambda r:Fraction(r['reported_amount_major_exact'])
        opening=sum((amount(r) for r in old.values() if inside(r)),Fraction())
        closing=sum((amount(r) for r in new.values() if inside(r)),Fraction())
        removed=sum((amount(old[k]) for k in set(old)-same if inside(old[k])),Fraction())
        added=sum((amount(new[k]) for k in set(new)-same if inside(new[k])),Fraction())
        delta=sum((amount(new[k])-amount(old[k]) for k in same if inside(old[k])),Fraction())
        incoming=sum((amount(new[k]) for k in same if dimension and inside(new[k]) and not inside(old[k])),Fraction())
        outgoing=sum((amount(new[k]) for k in same if dimension and inside(old[k]) and not inside(new[k])),Fraction())
        expected=[opening,removed,delta,incoming,outgoing,added,closing,closing-(opening-removed+delta+incoming-outgoing+added)]
        for name,number in zip(fields,expected):assert Fraction(item[name])==number;checks+=1
    transitions=defaultdict(lambda:[0,Fraction()])
    for k in same:
        for dimension in dimensions:
            if old[k][dimension]!=new[k][dimension]:
                key=(old[k]['currency'],dimension,old[k][dimension],new[k][dimension]);transitions[key][0]+=1;transitions[key][1]+=Fraction(new[k]['reported_amount_major_exact'])
    actual={(r['currency'],r['dimension'],r['from_bucket'],r['to_bucket']):[r['records'],Fraction(r['closing_amount_transferred'])] for r in result['transitions']}
    assert actual==dict(transitions);checks+=1
    assert result['global_cross_currency_total'] is None and all(not v for v in result['contract'].values() if isinstance(v,bool));checks+=1
    cases.append({'case':case,'same_currency':len(same),'migration':len(migrated),'transitions':len(actual)})
out=ROOT/'artifacts/private'/('movement-boundary-audit-'+uuid4().hex[:12]);out.mkdir()
write_new(out/'receipt.json',{'status':'PASS','cases':cases,'exact_checks':checks,'seed':40615,'synthetic_only':True,
    'method_sha256':sha256(Path(__file__)),'movement_method_sha256':sha256(ROOT/'src/credit_atlas/exposure_movements.py'),
    'scope':'Exact native-currency/bucket amounts and residuals; same-currency reclassification uses closing amount, migration is removal/addition. No institution actuals, exit attribution or FX P&L.'})
print(out);print('cases',len(cases),'checks',checks)
