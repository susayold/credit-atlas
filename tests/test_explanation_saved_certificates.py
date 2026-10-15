import json
from pathlib import Path
import pytest
from credit_atlas.retail_explanations_saved import certificate

def test_unaudited_study_fails_closed(tmp_path):
    with pytest.raises(ValueError,match='certificate required'):certificate(tmp_path,'retail-explanations-000000000000',tmp_path/'x')

def test_changed_certificate_fails_before_source_load(tmp_path):
    folder=tmp_path/'artifacts/private';folder.mkdir(parents=True)
    (folder/'retail-explanations-audit-d4c7f6227d3d.json').write_text(json.dumps({'status':'PASS'}))
    with pytest.raises(ValueError,match='certificate changed'):certificate(tmp_path,'retail-explanations-84b3ac3bab6e',tmp_path/'missing-receipt')
