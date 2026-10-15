from decimal import Decimal
from pathlib import Path
import pytest
from credit_atlas import sovereign_defaults as d

ROOT=Path(__file__).resolve().parents[1]

def test_source_cache_conflict_and_provisional_year_are_retained():
    r=d.report(ROOT,{})
    assert r['reference_year_header']=={'year':2025,'source_label':'2025p','source_cell':'BQ1','provisional':True}
    assert r['world_source_sovereigns_in_default_exact']=='80'
    count=next(c for c in r['source_summary_comparisons'] if c['metric']=='TOTAL_DEF_SOVEREIGNS')
    assert count['summary_exact']=='0' and count['flat_exact']=='80' and not count['matches_at_flat_precision']
    assert all(r[k] is False for k in ['historical_publication_vintages_complete','pd_lgd_calibrated','macro_stress_linkage_qualified','public_release_approved'])

def test_revision_is_distinct_from_year_change_and_not_nearest_year():
    r=d.report(ROOT,{'year':'2024'})
    assert Decimal(r['edition_revision_same_year_exact'])==Decimal('82335.31')
    assert Decimal(r['year_change_same_edition_exact'])==Decimal('-12698.10')
    latest=d.report(ROOT,{})
    assert latest['edition_revision_same_year_exact'] is None
    first=d.report(ROOT,{'year':'1960'})
    assert first['prior_year_same_edition_exact'] is None

def test_country_missing_zero_and_positive_stay_distinct():
    missing=d.report(ROOT,{'entity':'PLW'})
    zero=d.report(ROOT,{'entity':'NAM'})
    vietnam=d.report(ROOT,{'entity':'VNM'})
    assert missing['actual_exact'] is None
    assert Decimal(zero['actual_exact'])==0
    assert Decimal(vietnam['actual_exact'])==36
    assert vietnam['country_panel']['entities']==166
    assert vietnam['country_panel']['known_total_entities']<166
    assert vietnam['country_panel']['positive_total_entities']!=int(vietnam['world_source_sovereigns_in_default_exact'])
    assert vietnam['domestic_arrears_exact']=='0'
    assert len(vietnam['components'])==11

@pytest.mark.parametrize('query',[{'edition':'2022'},{'edition':'2025','year':'2025'}, {'entity':'XX'}, {'year':'2026'}, {'from':'2025','to':'2024'}, {'metric':'PD'},{'year':2025},{'scope':'all'}])
def test_invalid_scope_is_rejected(query):
    with pytest.raises(ValueError):d.report(ROOT,query)

def test_source_and_profile_tampering_fail_closed(monkeypatch):
    monkeypatch.setattr(d,'sha256',lambda p:'changed')
    with pytest.raises(ValueError,match='source receipt changed'):d.report(ROOT,{})

def test_normalized_profile_tampering_is_rejected(monkeypatch):
    original=d.sha256
    monkeypatch.setattr(d,'sha256',lambda p:'changed' if p.name=='profile.json' else original(p))
    with pytest.raises(ValueError,match='normalized profile changed'):d.report(ROOT,{})

def test_archive_schema_absence_and_vintage_dates_are_not_filled():
    r=d.report(ROOT,{'edition':'2023','metric':'IADB'})
    assert r['actual_exact'] is None and not r['metric_column_present']
    assert r['source_cell']['cell'] is None and r['source_cell']['source_header'] is None
    assert r['country_panel']['entities']==157
    assert r['source_update_text']=='Last Update: 29 August 2023'
    assert r['component_residual_exact'] is None
    assert all(x['value_exact'] is None for x in r['timeline'])
    assert r['prior_edition'] is None
    assert [e['edition'] for e in r['edition_catalog']]==[2023,2024,2025,2026]
    assert 'IADB' in r['edition_catalog'][0]['unavailable_metrics']

def test_source_specific_alias_and_markers_preserve_evidence():
    r=d.report(ROOT,{'edition':'2024','year':'2022'})
    assert r['source_cell']['source_header']=='DEBT_TOTAL_2023'
    assert r['actual_exact']=='530095.93000000005'
    assert r['prior_edition_same_year_exact']=='554236.54933913087'
    assert r['edition_revision_same_year_exact']=='-24140.61933913082'
    assert all(x['matches_at_flat_precision'] for x in r['source_summary_comparisons'])
    marker=d.report(ROOT,{'edition':'2024','entity':'AFG','year':'1981','metric':'OTHER_OFFICIAL_CREDITORS'})
    assert marker['actual_exact'] is None
    assert marker['selected_source_marker']=={'raw':'****','status':'source_unavailable','cell':'L151'}
    with pytest.raises(ValueError):d.report(ROOT,{'edition':'2023','entity':'CHN'})

def test_archive_receipt_tampering_is_rejected(monkeypatch):
    original=d.sha256
    monkeypatch.setattr(d,'sha256',lambda p:'changed' if p.parent.name==d.ARCHIVE and p.name=='acquisition-complete.json' else original(p))
    with pytest.raises(ValueError,match='archive receipt changed'):d.report(ROOT,{})
