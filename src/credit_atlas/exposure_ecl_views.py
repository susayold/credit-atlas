"""Verified private aggregate research cash-shortfall workbench."""
import copy
import threading
from pathlib import Path
from .exposure_ecl import methods,verify
from .exposure_movements import guard
from .workspace import sha256


class ExposureEclViews:
    def __init__(self,root):
        self.root=root; self.cache={}; self.lock=threading.RLock(); self.methods={**methods(),'serving':sha256(Path(__file__))}

    def evidence(self,identifier):
        if self.methods!={**methods(),'serving':sha256(Path(__file__))}: raise ValueError('ECL methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report=verify(self.root,identifier)
                pins={**receipt['inputs_sha256'],**{str((folder/n).relative_to(self.root)):d for n,d in receipt['outputs_sha256'].items()}}
                pins[str((folder/'ecl-complete.json').relative_to(self.root))]=sha256(folder/'ecl-complete.json')
                self.cache[identifier]=(receipt,report,pins)
            receipt,report,pins=self.cache[identifier]; guard(self.root,pins)
            return copy.deepcopy(receipt),copy.deepcopy(report)

    def catalog(self,source_id):
        result=[]
        for path in (self.root/'artifacts/private').glob('exposure-ecl-*/ecl-complete.json'):
            try:
                receipt,report=self.evidence(path.parent.name)
                if receipt['source_import_id']==source_id:
                    result.append({'ecl_id':receipt['ecl_id'],'name':report['name'],'version':report['version'],'completed_at':receipt['completed_at'],'status':'verified'})
            except (ValueError,OSError,KeyError,TypeError): continue
        return {'source_import_id':source_id,'ecl_studies':sorted(result,key=lambda r:r['completed_at'],reverse=True)}

    def report(self,query):
        if not isinstance(query,dict) or set(query)-{'ecl_id','source_import_id','currency','dimension'} or not {'ecl_id','source_import_id'}<=set(query):
            raise ValueError('ECL requires ecl_id/source_import_id, optional currency/dimension only')
        receipt,report=self.evidence(query['ecl_id'])
        if receipt['source_import_id']!=query['source_import_id']: raise ValueError('ECL source binding mismatch')
        c=query.get('currency','all'); d=query.get('dimension','stage')
        if c!='all' and c not in [r['currency'] for r in report['scope']]: raise ValueError('Unknown ECL currency')
        if d not in ('stage','region','segment'): raise ValueError('Unknown ECL dimension')
        report['scope']=[r for r in report['scope'] if c=='all' or r['currency']==c]
        def selected(rows): return [r for r in rows if (c=='all' or r['currency']==c) and r['dimension'] in ('total',d)]
        report['probability_weighted_aggregates']=selected(report['probability_weighted_aggregates'])
        for s in report['scenarios']: s['aggregates']=selected(s['aggregates'])
        report.update(ecl_id=receipt['ecl_id'],filters={'currency':c,'dimension':d},stage_assessment_scope='Whole declared segment model; not currency-specific fitted assessments')
        return report
