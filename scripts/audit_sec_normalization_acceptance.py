"""Independent raw JSON/Decimal canonical and annual field-candidate audit."""
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import pyarrow.parquet as pq
from credit_atlas.workspace import read_json, sha256, write_new

FIELDS = {'assets':('instant',['Assets']),'liabilities':('instant',['Liabilities']),
 'current_assets':('instant',['AssetsCurrent']),'current_liabilities':('instant',['LiabilitiesCurrent']),
 'cash_equivalents':('instant',['CashAndCashEquivalentsAtCarryingValue']),
 'revenue':('annual_duration',['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet','Revenues']),
 'net_income':('annual_duration',['NetIncomeLoss']),
 'operating_cashflow':('annual_duration',['NetCashProvidedByUsedInOperatingActivities'])}


def field_evidence(filing, facts, field):
    kind, concepts = FIELDS[field];end = filing['report_date'];candidates = []
    for f in facts:
        if (f['cik'],f['accession'],f['filed_date'],f['form']) != (filing['cik'],filing['accession'],filing['filing_date'],filing['form']):continue
        if f['taxonomy'] != 'us-gaap' or f['concept'] not in concepts or f['unit'] != 'USD' or f['end_date'] != end:continue
        start = f['start_date']
        if kind == 'instant' and start is not None:continue
        if kind != 'instant' and (not start or not 330 <= (date.fromisoformat(end)-date.fromisoformat(start)).days+1 <= 400):continue
        candidates.append(f)
    signatures = {(f['start_date'],f['end_date'],Decimal(f['value_exact'])) for f in candidates}
    state = 'missing' if not signatures else 'supported' if len(signatures)==1 else 'ambiguous'
    return {'status':state,'unit':'USD','kind':kind,
        'value_exact':candidates[0]['value_exact'] if state=='supported' else None,
        'start_date':candidates[0]['start_date'] if state=='supported' else None,'end_date':end,
        'evidence':[{k:f[k] for k in ['taxonomy','concept','unit','source_ordinal','start_date','end_date','value_exact','filed_date','frame']} for f in candidates]}


def audit(root):
    case = root/'artifacts/private/sec-case-33077fe45722';receipt = read_json(case/'case-complete.json')
    source = root/'data/private/sec'/receipt['source_id'];acquisition = read_json(source/'acquisition-complete.json')
    pins = {str((case/'case-complete.json').relative_to(root)):sha256(case/'case-complete.json'),
            str((source/'acquisition-complete.json').relative_to(root)):sha256(source/'acquisition-complete.json')}
    assert receipt['source_receipt_sha256']==sha256(source/'acquisition-complete.json')
    for name,digest in receipt['files'].items():
        assert sha256(case/name)==digest;pins[str((case/name).relative_to(root))]=digest
    for name,digest in receipt['methods'].items():assert sha256(root/'src/credit_atlas'/f'{name}.py')==digest
    facts=[];filings={};occurrences=[];definitions={};quality=[]
    for s in acquisition['files']:
        path=source/s['file'];assert sha256(path)==s['sha256'];pins[str(path.relative_to(root))]=s['sha256']
        payload=json.loads(path.read_text(encoding='utf-8'),parse_float=Decimal);cik=s['cik']
        if s['kind']=='companyfacts':
            assert str(payload['cik']).zfill(10)==cik
            definitions[cik]={}
            for taxonomy,concepts in payload['facts'].items():
                for concept,d in concepts.items():
                    definitions[cik][taxonomy+':'+concept]={'label':d.get('label'),'description':d.get('description'),'units':list(d['units'])}
                    for unit,values in d['units'].items():
                        for ordinal,f in enumerate(values):
                            known={'start','end','val','accn','fy','fp','form','filed','frame'}
                            facts.append({'cik':cik,'taxonomy':taxonomy,'concept':concept,'unit':unit,'source_ordinal':ordinal,
                                'start_date':f.get('start') or None,'end_date':f['end'],'value_exact':format(Decimal(f['val']),'f'),
                                'accession':f['accn'],'fiscal_year':f.get('fy'),'fiscal_period':f.get('fp'),'form':f['form'],
                                'filed_date':f['filed'],'frame':f.get('frame'),
                                'extra_json':json.dumps({k:v for k,v in f.items() if k not in known},sort_keys=True,default=str)})
        else:
            columns=payload['filings']['recent'] if s['kind']=='submissions' else payload
            assert all(len(v)==len(columns['accessionNumber']) for v in columns.values() if isinstance(v,list))
            for i,accession in enumerate(columns['accessionNumber']):
                def v(k):return columns[k][i] if k in columns else None
                row={'cik':cik,'accession':accession,'filing_date':v('filingDate'),'report_date':v('reportDate') or None,
                    'acceptance_datetime':v('acceptanceDateTime'),'form':v('form'),'primary_document':v('primaryDocument'),
                    'is_xbrl':None if v('isXBRL') is None else bool(v('isXBRL'))}
                key=(cik,accession)
                assert key not in filings or filings[key]==row
                filings[key]=row;occurrences.append({'cik':cik,'accession':accession,'source_file':s['file'],'source_ordinal':i})
    def multiset(rows):return Counter(json.dumps(r,sort_keys=True) for r in rows)
    def parquet_parity(rows,path,keys):
        expected={tuple(r[k] for k in keys):r for r in rows}
        assert len(expected)==len(rows)
        for batch in pq.ParquetFile(path).iter_batches(batch_size=512):
            for r in batch.to_pylist():
                key=tuple(r[k] for k in keys)
                assert key in expected and r==expected.pop(key)
        assert not expected
    parquet_parity(facts,case/'facts.parquet',['cik','taxonomy','concept','unit','source_ordinal'])
    counts=Counter((r['cik'],r['accession']) for r in occurrences)
    expected_filings=[{**f,'occurrences':counts[key]} for key,f in filings.items()]
    parquet_parity(expected_filings,case/'filings.parquet',['cik','accession'])
    assert multiset(occurrences)==multiset(read_json(case/'filing-occurrences.json'))
    assert definitions==read_json(case/'concepts.json')
    for entity in receipt['entities']:
        cik=entity['cik'];ff=[f for f in facts if f['cik']==cik];fs=[f for f in expected_filings if f['cik']==cik]
        quality.append({'cik':cik,'ticker':entity['ticker'],'fact_entries':len(ff),'concepts':len(definitions[cik]),
            'units':sorted({f['unit'] for f in ff}),'taxonomies':sorted({f['taxonomy'] for f in ff}),
            'unique_filings':len(fs),'filing_occurrences':sum(f['occurrences'] for f in fs),
            'facts_without_filing_manifest':sum((cik,f['accession']) not in filings for f in ff),
            'facts_filed_before_period_end':sum(f['filed_date']<f['end_date'] for f in ff),
            'facts_manifest_date_or_form_mismatch':sum((cik,f['accession']) in filings and
                (f['filed_date'],f['form'])!=(filings[(cik,f['accession'])]['filing_date'],filings[(cik,f['accession'])]['form']) for f in ff)})
    assert quality==read_json(case/'quality.json')
    grouped=defaultdict(list)
    for f in facts:grouped[(f['cik'],f['accession'])].append(f)
    expected={(f['cik'],f['accession']):f for f in expected_filings if f['form'] in {'10-K','10-K/A'} and f['report_date'] and (f['cik'],f['accession']) in grouped}
    statements=read_json(case/'annual-statements.json');assert len(statements)==len(expected)==67
    states=Counter();candidate_count=0
    for statement in statements:
        key=(statement['cik'],statement['accession']);filing=expected[key]
        for k in ['cik','accession','filing_date','report_date','form','primary_document']:assert statement[k]==filing[k]
        for field in FIELDS:
            value=field_evidence(filing,grouped[key],field)
            assert value==statement['fields'][field]
            states[value['status']]+=1;candidate_count+=len(value['evidence'])
    assert len(facts)==105441 and len(expected_filings)==len(occurrences)==13374
    assert all(sha256(root/p)==digest for p,digest in pins.items())
    out=root/'artifacts/private'/('sec-normalization-acceptance-'+uuid4().hex[:12])
    write_new(out/'receipt.json',{'status':'PASS','fact_entries':len(facts),'unique_filings':len(expected_filings),
        'filing_occurrences':len(occurrences),'annual_statements':67,'annual_field_states_checked':536,
        'field_status_counts':dict(states),'candidate_evidence_rows_checked':candidate_count,
        'inputs_sha256':pins,'method_sha256':sha256(Path(__file__)),'native_units_preserved':True,
        'historical_availability_qualified':False,'model_inference_or_fit':False,'full_completion_proven':False})
    print(json.dumps({'output':str(out),'status':'PASS','field_states':dict(states)}))


if __name__=='__main__':audit(Path.cwd().resolve())
