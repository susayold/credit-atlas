import copy
import re
import threading
from pathlib import Path
from .retail_subgroups import guard,methods
from .retail_subgroups_saved import build_saved_subgroups,verify_saved_subgroups
from .retail_policy_saved import storage
from .workspace import sha256

class RetailSubgroupViews:
    def __init__(self,root,storage_root=None,policy_storage=None):
        self.root=root;self.storage_root=storage(root,storage_root);self.policy_storage=storage(root,policy_storage);self.lock=threading.RLock();self.cache={};self.methods=self.current_methods()
    def current_methods(self):
        return {**methods(),'serving':sha256(Path(__file__)),'saved_verifier':sha256(Path(__file__).with_name('retail_subgroups_saved.py')),'saved_policy_verifier':sha256(Path(__file__).with_name('retail_policy_saved.py'))}
    def evidence(self,identifier):
        if self.methods!=self.current_methods(): raise ValueError('Subgroup serving methods changed')
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report=verify_saved_subgroups(self.root,identifier,self.storage_root,self.policy_storage)
                pins={**receipt['inputs_sha256'],**{str((folder/n).relative_to(self.root)):h for n,h in receipt['outputs_sha256'].items()}}
                pins[str((folder/'subgroups-complete.json').relative_to(self.root))]=sha256(folder/'subgroups-complete.json')
                self.cache[identifier]=(report,pins)
            report,pins=self.cache[identifier];guard(self.root,pins);return copy.deepcopy(report)
    def catalog(self,query):
        if set(query)!={'policy_id','freeze_id'}: raise ValueError('Policy/freeze-bound subgroup catalog required')
        if not re.fullmatch(r'retail-policy-[0-9a-f]{12}',query['policy_id']) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}',query['freeze_id']): raise ValueError('Valid source identifiers required')
        records=[]
        for path in self.storage_root.glob('retail-subgroups-*/subgroups-complete.json'):
            try:
                report=self.evidence(path.parent.name);plan=report['assumptions']
                if plan['policy_id']==query['policy_id'] and plan['freeze_id']==query['freeze_id']:
                    records.append({'subgroups_id':path.parent.name,'case_id':plan['case_id'],'dimensions':plan['dimensions']})
            except (ValueError,KeyError,OSError,TypeError): continue
        return {'studies':records,**query}
    def report(self,query):
        if set(query)-{'subgroups_id','policy_id','freeze_id','dimension'} or not {'subgroups_id','policy_id','freeze_id'}<=set(query): raise ValueError('Bound subgroup report required')
        report=self.evidence(query['subgroups_id']);plan=report['assumptions']
        if any(query[k]!=plan[k] for k in ('policy_id','freeze_id')): raise ValueError('Subgroup source mismatch')
        dimension=query.get('dimension',plan['dimensions'][0])
        if dimension not in plan['dimensions']: raise ValueError('Unsupported subgroup dimension')
        report['groups']=[r for r in report['groups'] if r['dimension']==dimension]
        report.update(subgroups_id=query['subgroups_id'],filters={'dimension':dimension},visibility='private',public_release_approved=False);return report
    def save(self,plan):
        if self.methods!=self.current_methods(): raise ValueError('Subgroup methods changed')
        with self.lock:
            result=build_saved_subgroups(self.root,plan,self.storage_root,self.policy_storage)
            if self.methods!=self.current_methods(): raise ValueError('Subgroup methods changed during save')
            return result
