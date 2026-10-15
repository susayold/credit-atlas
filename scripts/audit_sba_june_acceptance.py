"""Independent whole-source CSV/Python/Decimal vs canonical and all four marts."""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, localcontext
from itertools import zip_longest
from pathlib import Path
from uuid import uuid4
import pyarrow.parquet as pq
from credit_atlas.workspace import read_json, sha256, write_new, timestamp

DATE_FIELDS = {'AsOfDate':'snapshot_date','ApprovalDate':'approval_date',
    'FirstDisbursementDate':'first_disbursement_date','PaidInFullDate':'paid_in_full_date','ChargeOffDate':'charge_off_date'}
MONEY_FIELDS = {'GrossApproval':'reported_approval_amount','GrossChargeOffAmount':'reported_chargeoff_amount',
    'SBAGuaranteedApproval':'guaranteed_approval_amount','ThirdPartyDollars':'third_party_amount'}
INT_FIELDS = {'ApprovalFY':'approval_fiscal_year','TermInMonths':'term_months','JobsSupported':'jobs_supported'}
TEXT_FIELDS = {'LocationID':'lender_source_id','ProjectState':'project_state','NaicsCode':'naics_code',
    'BusinessType':'business_type','BusinessAge':'business_age','ProcessingMethod':'processing_method'}
STATUS = {'7A':{'CANCLD':'cancelled','CHGOFF':'charged_off','COMMIT':'undisbursed','EXEMPT':'disbursed_status_withheld','PIF':'paid_in_full','P I F':'paid_in_full'},
          '504':{'CANCLD':'cancelled','CHGOFF':'charged_off','NOT FUNDED':'undisbursed','EXEMPT':'disbursed_status_withheld','PIF':'paid_in_full','CLOSED':'closed_other_legacy'}}


def typed(raw, program, source, ordinal):
    r = {'source_id':source,'source_row_ordinal':ordinal,'source_record_key':f'{source}:{ordinal}',
         'program':raw['Program'].strip(),'status_raw':raw['LoanStatus'],
         'status':STATUS[program].get(raw['LoanStatus'].strip(),'unmapped')}
    for field, name in DATE_FIELDS.items():
        value = raw[field].strip();r[name] = date.fromisoformat(value) if value else None
    for field, name in MONEY_FIELDS.items():
        value = raw.get(field,'').strip();r[name] = Decimal(value) if value else None
    for field, name in INT_FIELDS.items():
        value = raw[field].strip()
        if value and Decimal(value) != Decimal(value).to_integral_value():
            raise ValueError('Nonintegral source integer')
        r[name] = int(Decimal(value)) if value else None
    rate = raw.get('InitialInterestRate','').strip()
    r['initial_rate_pct'] = Decimal(rate) if rate else None
    for field, name in TEXT_FIELDS.items():r[name] = raw[field].strip() or None
    return r


def quality_flags(r):
    approval = r['approval_date'];snapshot = r['snapshot_date'];fy = r['approval_fiscal_year']
    first = r['first_disbursement_date'];co = r['charge_off_date'];paid = r['paid_in_full_date']
    a = r['reported_approval_amount'];c = r['reported_chargeoff_amount']
    return {'unmapped_status':r['status']=='unmapped',
        'missing_approval_date_or_year':approval is None or fy is None,
        'fiscal_year_mismatch':approval is not None and fy is not None and fy != approval.year + (approval.month >= 10),
        'event_date_after_snapshot':any(v is not None and snapshot is not None and v > snapshot for v in [approval,first,co,paid]),
        'disbursement_before_approval':first is not None and approval is not None and first < approval,
        'outcome_before_approval':any(v is not None and approval is not None and v < approval for v in [co,paid]),
        'charged_off_missing_date':r['status']=='charged_off' and co is None,
        'other_status_has_chargeoff_date':r['status']!='charged_off' and co is not None,
        'signed_negative_amount':any(v is not None and v < 0 for v in [a,c]),
        'chargeoff_exceeds_approval':a is not None and c is not None and c > a}


def buckets(r):
    code = r['naics_code']
    return {'program_status':'all', 'approval_fiscal_year':str(r['approval_fiscal_year']) if r['approval_fiscal_year'] is not None else None,
            'project_state':r['project_state'] or '__unavailable__',
            'naics_two_digit':code[:2] if code and re.fullmatch(r'[0-9]{2,6}',code) else '__unavailable__'}


def fingerprint(row):
    return hashlib.sha256(json.dumps(row,ensure_ascii=False,separators=(',',':')).encode()).digest()


def saved_rows(path):
    for batch in pq.ParquetFile(path).iter_batches(batch_size=2048):yield from batch.to_pylist()


def audit(root):
    case = root / 'artifacts/private/business-sba-21c568f10f7d'
    receipt_path = case / 'business-complete.json';receipt = read_json(receipt_path)
    source = root / 'data/private/public-suite' / receipt['suite_id']
    acquisition = read_json(source / 'acquisition-complete.json')
    assert sha256(source / 'acquisition-complete.json') == receipt['source_receipt_sha256']
    assert sha256(root/'src/credit_atlas/business_sba.py') == receipt['method_source_sha256']
    pins = {str(receipt_path.relative_to(root)):sha256(receipt_path),
            str((source/'acquisition-complete.json').relative_to(root)):sha256(source/'acquisition-complete.json')}
    for name, digest in receipt['outputs_sha256'].items():
        assert sha256(case/name) == digest;pins[str((case/name).relative_to(root))] = digest
    specs = {s['source_id']:s for s in acquisition['sources']}
    quality = read_json(case/'quality.json');dictionary = read_json(case/'dictionary.json')
    expected_marts = read_json(case/'aggregates.json')['dimensions']
    marts = {d:{} for d in expected_marts};checked = [];total_cells = 0
    for segment in receipt['files']:
        identifier = segment['source_id'];program = segment['program'];spec = specs[identifier]
        raw_path = source/spec['file'];assert sha256(raw_path) == spec['sha256'] == segment['source_sha256']
        pins[str(raw_path.relative_to(root))] = spec['sha256']
        flags = Counter();lenders = set();seen = set();candidates = set();n = 0
        parse = {f:Counter({k:0 for k in v if isinstance(v[k],int)}) for f,v in quality[identifier]['parse'].items()}
        with raw_path.open(encoding='utf-8-sig',newline='') as stream:
            reader = csv.reader(stream);headers = next(reader)
            assert headers == [e['field'] for e in dictionary[program]] == spec['profile']['fields']
            for ordinal, (rawrow, saved) in enumerate(zip_longest(reader,saved_rows(case/segment['file'])),1):
                assert rawrow is not None and saved is not None and len(rawrow) == len(headers)
                raw = dict(zip(headers,rawrow));r = typed(raw,program,identifier,ordinal)
                assert r == saved, 'Canonical row differs;no private row contents emitted'
                assert r['program'] == program and r['snapshot_date'] == date(2026,6,30)
                n += 1;total_cells += len(r);flags.update({k:int(v) for k,v in quality_flags(r).items()})
                if r['lender_source_id'] is not None:lenders.add(r['lender_source_id'])
                digest = fingerprint(rawrow)
                if digest in seen:candidates.add(digest)
                else:seen.add(digest)
                for f, counts in parse.items():
                    text = raw[f];value = text.strip();counts['blank'] += not value
                    if not value:continue
                    if f in DATE_FIELDS:
                        counts['non_iso_nonblank'] += re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',text) is None
                    else:
                        dec = Decimal(value);assert dec.is_finite()
                        counts['non_decimal_nonblank'] += re.fullmatch(r'[+-]?[0-9]+([.][0-9]+)?([eE][+-]?[0-9]+)?',value) is None
                        counts['excess_fractional_digits'] += len(value.split('.')[1] if '.' in value else '') > 18
                        if f in MONEY_FIELDS:counts['fractional_cent_records'] += dec != dec.quantize(Decimal('0.01'))
                for dimension, bucket in buckets(r).items():
                    key = (program,bucket,r['status'])
                    cell = marts[dimension].setdefault(key,{'records':0,'approval':None,'chargeoff':None,'known_approval':0,'known_chargeoff':0})
                    cell['records'] += 1
                    for label,field in [('approval','reported_approval_amount'),('chargeoff','reported_chargeoff_amount')]:
                        if r[field] is not None:
                            cell[label] = (cell[label] or Decimal(0)) + r[field];cell['known_'+label] += 1
        # Resolve every repeated fingerprint with exact raw tuples;hash collisions do not count as duplicates.
        exact = Counter()
        if candidates:
            with raw_path.open(encoding='utf-8-sig',newline='') as stream:
                reader = csv.reader(stream);next(reader)
                for row in reader:
                    if fingerprint(row) in candidates:exact[tuple(row)] += 1
        duplicates = sum(c-1 for c in exact.values());flags['distinct_lender_source_ids'] = len(lenders)
        assert n == segment['rows'] == spec['profile']['rows'] == quality[identifier]['retained_rows']
        assert duplicates == quality[identifier]['exact_duplicate_excess_rows']
        assert dict(flags) == quality[identifier]['flags']
        assert {f:dict(c) for f,c in parse.items()} == quality[identifier]['parse']
        checked.append({'source_id':identifier,'records':n,'canonical_fields':25,'exact_duplicate_excess':duplicates,
                        'parse_quality_fields':len(parse),'flags_checked':len(flags),'row_parity':'PASS'})
        print(json.dumps(checked[-1]),flush=True)
    cells = 0
    for dimension, rows in expected_marts.items():
        expected = {(r['program'],r['bucket'],r['status']):r for r in rows}
        assert len(expected) == len(rows) and set(expected) == set(marts[dimension])
        for key, computed in marts[dimension].items():
            e = expected[key]
            assert computed['records'] == e['records']
            for name, field in [('approval','reported_approval_amount'),('chargeoff','reported_chargeoff_amount')]:
                assert computed[name] == (Decimal(e[field]) if e[field] is not None else None)
                assert computed['known_'+name] == e['known_'+name+'_amount_records']
            cells += 1
    assert sum(c['records'] for c in checked) == receipt['rows'] == 2190504
    assert all(sha256(root/p) == digest for p,digest in pins.items())
    out = root / 'artifacts/private' / ('sba-june-acceptance-audit-' + uuid4().hex[:12])
    write_new(out/'receipt.json',{'status':'PASS','completed_at':timestamp(),'source_records':2190504,
        'canonical_cells_compared':total_cells,'segments':checked,'aggregate_dimensions_checked':list(marts),
        'aggregate_cells_checked':cells,'duplicate_policy':'Exact raw tuples;fingerprint candidates resolved in second pass',
        'inputs_sha256':pins,'audit_method_sha256':sha256(Path(__file__)),
        'model_fit_or_inference':False,'identity_qualified':False,'fixed_horizon_PD_qualified':False,
        'dictionary_cells_independently_checked':False,'full_completion_proven':False})
    print(json.dumps({'output':str(out),'status':'PASS','aggregate_cells':cells}),flush=True)


if __name__ == '__main__':
    with localcontext() as context:
        context.prec = 60
        audit(Path.cwd().resolve())
