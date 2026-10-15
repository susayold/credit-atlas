import copy
import re
import threading
from pathlib import Path
from . import retail_cohort_explanations as cohort
from .retail_explanations import guard
from .retail_explanations_saved import verify_cohort_saved,certificate_pins,CERTIFICATES
from .workspace import sha256


class RetailCohortExplanationViews:
    def __init__(self,root):
        self.root=root; self.lock=threading.RLock(); self.cache={}
        self.methods=self.current_methods()
    def current_methods(self):
        return cohort.methods()|{'serving':sha256(Path(__file__)),'saved_verifier':sha256(Path(__file__).with_name('retail_explanations_saved.py'))}

    def evidence(self,identifier):
        if self.methods != self.current_methods(): raise ValueError('Cohort serving methods changed')
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report,rows=verify_cohort_saved(self.root,identifier)
                pins=receipt['inputs_sha256']|{str((folder/n).relative_to(self.root)):h for n,h in receipt['outputs_sha256'].items()}
                pins[str((folder/'cohort-explanations-complete.json').relative_to(self.root))]=sha256(folder/'cohort-explanations-complete.json')
                if identifier in CERTIFICATES:
                    pins.update(certificate_pins(self.root,identifier))
                    pins.update(certificate_pins(self.root,report['explanations_id']))
                self.cache[identifier]=(report,rows,pins)
            report,rows,pins=self.cache[identifier]; guard(self.root,pins)
            return report,rows

    def catalog(self,query):
        if set(query)!={'freeze_id','explanations_id'} or not isinstance(query['freeze_id'],str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}',query['freeze_id']) or not isinstance(query['explanations_id'],str) or not cohort.base.ID.fullmatch(query['explanations_id']): raise ValueError('Bound cohort catalog required')
        studies=[]
        for path in (self.root/'artifacts/private').glob('retail-cohort-explanations-*/cohort-explanations-complete.json'):
            try:
                report,_=self.evidence(path.parent.name)
                if all(report[k]==query[k] for k in query): studies.append({'cohort_id':path.parent.name,'records':report['records']})
            except (ValueError,KeyError,OSError,TypeError): continue
        return {'studies':studies,**query}

    def bound(self,query):
        report,rows=self.evidence(query['cohort_id'])
        if any(report[k]!=query[k] for k in ('freeze_id','explanations_id')): raise ValueError('Cohort explanation source mismatch')
        return report,rows

    def clients(self,query):
        required={'cohort_id','freeze_id','explanations_id'}
        if not required<=set(query) or set(query)-required-{'offset','limit','q'}: raise ValueError('Exact cohort client query required')
        def integer(name,default,maximum):
            value=query.get(name,str(default))
            if not isinstance(value,str) or not value.isascii() or not value.isdigit() or len(value)>5 or int(value)>maximum: raise ValueError('Bounded ASCII pagination required')
            return int(value)
        offset=integer('offset',0,50000); limit=integer('limit',20,50)
        if limit<1: raise ValueError('Positive pagination limit required')
        q=query.get('q','')
        if not isinstance(q,str) or q and not cohort.TOKEN.fullmatch(q): raise ValueError('Exact study-scoped client token required')
        report,rows=self.bound(query)
        selected=sorted((r for r in rows if not q or r['client_token']==q),key=lambda r:-r['score_rank'])
        if offset>len(selected): raise ValueError('Pagination exceeds selected cohort')
        return {'cohort_id':query['cohort_id'],'freeze_id':report['freeze_id'],'explanations_id':report['explanations_id'],
                'total':len(selected),'cohort_records':report['records'],'offset':offset,'limit':limit,'q':q,
                'clients':[{k:r[k] for k in ('client_token','score_rank','predicted_probability')} for r in selected[offset:offset+limit]],
                'visibility':'private','public_release_approved':False}

    def report(self,query):
        if set(query)!={'cohort_id','freeze_id','explanations_id','client_token'} or not isinstance(query['client_token'],str) or not cohort.TOKEN.fullmatch(query['client_token']): raise ValueError('Exact source-bound client report required')
        report,rows=self.bound(query)
        row=next((r for r in rows if r['client_token']==query['client_token']),None)
        if row is None: raise ValueError('Client token does not belong to this cohort')
        client={k:row[k] for k in ('client_token','score_rank','predicted_probability','reference_probability','reconstruction_residual')}
        client['contributions']=[{'group':g,'probability_contribution':row[g]} for g in report['feature_groups']]
        return copy.deepcopy(report)|{'cohort_id':query['cohort_id'],'client':client,'filters':{'client_token':query['client_token']},
                                      'visibility':'private','public_release_approved':False}
