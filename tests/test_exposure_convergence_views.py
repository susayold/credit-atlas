import pytest
from credit_atlas.exposure_convergence import build
from credit_atlas.exposure_convergence_views import ExposureConvergenceViews
from credit_atlas.workspace import write_new
from tests.test_exposure_tail import frozen
from tests.test_exposure_convergence import plan


def test_source_filters_copies_and_cached_corruption(tmp_path):
    base=frozen(tmp_path); write_new(tmp_path/'convergence.json',plan(base['tail_id']))
    receipt=build(tmp_path,'convergence.json'); views=ExposureConvergenceViews(tmp_path)
    assert len(views.catalog(base['source_import_id'])['studies'])==1
    query={'convergence_id':receipt['convergence_id'],'source_import_id':base['source_import_id'],'currency':'USD'}
    report=views.report(query); assert all(r['currency']=='USD' for r in report['diagnostics'])
    report['runs'].clear(); assert views.report(query)['runs']
    for change in ({'currency':'GBP'},{'source_import_id':'x'},{'seed':'0'}):
        with pytest.raises(ValueError): views.report({**query,**change})
    path=tmp_path/'artifacts/private'/receipt['convergence_id']/'report.json'
    path.write_text(path.read_text(encoding='utf-8')+' ',encoding='utf-8')
    with pytest.raises(ValueError,match='source changed'): views.report(query)
