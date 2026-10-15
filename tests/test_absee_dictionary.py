from pathlib import Path
import pytest
from credit_atlas import absee_dictionary as d

ROOT=Path(__file__).resolve().parents[1]

def test_definition_evidence_and_no_premature_model_or_code_qualification():
    r=d.report(ROOT,{})
    assert r['observed_fields']==62 and r['edition']=='2025-04-01'
    assert all(r[k] is False for k in ['xsd_verified','mirror_fidelity_verified','model_ready','current_rule_verified'])
    assert r['raw_filing_xml_acquired'] is True
    fields={x['field']:x for x in r['fields']}
    assert fields['currentDelinquencyStatus']['schedule_al_item']=='3(f)(25)'
    assert 'number of days' in fields['currentDelinquencyStatus']['definition']
    assert fields['recoveredAmount']['schedule_al_item']=='3(i)(2)'
    assert 'after charge-off' in fields['recoveredAmount']['definition']
    assert 'net of repossession fees' in fields['repossessedProceedsAmount']['definition']
    assert fields['zeroBalanceCode']['schedule_al_item']=='3(f)(24)(ii)'
    assert fields['paymentToIncomePercentage']['schedule_al_item']=='3(e)(6)'
    assert 'origination date' in fields['paymentToIncomePercentage']['definition']
    assert all(x['present_periods']+x['absent_periods']==11 for x in r['fields'])
    assert fields['zeroBalanceCode']['absent_periods']>0
    assert fields['assetNumber']['missing_present_schema_rows']==0
    assert all(x['mapping_status']=='ANALYST_PROPOSED_CORRESPONDENCE_NOT_XSD_VERIFIED' for x in r['fields'])

def test_no_lease_contamination_or_lost_zero_balance_subclauses():
    payload=(ROOT/'data/private/structured'/d.SOURCE/'CFR-2025-title17-vol3-sec229-1125.xml').read_bytes()
    clauses=d.clauses(payload)
    assert clauses['3(f)(24)(i)']['text'].startswith('(i) Zero balance effective date.')
    assert clauses['3(i)(1)']['text'].startswith('(1) Charged-off principal amount.')
    assert 'lessee' not in clauses['3(f)(25)']['text']
    assert set(d.MAPPING.values())<=set(clauses)
    assert len(d.MAPPING)==62

def test_rejects_scope_changes_source_mutation_and_unsafe_xml(monkeypatch):
    with pytest.raises(ValueError):d.report(ROOT,{'default_code':'3'})
    with pytest.raises(ValueError):d.clauses(b'<!DOCTYPE x><x/>')
    with pytest.raises(ValueError):d.clauses(b'<x><P>Item 3. Automobile loans.</P></x>')
    monkeypatch.setattr(d,'sha256',lambda p:'changed')
    with pytest.raises(ValueError,match='receipt changed'):d.report(ROOT,{})
