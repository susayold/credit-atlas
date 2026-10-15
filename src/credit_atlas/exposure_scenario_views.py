"""Private aggregate-only scenario comparison with source binding on every read."""
import copy
import threading
from pathlib import Path
from .exposure_movements import guard
from .exposure_scenarios import DIMENSIONS,methods,verify
from .workspace import sha256


class ExposureScenarioViews:
    def __init__(self,root):
        self.root=root; self.cache={}; self.lock=threading.RLock()
        self.methods={**methods(),'serving':sha256(Path(__file__))}

    def evidence(self,identifier):
        if self.methods!={**methods(),'serving':sha256(Path(__file__))}: raise ValueError('Scenario methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report=verify(self.root,identifier)
                pins={**receipt['inputs_sha256'],**{str((folder/n).relative_to(self.root)):d for n,d in receipt['outputs_sha256'].items()}}
                pins[str((folder/'scenario-complete.json').relative_to(self.root))]=sha256(folder/'scenario-complete.json')
                self.cache[identifier]=(receipt,report,pins)
            receipt,report,pins=self.cache[identifier]; guard(self.root,pins)
            return copy.deepcopy(receipt),copy.deepcopy(report)

    def catalog(self,source_id):
        result=[]
        for path in (self.root/'artifacts/private').glob('exposure-scenario-*/scenario-complete.json'):
            try:
                receipt,report=self.evidence(path.parent.name)
                if receipt['source_import_id']==source_id:
                    result.append({'scenario_id':receipt['scenario_id'],'name':report['name'],'version':report['version'],
                        'completed_at':receipt['completed_at'],'status':'verified'})
            except (ValueError,OSError,KeyError,TypeError): continue
        return {'source_import_id':source_id,'scenario_sets':sorted(result,key=lambda r:r['completed_at'],reverse=True)}

    def report(self,query):
        if not isinstance(query,dict) or set(query)-{'scenario_id','source_import_id','currency','dimension'} or not {'scenario_id','source_import_id'}<=set(query):
            raise ValueError('Scenario requires scenario_id/source_import_id with optional currency/dimension only')
        receipt,report=self.evidence(query['scenario_id'])
        if receipt['source_import_id']!=query['source_import_id']: raise ValueError('Scenario does not belong to selected import')
        c=query.get('currency','all'); dim=query.get('dimension','segment')
        if c!='all' and c not in [r['currency'] for r in report['scope']]: raise ValueError('Unknown scenario source currency')
        if dim not in DIMENSIONS: raise ValueError('Unsupported scenario concentration dimension')
        for key in ('scope','exclusions'): report[key]=[r for r in report[key] if c=='all' or r['currency']==c]
        for scenario in report['scenarios']:
            scenario['aggregates']=[r for r in scenario['aggregates'] if r['dimension'] in ('total',dim) and (c=='all' or r['currency']==c)]
        report.update(scenario_id=receipt['scenario_id'],filters={'currency':c,'dimension':dim})
        return report
