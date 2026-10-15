import copy
import threading
from pathlib import Path
from .exposure_convergence import methods,verify
from .exposure_movements import guard
from .workspace import sha256


class ExposureConvergenceViews:
    def __init__(self,root):
        self.root=root; self.cache={}; self.lock=threading.RLock(); self.methods={**methods(),'serving':sha256(Path(__file__))}

    def evidence(self,identifier):
        if self.methods!={**methods(),'serving':sha256(Path(__file__))}: raise ValueError('Convergence methods changed')
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report=verify(self.root,identifier)
                pins={**receipt['inputs_sha256'],**{str((folder/n).relative_to(self.root)):d for n,d in receipt['outputs_sha256'].items()}}
                pins[str((folder/'convergence-complete.json').relative_to(self.root))]=sha256(folder/'convergence-complete.json')
                self.cache[identifier]=(receipt,report,pins)
            receipt,report,pins=self.cache[identifier]; guard(self.root,pins)
            return copy.deepcopy(report)

    def catalog(self,source):
        results=[]
        for path in (self.root/'artifacts/private').glob('exposure-convergence-*/convergence-complete.json'):
            try:
                report=self.evidence(path.parent.name)
                if report['source_import_id']==source: results.append({'convergence_id':path.parent.name,'tail_id':report['tail_id']})
            except (ValueError,KeyError,OSError,TypeError): continue
        return {'source_import_id':source,'studies':results}

    def report(self,query):
        if set(query)-{'convergence_id','source_import_id','currency'} or not {'convergence_id','source_import_id'}<=set(query): raise ValueError('Source-bound convergence query required')
        report=self.evidence(query['convergence_id'])
        if report['source_import_id']!=query['source_import_id']: raise ValueError('Convergence source mismatch')
        currency=query.get('currency','all'); currencies={r['currency'] for r in report['diagnostics']}
        if currency!='all' and currency not in currencies: raise ValueError('Unknown currency')
        report['diagnostics']=[r for r in report['diagnostics'] if currency=='all' or r['currency']==currency]
        for run in report['runs']: run['results']=[r for r in run['results'] if currency=='all' or r['currency']==currency]
        report.update(convergence_id=query['convergence_id'],filters={'currency':currency}); return report
