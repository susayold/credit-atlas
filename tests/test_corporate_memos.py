import copy
import pytest
from types import SimpleNamespace
from credit_atlas.corporate_memos import CorporateMemos,SECTIONS
from credit_atlas.reviews import ReviewConflict
from tests.test_sec_financials import acquired
from tests.test_sec_views import view


def payload(key):
    sections={k:'' for k in SECTIONS}
    sections.update(business_summary='Issuer research',conclusion='Need further evidence',next_action='Read debt terms')
    return {'title':'Financial memo','owner':'Analyst','status':'draft','sections':sections,
            'scope':{'view_id':key,'cik':'0000320193','accession':'','asof':'2026-02-01','years':'3'}}


def test_source_capture_revision_and_conflict(view):
    root,_,receipt,views=view;store=CorporateMemos(SimpleNamespace(root=root,sec_views=views))
    p=payload(receipt['view_id']);record=store.save(p)
    capture=copy.deepcopy(record['capture']);assert capture['evidence']['selected_filing']['statement']
    assert capture['evidence']['interest_coverage']['filters']['interest_concept']=='InterestExpenseNonoperating'
    assert capture['evidence']['interest_coverage']['filters']['asof']==capture['resolved_scope']['filing_date']
    assert capture['evidence']['debt_maturities']['filters']['debt_scope']=='debt_only'
    assert capture['evidence']['debt_maturities']['filters']['accession']==capture['resolved_scope']['accession']
    assert capture['evidence']['debt_maturities']['filters']['asof']==capture['resolved_scope']['filing_date']
    assert capture['evidence']['annual_trend']['filters']['asof']=='2026-02-01'
    assert not any(capture['qualification'].values())
    assert len(capture['evidence_sha256'])==64
    p.pop('scope');p.update(id=record['id'],revision=1,status='reviewed');p['sections']['conclusion']='Updated view'
    revised=store.save(p);assert revised['revision']==2 and revised['capture']==capture
    with pytest.raises(ReviewConflict):store.save(p)
    p['revision']=2;p['scope']={}
    with pytest.raises(ValueError,match='immutable'):store.save(p)
    assert len(store.report(record['id'])['history'])==2
    assert len(store.list({'view_id':receipt['view_id'],'cik':'0000320193'})['memos'])==1
    assert store.list({'view_id':receipt['view_id'],'cik':'0000789019'})['memos']==[]


@pytest.mark.parametrize('case',['before_source','wrong_issuer','bad_years','injected_capture','empty_conclusion','long_owner','invalid_status','missing_section'])
def test_invalid_memos(view,case):
    root,_,receipt,views=view;store=CorporateMemos(SimpleNamespace(root=root,sec_views=views));p=payload(receipt['view_id'])
    if case=='before_source':p['scope']['asof']='2026-01-31'
    if case=='wrong_issuer':p['scope']['cik']='unknown'
    if case=='bad_years':p['scope']['years']='100'
    if case=='injected_capture':p['capture']={'approved':True}
    if case=='empty_conclusion':p['sections']['conclusion']=' '
    if case=='long_owner':p['owner']='X'*101
    if case=='invalid_status':p['status']='approved'
    if case=='missing_section':p['sections'].pop('liquidity')
    with pytest.raises(ValueError):store.save(p)
    assert store.list({'view_id':receipt['view_id'],'cik':'0000320193'})['memos']==[]


def test_history_remains_readable_without_current_source(view,monkeypatch):
    root,_,receipt,views=view;store=CorporateMemos(SimpleNamespace(root=root,sec_views=views));p=payload(receipt['view_id']);r=store.save(p)
    def unavailable(*args):raise ValueError('Source changed')
    monkeypatch.setattr(views,'report',unavailable)
    assert store.report(r['id'])['memo']['capture']==r['capture']
    p.pop('scope');p.update(id=r['id'],revision=1,status='archived')
    assert store.save(p)['capture']==r['capture']
    with pytest.raises(ValueError):store.save(payload(receipt['view_id']))
