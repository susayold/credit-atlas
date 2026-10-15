"""Verified private aggregate Monte Carlo views; raw draws never served."""
import copy
import threading
from pathlib import Path
from .exposure_tail import methods,verify
from .exposure_movements import guard
from .workspace import sha256


class ExposureTailViews:
    def __init__(self,root):
        self.root=root; self.cache={}; self.lock=threading.RLock()
        self.methods={**methods(),'serving':sha256(Path(__file__))}

    def evidence(self,identifier):
        if self.methods!={**methods(),'serving':sha256(Path(__file__))}:
            raise ValueError('Tail methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report=verify(self.root,identifier)
                pins={**receipt['inputs_sha256'],**{str((folder/n).relative_to(self.root)):d for n,d in receipt['outputs_sha256'].items()}}
                pins[str((folder/'tail-complete.json').relative_to(self.root))]=sha256(folder/'tail-complete.json')
                self.cache[identifier]=(receipt,report,pins)
            receipt,report,pins=self.cache[identifier]; guard(self.root,pins)
            return copy.deepcopy(receipt),copy.deepcopy(report)

    def catalog(self,source_id):
        result=[]
        for path in (self.root/'artifacts/private').glob('exposure-tail-*/tail-complete.json'):
            try:
                receipt,report=self.evidence(path.parent.name)
                if receipt['source_import_id']==source_id:
                    result.append({'tail_id':receipt['tail_id'],'name':report['name'],'version':report['version'],
                        'completed_at':receipt['completed_at'],'status':'verified'})
            except (ValueError,OSError,KeyError,TypeError): continue
        return {'source_import_id':source_id,'tail_studies':sorted(result,key=lambda r:r['completed_at'],reverse=True)}

    def report(self,query):
        if not isinstance(query,dict) or set(query)-{'tail_id','source_import_id','currency'} or not {'tail_id','source_import_id'}<=set(query):
            raise ValueError('Tail requires tail_id/source_import_id, optional currency only')
        receipt,report=self.evidence(query['tail_id'])
        if receipt['source_import_id']!=query['source_import_id']: raise ValueError('Tail source binding mismatch')
        currency=query.get('currency','all')
        if currency!='all' and currency not in [r['currency'] for r in report['scope']]: raise ValueError('Unknown tail currency')
        for key in ('scope','results'): report[key]=[r for r in report[key] if currency=='all' or r['currency']==currency]
        report.update(tail_id=receipt['tail_id'],filters={'currency':currency})
        return report
