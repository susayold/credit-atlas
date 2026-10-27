"""Private, versioned source-bound review packages; no source/model overrides."""
import json
import re
import sqlite3
import uuid
from datetime import date,datetime,timezone
from .reviews import ReviewConflict
from .runtime_state import SQLiteRuntimeState
from .workspace import timestamp


class PortfolioReviews:
    def __init__(self,service,path):
        self.service=service; self._db=SQLiteRuntimeState(path,"portfolio-reviews"); self.path=self._db.path
        with self.connect() as db:
            db.executescript('''PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS packages(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,revision INTEGER NOT NULL,record_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history(id TEXT NOT NULL,revision INTEGER NOT NULL,record_json TEXT NOT NULL,PRIMARY KEY(id,revision));''')

    def connect(self): return self._db.connect(timeout=10)

    def evidence(self,source,currency,refs):
        source_report=self.service.exposure_views.report({'import_id':source,'currency':currency,'dimension':'region'})
        snapshots={'inventory':source_report}
        kinds={'scenario':(self.service.exposure_scenario_views,'scenario_id'),
            'ecl':(self.service.exposure_ecl_views,'ecl_id'),'tail':(self.service.exposure_tail_views,'tail_id')}
        for ref in refs:
            view,key=kinds[ref['kind']]
            query={key:ref['id'],'source_import_id':source,'currency':currency}
            snapshots[ref['kind']+':'+ref['id']]=view.report(query)
        return snapshots

    def save(self,payload):
        required={'source_import_id','title','rationale','owner','expires_on','status','currency','assumptions_acknowledged','evidence_refs'}
        if not isinstance(payload,dict) or set(payload)-required-{'id','revision'} or not required<=set(payload): raise ValueError('Explicit review package required')
        for key,limit in [('title',200),('rationale',10000),('owner',200)]:
            if not isinstance(payload[key],str) or not 1<=len(payload[key].strip())<=limit: raise ValueError('Bounded review text required')
        if payload['status'] not in ('draft','reviewed','archived') or type(payload['assumptions_acknowledged']) is not bool:
            raise ValueError('Research review status required')
        expiry=date.fromisoformat(payload['expires_on'])
        if expiry.isoformat()!=payload['expires_on']: raise ValueError('ISO expiry date required')
        if payload['status']=='reviewed' and (not payload['assumptions_acknowledged'] or expiry<datetime.now(timezone.utc).date()):
            raise ValueError('Reviewed package requires assumption acknowledgement and unexpired date')
        refs=payload['evidence_refs']
        if not isinstance(refs,list) or not 1<=len(refs)<=8: raise ValueError('One to eight typed evidence references required')
        seen=set()
        for ref in refs:
            if not isinstance(ref,dict) or set(ref)!={'kind','id'} or ref['kind'] not in ('scenario','ecl','tail') or not isinstance(ref['id'],str): raise ValueError('Unknown review evidence')
            key=(ref['kind'],ref['id'])
            if key in seen: raise ValueError('Duplicate review evidence')
            seen.add(key)
        snapshots=self.evidence(payload['source_import_id'],payload['currency'],refs)
        identifier=payload.get('id') or 'portfolio-review-'+uuid.uuid4().hex[:12]
        if not re.fullmatch('portfolio-review-[0-9a-f]{12}',identifier): raise ValueError('Invalid review ID')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE'); row=db.execute('SELECT source_id,revision,record_json FROM packages WHERE id=?',[identifier]).fetchone()
            if payload.get('id'):
                if not row or row[0]!=payload['source_import_id']: raise KeyError('Review not in source snapshot')
                if type(payload.get('revision')) is not int or payload['revision']!=row[1]: raise ReviewConflict('Review revision changed')
            elif 'revision' in payload: raise ValueError('Creation does not accept revision')
            now=timestamp(); revision=row[1]+1 if row else 1
            record={k:payload[k] for k in required}
            record.update(id=identifier,revision=revision,created_at=json.loads(row[2])['created_at'] if row else now,updated_at=now,
                snapshots=snapshots,visibility='private',public_release_approved=False,
                qualification={'accounting_approved':False,'capital_approved':False,'model_calibrated':False,'review_is_research_annotation':True})
            # Recheck while transaction is held: changed evidence rolls back.
            if snapshots!=self.evidence(payload['source_import_id'],payload['currency'],refs): raise ValueError('Review evidence changed during save')
            encoded=json.dumps(record,ensure_ascii=False,allow_nan=False)
            db.execute('INSERT INTO packages VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,record_json=excluded.record_json',[identifier,payload['source_import_id'],revision,encoded])
            db.execute('INSERT INTO history VALUES(?,?,?)',[identifier,revision,encoded])
        return record

    def list(self,source):
        self.service.exposure_views.report({'import_id':source})
        with self.connect() as db: records=[json.loads(r[0]) for r in db.execute('SELECT record_json FROM packages WHERE source_id=? ORDER BY id',[source])]
        summaries=[]
        for record in records:
            try: current=record['snapshots']==self.evidence(source,record['currency'],record['evidence_refs'])
            except (ValueError,KeyError,OSError): current=False
            summaries.append({k:record[k] for k in ('id','revision','title','owner','expires_on','status','updated_at')}|{
                'evidence_current':current,'expired':date.fromisoformat(record['expires_on'])<datetime.now(timezone.utc).date()})
        return {'source_import_id':source,'packages':summaries,'visibility':'private','public_release_approved':False}

    def report(self,source,identifier,revision=None):
        if not isinstance(identifier,str) or not re.fullmatch('portfolio-review-[0-9a-f]{12}',identifier): raise ValueError('Invalid review ID')
        with self.connect() as db:
            row=db.execute('SELECT source_id,record_json FROM packages WHERE id=?',[identifier]).fetchone()
            if not row or row[0]!=source: raise KeyError('Review not in source')
            if revision is not None:
                if type(revision) is not int or revision<1: raise ValueError('Positive review revision required')
                version=db.execute('SELECT record_json FROM history WHERE id=? AND revision=?',[identifier,revision]).fetchone()
                if not version: raise KeyError('Unknown review revision')
                record=json.loads(version[0])
            else: record=json.loads(row[1])
        if record['snapshots']!=self.evidence(source,record['currency'],record['evidence_refs']): raise ValueError('Review evidence no longer matches saved snapshot')
        record.update(expired=date.fromisoformat(record['expires_on'])<datetime.now(timezone.utc).date(),evidence_current=True)
        return record
