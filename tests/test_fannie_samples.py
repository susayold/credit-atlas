from pathlib import Path
import pytest
from credit_atlas.fannie_samples import report,PROFILE,PROFILE_SHA
ROOT=Path(__file__).resolve().parents[1]

def test_source_scopes_quality_and_sample_not_training_gates():
    r=report(ROOT,{})
    assert r['summary']['source_rows']==1015 and r['summary']['source_positions']==96749
    assert len(r['profiles'])==3 and r['summary']['added_freddie_annual_vintages']==0
    assert all(not value for value in r['gates'].values())
    sf=report(ROOT,{'family':'single-family'})
    assert sf['summary']['source_rows']==757 and sf['profiles'][0]['columns']==108 and sf['profiles'][0]['loan_count']==8
    assert sf['multifamily_link_support'] is None
    mf=report(ROOT,{'family':'multifamily'})
    assert mf['summary']['source_rows']==258 and mf['multifamily_link_support']['overlap_loans']==4
    assert not mf['multifamily_link_support']['monthly_join_performed']
    annual=next(p for p in mf['profiles'] if p['columns']==3)
    assert annual['reported_dscr']['min_exact']=='1.13' and annual['reported_dscr']['max_exact']=='2.68'
    assert not annual['reported_dscr']['ratio_recomputed_from_cashflow_and_debt_service']

@pytest.mark.parametrize('query',[{'family':'all','loan_id':'private'},{'family':'../'},{'from':'2020'},{'family':[]}])
def test_invalid_scopes(query):
    with pytest.raises(ValueError):report(ROOT,query)

def test_changed_profile_rejected_before_sources(tmp_path):
    path=tmp_path/'artifacts/private'/PROFILE;path.mkdir(parents=True)
    (path/'profile.json').write_text('{}')
    with pytest.raises(ValueError,match='profile changed'):report(tmp_path,{})
