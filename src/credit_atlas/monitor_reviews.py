"""Private analyst reviews: immutable captured context and atomic revisions."""
import copy
import hashlib
import json
import re
import sqlite3
import uuid
from .reviews import ReviewConflict
from .runtime_state import SQLiteRuntimeState
from .workspace import timestamp


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class MonitorReviews:
    def __init__(self, service):
        self.service = service
        path = None if service.ephemeral_state else service.root / 'artifacts/private/monitor-reviews.sqlite3'
        self._db = SQLiteRuntimeState(path, "monitor-reviews")
        self.path = self._db.path
        with self.connect() as db:
            db.executescript('''PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,domain TEXT NOT NULL,revision INTEGER NOT NULL,record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history(id TEXT NOT NULL,revision INTEGER NOT NULL,record TEXT NOT NULL,PRIMARY KEY(id,revision));''')

    def connect(self):
        return self._db.connect(timeout=10)

    def list(self, domain):
        if domain not in {'P1','P2','P3','P4','P5'}:
            raise ValueError('Unsupported review domain')
        with self.connect() as db:
            return {'reviews': [json.loads(x[0]) for x in db.execute('SELECT record FROM reviews WHERE domain=? ORDER BY rowid DESC', [domain])], 'visibility':'private'}

    def report(self, identifier):
        if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]{32}',identifier):
            raise ValueError('Invalid review identifier')
        with self.connect() as db:
            rows=[json.loads(x[0]) for x in db.execute('SELECT record FROM history WHERE id=? ORDER BY revision',[identifier])]
        if not rows:
            raise KeyError('Review not found')
        return {'review': rows[-1], 'history': rows, 'visibility':'private', 'public_release_approved':False}

    def capture(self, snapshot):
        if not isinstance(snapshot,dict) or set(snapshot)!={'domain','scope','metrics','quality_metrics','filters','comparison_control','evidence_refs'}:
            raise ValueError('Bounded KPI context required')
        domain=snapshot['domain']; allowed={'P1':{'suite','policy','source_quality'},'P2':{'run'},'P3':{'suite','sec'},'P4':{'exposure'},'P5':{'abs'}}
        if domain not in allowed or len(encoded(snapshot).encode('utf-8'))>48000:
            raise ValueError('Invalid KPI context scope/size')
        if not isinstance(snapshot['metrics'],list) or not 1<=len(snapshot['metrics'])<=40 or not isinstance(snapshot['quality_metrics'],list) or len(snapshot['quality_metrics'])>30:
            raise ValueError('Bounded KPI metrics required')
        if not isinstance(snapshot['scope'],str) or len(snapshot['scope'])>1000 or not isinstance(snapshot['filters'],dict):
            raise ValueError('Invalid KPI scope/filters')
        refs=snapshot['evidence_refs']
        if not isinstance(refs,list) or not 1<=len(refs)<=6:
            raise ValueError('Source references required')
        captures=[]
        for ref in refs:
            if not isinstance(ref,dict) or set(ref)!={'kind','id'} or ref['kind'] not in allowed[domain] or not isinstance(ref['id'],str):
                raise ValueError('Unsupported source reference')
            kind,identifier=ref['kind'],ref['id']
            if kind=='suite': data=self.service.suite_views.view(identifier)
            elif kind=='run': data=self.service.snapshot(identifier)
            elif kind=='sec': data=self.service.sec_views.view(identifier)
            elif kind=='abs': data=self.service.abs_views.view(identifier)
            elif kind=='source_quality':
                if not any(r == {'kind':'suite','id':identifier} for r in refs):
                    raise ValueError('Source quality requires the same suite scope')
                from .retail_source_quality import report
                data=report(self.service.suite_views,identifier)
            elif kind=='policy':
                suite=next((r['id'] for r in refs if r.get('kind')=='suite'),None)
                if not suite: raise ValueError('Policy requires suite model scope')
                freeze=self.service.suite_views.view(suite)['retail']['freeze_id']
                data=self.service.retail_policy_views.report({'policy_id':identifier,'freeze_id':freeze})
            else: data=self.service.exposure_views.report({'import_id':identifier,'currency':'USD','dimension':'region'})
            captures.append({**ref,'verified_source_sha256':hashlib.sha256(encoded(data).encode('utf-8')).hexdigest()})
        primary={'P1':'suite','P2':'run','P3':'suite','P4':'exposure','P5':'abs'}[domain]
        if not any(x['kind']==primary for x in refs):
            raise ValueError('Primary domain source required')
        return {'snapshot':copy.deepcopy(snapshot),'snapshot_sha256':hashlib.sha256(encoded(snapshot).encode('utf-8')).hexdigest(),
                'source_capture':captures,'captured_at':timestamp(),
                'calculation_scope':'Browser-derived KPI context; source artifacts verified at capture; server does not independently recompute every displayed KPI',
                'credit_decision_approved':False}

    def save(self, payload):
        if not isinstance(payload,dict) or set(payload)-{'id','revision','title','owner','judgement','hypothesis','next_action','status','snapshot'}:
            raise ValueError('Invalid review fields')
        texts={}
        for key,limit,required in [('title',200,True),('owner',100,True),('judgement',5000,True),('hypothesis',5000,False),('next_action',5000,True)]:
            v=payload.get(key,'')
            if not isinstance(v,str) or len(v)>limit or (required and not v.strip()):
                raise ValueError('Invalid review '+key)
            texts[key]=v.strip()
        status=payload.get('status','draft')
        if status not in {'draft','reviewed','archived'}:
            raise ValueError('Invalid analyst review status')
        identifier=payload.get('id')
        if identifier and (not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]{32}',identifier)):
            raise ValueError('Invalid review identifier')
        capture=None if identifier else self.capture(payload.get('snapshot'))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=None
            if identifier:
                found=db.execute('SELECT record FROM reviews WHERE id=?',[identifier]).fetchone()
                if not found: raise KeyError('Review not found')
                current=json.loads(found[0])
                if type(payload.get('revision')) is not int or payload['revision']!=current['revision']:
                    raise ReviewConflict('Review changed; reload latest revision')
                if 'snapshot' in payload:
                    raise ValueError('Captured evidence is immutable; create a new review for new evidence')
                capture=current['capture']
            identifier=identifier or uuid.uuid4().hex
            record={'id':identifier,'domain':capture['snapshot']['domain'],'revision':current['revision']+1 if current else 1,
                    **texts,'status':status,'capture':capture,'created_at':current['created_at'] if current else timestamp(),
                    'updated_at':timestamp(),'visibility':'private','public_release_approved':False}
            serialized=encoded(record)
            db.execute('INSERT INTO reviews VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,record=excluded.record',[identifier,record['domain'],record['revision'],serialized])
            db.execute('INSERT INTO history VALUES(?,?,?)',[identifier,record['revision'],serialized])
        return record
