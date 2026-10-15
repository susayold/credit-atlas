"""Issuer financial memos with server-derived immutable evidence and revisions."""
import hashlib
import json
import re
import sqlite3
import uuid
from .reviews import ReviewConflict
from .sec_trends import report as trend_report
from .sec_coverage import report as coverage_report,INTEREST_CONCEPTS
from .sec_debt import report as debt_report,CONCEPTS as DEBT_CONCEPTS
from .workspace import timestamp

SECTIONS=('business_summary','liquidity','leverage','profitability','cashflow','risks','missing_information','conclusion','next_action')


def encoded(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False)


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{32}',value):raise ValueError('Invalid memo ID')
    return value


class CorporateMemos:
    def __init__(self,service):
        self.service=service
        self.path=service.root/'artifacts/private/corporate-memos.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS memos(id TEXT PRIMARY KEY,view_id TEXT NOT NULL,cik TEXT NOT NULL,revision INTEGER NOT NULL,record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history(id TEXT NOT NULL,revision INTEGER NOT NULL,record TEXT NOT NULL,PRIMARY KEY(id,revision));''')

    def connect(self):return sqlite3.connect(self.path,timeout=10)

    def list(self,query):
        if set(query)!={'view_id','cik'} or not isinstance(query['view_id'],str) or not re.fullmatch(r'sec-view-[0-9a-f]{12}',query['view_id']) or not isinstance(query['cik'],str) or not re.fullmatch(r'\d{10}',query['cik']):
            raise ValueError('Explicit SEC view/CIK scope required')
        # Existing records remain readable even if current source verification fails.
        with self.connect() as db:
            records=[json.loads(r[0]) for r in db.execute('SELECT record FROM memos WHERE view_id=? AND cik=? ORDER BY rowid DESC',[query['view_id'],query['cik']])]
        return {'memos':records,'visibility':'private','public_release_approved':False}

    def report(self,key):
        identifier(key)
        with self.connect() as db:rows=[json.loads(x[0]) for x in db.execute('SELECT record FROM history WHERE id=? ORDER BY revision',[key])]
        if not rows:raise KeyError('Memo not found')
        return {'memo':rows[-1],'history':rows,'visibility':'private','public_release_approved':False}

    def capture(self,scope):
        required={'view_id','cik','accession','asof','years'}
        if not isinstance(scope,dict) or not required<=set(scope) or set(scope)-required-{'interest_concept','debt_scope'} or any(not isinstance(v,str) or len(v)>64 for v in scope.values()):raise ValueError('Bounded SEC memo source scope required')
        scope={**scope,'interest_concept':scope.get('interest_concept','InterestExpenseNonoperating')}
        if scope['interest_concept'] not in INTEREST_CONCEPTS:raise ValueError('Explicit supported interest concept required')
        scope={**scope,'debt_scope':scope.get('debt_scope','debt_only')}
        if scope['debt_scope'] not in DEBT_CONCEPTS:raise ValueError('Explicit supported maturity scope required')
        views=self.service.sec_views
        report=views.report(scope['view_id'],{k:scope[k] for k in ['cik','accession','asof']})
        if not report['statement']:raise ValueError('Supported selected annual statement required')
        # Anchor history to the selected filing date; never add later filings to an older memo.
        trend=trend_report(views,scope['view_id'],{'cik':scope['cik'],'asof':report['statement']['filing_date'],'years':scope['years']})
        coverage=coverage_report(views,scope['view_id'],{'cik':scope['cik'],'asof':report['statement']['filing_date'],'years':scope['years'],'interest_concept':scope['interest_concept']})
        debt=debt_report(views,scope['view_id'],{'cik':scope['cik'],'accession':report['filters']['accession'],'asof':report['statement']['filing_date'],'debt_scope':scope['debt_scope']})
        evidence={'selected_filing':report,'annual_trend':trend,'interest_coverage':coverage,'debt_maturities':debt}
        return {'captured_at':timestamp(),'requested_scope':scope.copy(),'resolved_scope':{'view_id':scope['view_id'],'cik':report['filters']['cik'],'accession':report['filters']['accession'],'report_date':report['statement']['report_date'],'filing_date':report['statement']['filing_date'],'trend_cutoff':trend['filters']['asof'],'years':scope['years'],'interest_concept':scope['interest_concept'],'debt_scope':scope['debt_scope']},
                'evidence':evidence,'evidence_sha256':hashlib.sha256(encoded(evidence).encode('utf-8')).hexdigest(),
                'calculation_scope':'Server-derived selected filing, annual trend explicitly selected interest coverage and filing-specific principal maturity disclosure from verified SEC source artifacts; narrative is analyst input.',
                'qualification':{'credit_decision_approved':False,'issuer_pd_qualified':False,'dscr_supported':False,'covenant_compliance_supported':False,'historical_availability_qualified':False}}

    def save(self,payload):
        if not isinstance(payload,dict) or set(payload)-{'id','revision','title','owner','status','sections','scope'}:raise ValueError('Invalid memo fields')
        text={}
        for key,limit in [('title',200),('owner',100)]:
            value=payload.get(key)
            if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Required bounded '+key)
            text[key]=value.strip()
        sections=payload.get('sections')
        if not isinstance(sections,dict) or set(sections)!=set(SECTIONS) or any(not isinstance(v,str) or len(v)>5000 for v in sections.values()):raise ValueError('Required bounded memo sections')
        sections={k:v.strip() for k,v in sections.items()}
        if any(not sections[k] for k in ['business_summary','conclusion','next_action']):raise ValueError('Memo summary, conclusion and next action required')
        status=payload.get('status','draft')
        if status not in {'draft','reviewed','archived'}:raise ValueError('Invalid memo status')
        key=payload.get('id')
        if key:
            identifier(key)
            if 'scope' in payload:raise ValueError('Captured memo source is immutable')
            capture=None
        else:
            if 'id' in payload or 'revision' in payload:raise ValueError('New memo cannot supply revision or ID')
            capture=self.capture(payload.get('scope'))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=None
            if key:
                row=db.execute('SELECT record FROM memos WHERE id=?',[key]).fetchone()
                if not row:raise KeyError('Memo not found')
                current=json.loads(row[0])
                if type(payload.get('revision')) is not int or current['revision']!=payload['revision']:raise ReviewConflict('Memo changed; reload latest revision')
                capture=current['capture']
            key=key or uuid.uuid4().hex
            record={'id':key,**text,'status':status,'sections':sections,'capture':capture,'revision':current['revision']+1 if current else 1,
                    'created_at':current['created_at'] if current else timestamp(),'updated_at':timestamp(),'visibility':'private','public_release_approved':False}
            scope=capture['resolved_scope']
            db.execute('INSERT INTO memos VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,record=excluded.record',[key,scope['view_id'],scope['cik'],record['revision'],encoded(record)])
            db.execute('INSERT INTO history VALUES(?,?,?)',[key,record['revision'],encoded(record)])
        return record
