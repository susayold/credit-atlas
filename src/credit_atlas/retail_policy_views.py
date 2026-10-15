import copy
import re
import threading
from pathlib import Path
import hashlib
import pyarrow as pa
import pyarrow.parquet as pq
from .retail_policy import calculate,methods,number,validate
from .retail_policy_saved import build_saved,verify_saved
verify=verify_saved
from .workspace import contained,read_json,sha256

def lineage_pins(root,report):
    """Capture the complete verified freeze graph, including acquisition files."""
    pins=dict(report['inputs_sha256'])
    freeze_folder=contained(root,'artifacts/private/'+report['freeze_id'])
    frozen=read_json(freeze_folder/'freeze-complete.json')
    specs=[(freeze_folder,'freeze-complete.json','retail_freeze',None),
        (contained(root,'artifacts/private/'+frozen['comparison_id']),'comparison-complete.json','retail_comparison',frozen['comparison_receipt_sha256']),
        (contained(root,'artifacts/private/'+frozen['assessment_id']),'assessment-complete.json','retail_assessment',frozen['assessment_receipt_sha256']),
        (contained(root,'artifacts/private/'+frozen['feature_id']),'features-complete.json','retail_features',frozen['feature_receipt_sha256']),
        (contained(root,'artifacts/private/'+frozen['case_id']),'case-complete.json','retail',frozen['case_receipt_sha256'])]
    def pin(path,expected=None):
        digest=sha256(path)
        if expected is not None and expected!=digest: raise ValueError('Verified policy lineage changed')
        key=str(path.relative_to(root))
        if key in pins and pins[key]!=digest: raise ValueError('Verified policy input changed')
        pins[key]=digest
    case=None
    for folder,name,module,digest in specs:
        pin(folder/name,digest); receipt=read_json(folder/name)
        pin(Path(__file__).with_name(module+'.py'),receipt['method_source_sha256'])
        for output,expected in receipt['outputs_sha256'].items(): pin(contained(root,str((folder/output).relative_to(root))),expected)
        if module=='retail': case=receipt
    acquisition=contained(root,'data/private/public-suite/'+case['suite_id'])
    pin(acquisition/'acquisition-complete.json',case['source_receipt_sha256'])
    for record in read_json(acquisition/'acquisition-complete.json')['sources']:
        per_source=acquisition/(record['source_id']+'-receipt.json')
        if read_json(per_source)!=record: raise ValueError('Acquisition source receipt changed')
        pin(per_source)
        if record['status']=='DOWNLOADED_AND_PROFILED': pin(contained(root,str((acquisition/record['file']).relative_to(root))),record['sha256'])
    for module in ('workspace','public_suite','public_sources'): pin(Path(__file__).with_name(module+'.py'))
    return pins

def pinned_scores(root,report):
    path=contained(root,'artifacts/private/'+report['assessment_id']+'/private-validation-scores.parquet')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=report['inputs_sha256'][str(path.relative_to(root))]: raise ValueError('Policy score snapshot changed')
    column=report['selected_variant']+'_probability'
    return [{'source_client_id':r['source_client_id'],'target':r['target'],'probability':r[column]}
        for r in pq.read_table(pa.BufferReader(raw)).to_pylist() if r['model']==report['selected_model']]

class RetailPolicyViews:
    def __init__(self,root,storage_root=None):
        from .retail_policy_saved import storage
        self.root=root; self.storage_root=storage(root,storage_root); self.lock=threading.RLock(); self.method={**methods(),'serving':sha256(Path(__file__)),'saved_verifier':sha256(Path(__file__).with_name('retail_policy_saved.py'))}; self.cache={}

    def guard(self):
        if self.method!={**methods(),'serving':sha256(Path(__file__)),'saved_verifier':sha256(Path(__file__).with_name('retail_policy_saved.py'))}: raise ValueError('Policy serving method changed; restart required')

    def evidence(self,identifier):
        self.guard()
        with self.lock:
            if identifier not in self.cache:
                folder,receipt,report=verify(self.root,identifier,self.storage_root)
                pins=lineage_pins(self.root,report)
                pins[str((folder/'policy-complete.json').relative_to(self.root))]=sha256(folder/'policy-complete.json')
                pins.update({str((folder/name).relative_to(self.root)):digest for name,digest in receipt['outputs_sha256'].items()})
                rows=pinned_scores(self.root,report)
                self.cache[identifier]=(copy.deepcopy(receipt),copy.deepcopy(report),rows,pins)
            receipt,report,rows,pins=self.cache[identifier]
            self.guard()
            if any(sha256(contained(self.root,path))!=digest for path,digest in pins.items()): raise ValueError('Policy cached evidence changed')
            return copy.deepcopy(receipt),copy.deepcopy(report),copy.deepcopy(rows)

    def catalog(self,freeze):
        if not isinstance(freeze,str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}',freeze): raise ValueError('Valid frozen model required')
        self.guard(); studies=[]
        for path in self.storage_root.glob('retail-policy-*/policy-complete.json'):
            try:
                receipt,report,_=self.evidence(path.parent.name)
                if receipt['freeze_id']==freeze: studies.append({'policy_id':path.parent.name,'completed_at':receipt['completed_at'],'records':report['records']})
            except (OSError,ValueError,KeyError,TypeError): continue
        return {'freeze_id':freeze,'policies':sorted(studies,key=lambda r:r['completed_at'],reverse=True)}

    def report(self,query):
        if set(query)!={'policy_id','freeze_id'}: raise ValueError('Policy and frozen-model scope required')
        self.guard(); receipt,report,_=self.evidence(query['policy_id'])
        if receipt['freeze_id']!=query['freeze_id']: raise ValueError('Policy frozen-model mismatch')
        self.guard(); return copy.deepcopy(report)|{'policy_id':query['policy_id'],'visibility':'private','public_release_approved':False}

    def preview(self,query):
        required={'policy_id','freeze_id','lower_threshold','upper_threshold','review_capacity'}|{a+'_'+y for a in ('accept','review','decline') for y in ('non_event','event')}
        if set(query)!=required: raise ValueError('Exact declared policy preview required')
        base=self.report({k:query[k] for k in ('policy_id','freeze_id')}); plan=base['assumptions']
        capacity=query['review_capacity']
        if capacity!='' and (not isinstance(capacity,str) or not capacity.isascii() or not capacity.isdigit() or len(capacity)>5): raise ValueError('Integer review capacity required')
        plan.update(review_capacity=None if capacity=='' else int(capacity),cases=[{'id':'preview','lower_threshold':query['lower_threshold'],'upper_threshold':query['upper_threshold']}],
            cost_matrix={a:{y:query[a+'_'+y] for y in ('non_event','event')} for a in ('accept','review','decline')})
        _,current,scores=self.evidence(query['policy_id'])
        lineage={k:current[k] for k in ('freeze_id','case_id','assessment_id','selected_model','selected_variant','inputs_sha256')}
        report=calculate(scores,validate(plan))|lineage
        self.guard()
        if lineage['inputs_sha256']!=base['inputs_sha256']: raise ValueError('Policy preview source changed')
        self.evidence(query['policy_id'])
        return report|{'status':'UNSAVED_POLICY_PREVIEW','parent_policy_id':query['policy_id'],'visibility':'private','public_release_approved':False}

    def save(self,plan):
        self.guard()
        with self.lock:
            result=build_saved(self.root,plan,self.storage_root); self.guard(); return result
