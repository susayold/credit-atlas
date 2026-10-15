"""Small auditable train-only encoder. Never auto-selects numeric/source columns."""
from __future__ import annotations
import math
import statistics

NUMERIC_ALLOWLIST={'classic_fico','original_dti','original_ltv','original_cltv','original_upb','original_term','units'}
CATEGORICAL_ALLOWLIST={'occupancy','loan_purpose','property_type','first_time_homebuyer'}

def _numeric(value):
    if value is None: return None
    if isinstance(value,bool): raise ValueError('Boolean is not a numeric feature')
    value=float(value)
    if not math.isfinite(value): raise ValueError('Nonfinite feature')
    return value

def _category(value):
    if value is None: return '__missing__'
    if not isinstance(value,str): raise ValueError('Categorical feature must be string or null')
    return 'value:'+value

class OriginationEncoder:
    def __init__(self,config):
        self.numeric=list(config['numeric']); self.categorical=list(config['categorical'])
        names=self.numeric+self.categorical
        if len(set(names))!=len(names): raise ValueError('Duplicate feature')
        if not set(self.numeric)<=NUMERIC_ALLOWLIST or not set(self.categorical)<=CATEGORICAL_ALLOWLIST:
            raise ValueError('Feature not in reviewed origination allowlist')
        self.state=None

    def fit(self,records):
        records=list(records)
        if not records: raise ValueError('Empty training partition')
        if any(r.get('partition')!='train' or r.get('included') is not True for r in records):
            raise ValueError('Preprocessing may fit only included training rows')
        for row in records:
            if any(f not in row for f in self.numeric+self.categorical): raise ValueError('Missing feature column')
        stats={}; categories={}; schema=[]
        for f in self.numeric:
            observed=[_numeric(r[f]) for r in records if r[f] is not None]
            median=statistics.median(observed) if observed else 0.0
            imputed=[median if r[f] is None else _numeric(r[f]) for r in records]
            mean=statistics.mean(imputed); scale=statistics.pstdev(imputed) or 1.0
            stats[f]={'median':median,'mean':mean,'scale':scale,'all_missing_train':not observed}
            schema.extend([f,f+'__missing'])
        for f in self.categorical:
            categories[f]=['__missing__','__unseen__']+sorted({_category(r[f]) for r in records if r[f] is not None})
            schema.extend(f+'='+v for v in categories[f])
        self.state={'numeric':stats,'categorical':categories,'feature_names':schema,'fit_partition':'train','fit_rows':len(records)}
        return self

    def transform(self,records):
        if self.state is None: raise ValueError('Encoder must be fitted on training first')
        result=[]
        for row in records:
            if any(f not in row for f in self.numeric+self.categorical): raise ValueError('Missing feature column')
            vector=[]
            for f in self.numeric:
                value=_numeric(row[f]); stats=self.state['numeric'][f]
                vector.extend([((stats['median'] if value is None else value)-stats['mean'])/stats['scale'],float(value is None)])
            for f in self.categorical:
                value=_category(row[f]); known=self.state['categorical'][f]
                if value not in known: value='__unseen__'
                vector.extend(float(value==v) for v in known)
            result.append(vector)
        return result
