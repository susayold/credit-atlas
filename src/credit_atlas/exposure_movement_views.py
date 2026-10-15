"""Verified private bridge aggregates; all source pins guarded on each read."""
import copy
import threading
from pathlib import Path
from .exposure_movements import DIMENSIONS, guard, methods, verify
from .workspace import contained, sha256


class ExposureMovementViews:
    def __init__(self, root):
        self.root=root; self.cache={}; self.lock=threading.RLock()
        self.methods={**methods(), 'serving':sha256(Path(__file__))}

    def evidence(self, identifier):
        if self.methods != {**methods(), 'serving':sha256(Path(__file__))}: raise ValueError('Bridge methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report=verify(self.root,identifier)
                pins={**receipt['inputs_sha256'],str((folder/'report.json').relative_to(self.root)):receipt['report_sha256'],
                      str((folder/'movement-complete.json').relative_to(self.root)):sha256(folder/'movement-complete.json')}
                self.cache[identifier]=(receipt,report,pins)
            receipt,report,pins=self.cache[identifier]; guard(self.root,pins)
            return copy.deepcopy(receipt),copy.deepcopy(report)

    def catalog(self, closing_id):
        result=[]
        for path in (self.root/'artifacts/private').glob('exposure-movement-*/movement-complete.json'):
            try:
                receipt,report=self.evidence(path.parent.name)
                if receipt['closing_import_id'] == closing_id:
                    result.append({'movement_id':receipt['movement_id'],'opening_as_of':report['opening_as_of'],
                        'closing_as_of':report['closing_as_of'],'status':'verified','completed_at':receipt['completed_at']})
            except (ValueError,OSError,KeyError,TypeError): continue
        return {'closing_import_id':closing_id,'movements':sorted(result,key=lambda r:r['completed_at'],reverse=True)}

    def report(self, query):
        if not isinstance(query,dict) or set(query)-{'movement_id','closing_import_id','dimension','currency'} or not {'movement_id','closing_import_id'}<=set(query):
            raise ValueError('Bridge requires movement_id/closing_import_id; optional dimension/currency only')
        receipt,report=self.evidence(query['movement_id'])
        if receipt['closing_import_id'] != query['closing_import_id']: raise ValueError('Bridge does not belong to selected closing import')
        dimension=query.get('dimension','region'); currency=query.get('currency','all')
        if dimension not in DIMENSIONS: raise ValueError('Unknown bridge dimension')
        if currency!='all' and currency not in [r['currency'] for r in report['currencies']]: raise ValueError('Currency not present in bridge')
        report['currencies']=[r for r in report['currencies'] if currency=='all' or r['currency']==currency]
        for field in ('groups','transitions'):
            report[field]=[r for r in report[field] if r['dimension']==dimension and (currency=='all' or r['currency']==currency)]
        report.update(movement_id=receipt['movement_id'],opening_import_id=receipt['opening_import_id'],closing_import_id=receipt['closing_import_id'],
                      filters={'currency':currency,'dimension':dimension},identity_counts_scope='Whole pair, independent of currency filter')
        return report
