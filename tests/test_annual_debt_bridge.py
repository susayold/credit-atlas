import json
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
import pytest
from credit_atlas import annual_debt_bridge as bridge

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def selected(monkeypatch):
    manifest = json.loads((ROOT / 'artifacts/private/maturity-workbook-scope-audit-46d6a12f8d2d/receipt.json').read_text())
    scope = manifest['scopes'][0]
    value = json.loads((ROOT / scope['capture']).read_text())
    monkeypatch.setattr(bridge, 'maturity_report', lambda *args: deepcopy(value))
    return value

def test_integer_bridges_and_selected_maturity(selected):
    r = bridge.report(SimpleNamespace(root=ROOT), selected['view_id'], {})
    assert r['status'] == 'VERIFIED_ANNUAL_DEBT_BRIDGE'
    assert r['first_year_principal_minus_current_carrying_usd_exact'] == '43000000'
    assert len(r['maturities']) == 6
    for b in r['bridges']:
        assert int(b['principal_usd_exact']) + int(b['discount_and_costs_usd_exact']) + int(b['hedge_fair_value_adjustment_usd_exact']) == int(b['carrying_usd_exact'])
        assert int(b['current_carrying_usd_exact']) + int(b['noncurrent_carrying_usd_exact']) == int(b['carrying_usd_exact'])
    assert not any(r['qualification'].values()) and not r['public_release_approved']

@pytest.mark.parametrize('change', ['issuer', 'family', 'accession', 'date', 'no_statement'])
def test_no_cross_scope_fallback(selected, change):
    if change == 'issuer': selected['filters']['cik'] = '0000789019'
    if change == 'family': selected['filters']['debt_scope'] = 'debt_and_capital_lease'
    if change == 'accession': selected['statement']['accession'] = '0000320193-24-000123'
    if change == 'date': selected['statement']['report_date'] = '2024-09-28'
    if change == 'no_statement': selected['statement'] = None
    r = bridge.report(SimpleNamespace(root=ROOT), selected['view_id'], {})
    assert r['status'] == 'NO_MATCHING_ANNUAL_DEBT_EVIDENCE'
    assert r['source'] is None and r['bridges'] == r['maturities'] == r['tables'] == []
    assert r['first_year_principal_minus_current_carrying_usd_exact'] is None

def test_conflicting_bucket_fails_closed(selected):
    selected['buckets'][0]['field']['value_exact'] = '0'
    with pytest.raises(ValueError, match='no longer reconciles'):
        bridge.report(SimpleNamespace(root=ROOT), selected['view_id'], {})

def test_source_tampering_fails_closed(selected, monkeypatch):
    original = bridge.sha256
    monkeypatch.setattr(bridge, 'sha256', lambda p: '0'*64 if Path(p).name == 'apple-2025-10k.html' else original(p))
    with pytest.raises(ValueError, match='source evidence changed'):
        bridge.report(SimpleNamespace(root=ROOT), selected['view_id'], {})

def test_audit_method_tampering_fails_closed(selected, monkeypatch):
    original = bridge.sha256
    monkeypatch.setattr(bridge, 'sha256', lambda p: '0'*64 if Path(p).name == 'audit_apple_annual_debt_bridge.py' else original(p))
    with pytest.raises(ValueError, match='audit or method changed'):
        bridge.report(SimpleNamespace(root=ROOT), selected['view_id'], {})

def test_audit_capture_tampering_fails_closed(selected, monkeypatch):
    original = bridge.sha256
    monkeypatch.setattr(bridge, 'sha256', lambda p: '0'*64 if Path(p) == ROOT / bridge.AUDIT else original(p))
    with pytest.raises(ValueError, match='audit capture changed'):
        bridge.report(SimpleNamespace(root=ROOT), selected['view_id'], {})
