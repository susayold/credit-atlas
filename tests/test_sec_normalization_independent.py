from scripts.audit_sec_normalization_acceptance import field_evidence


def filing():
    return {'cik':'1','accession':'a','filing_date':'2026-02-01','report_date':'2025-12-31','form':'10-K'}


def fact(**overrides):
    r={'cik':'1','accession':'a','filed_date':'2026-02-01','form':'10-K','taxonomy':'us-gaap',
       'concept':'Revenues','unit':'USD','start_date':'2025-01-01','end_date':'2025-12-31',
       'value_exact':'9007199254740993.123456789','source_ordinal':0,'frame':None}
    r.update(overrides);return r


def test_quarter_ytd_other_filing_or_unit_are_not_annual_inputs():
    rows=[fact(start_date='2025-10-01'),fact(start_date='2025-07-01'),fact(accession='later'),fact(unit='EUR'),fact(filed_date='2026-03-01')]
    r=field_evidence(filing(),rows,'revenue')
    assert r['status']=='missing' and r['value_exact'] is None and not r['evidence']


def test_equal_candidates_retained_conflicting_values_unavailable():
    rows=[fact(),fact(concept='SalesRevenueNet',source_ordinal=1)]
    r=field_evidence(filing(),rows,'revenue')
    assert r['status']=='supported' and len(r['evidence'])==2 and r['value_exact']==rows[0]['value_exact']
    rows[1]['value_exact']='0'
    r=field_evidence(filing(),rows,'revenue')
    assert r['status']=='ambiguous' and r['value_exact'] is None and len(r['evidence'])==2


def test_conflicting_annual_start_dates_are_not_concept_equivalent():
    r=field_evidence(filing(),[fact(),fact(start_date='2025-01-02')],'revenue')
    assert r['status']=='ambiguous' and r['start_date'] is None


def test_instant_rejects_duration_and_keeps_zero_actual():
    rows=[fact(concept='Assets',value_exact='0',start_date=None),fact(concept='Assets',value_exact='10')]
    r=field_evidence(filing(),rows,'assets')
    assert r['status']=='supported' and r['value_exact']=='0' and len(r['evidence'])==1


def test_unknown_taxonomy_and_missing_do_not_become_zero():
    r=field_evidence(filing(),[fact(taxonomy='issuer-custom')],'revenue')
    assert r['status']=='missing' and r['value_exact'] is None
