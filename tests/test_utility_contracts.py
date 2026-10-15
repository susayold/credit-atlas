from pathlib import Path
import pytest
from credit_atlas import utility_contracts as c
from credit_atlas import utility_debt_service as d
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('system,date,supplement',[('water','March 31, 2026','Thirty-Second'),('wastewater','April 15, 2026','Twenty-Second')])
def test_policy_threshold_proposed_terms_and_historical_scope_stay_distinct(system,date,supplement):
    r=c.report(ROOT,system);s=r['description']
    assert s['reported_rate_covenant_multiple']=='1.1'
    assert s['reported_policy_target_multiple']=='1.6'
    assert s['statement_date_text']==date and s['proposed_amendment_supplement']==supplement
    assert s['amendment_effective_date'] is None and not s['amendment_effectiveness_verified']
    assert not s['current_historical_applicability_qualified']
    assert all(r[k] is None for k in ['qualified_headroom','applicable_historical_threshold','compliance'])
    assert len(s['evidence'])==11
    assert {'proposed_rate_redline','proposed_default_caveat','debt_service_continued'}<=set(e['role'] for e in s['evidence'])

def test_debt_report_has_source_legal_description_without_promoting_headroom():
    r=d.report(ROOT,{'year':'2021'})
    assert r['legal_evidence']['description']['statement_date_text']=='March 31, 2026'
    assert r['threshold'] is None and r['headroom'] is None and r['compliance'] is None

@pytest.mark.parametrize('target',['acquisition-complete.json','water-official-statement.pdf','profile.json'])
def test_contract_receipt_source_profile_tampering_is_rejected(monkeypatch,target):
    original=c.sha256
    monkeypatch.setattr(c,'sha256',lambda p:'changed' if p.name==target else original(p))
    with pytest.raises(ValueError,match='changed'):c.report(ROOT,'water')

def test_unknown_system_rejected():
    with pytest.raises(ValueError):c.report(ROOT,'corporate')
