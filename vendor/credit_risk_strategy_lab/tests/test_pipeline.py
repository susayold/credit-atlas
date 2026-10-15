import json
import pytest
from crsl.pipeline import run, STAGES, verified_vintage

def source(tmp_path,kind='annual_sample'):
    path=tmp_path/'input';path.mkdir()
    (path/'run-complete.json').write_text(json.dumps({'data_kind':kind,'result_status':'PROFILED'}))
    return path

def test_pipeline_dependencies_and_incomplete_research(tmp_path):
    original=source(tmp_path);seen=[]
    def stage(root,previous):
        seen.append(previous)
        output=root/f'fixture-{len(seen)}';output.mkdir();return output
    result=run(tmp_path,original,[('first',stage,'source'),('second',stage,'first')])
    manifest=json.loads((result/'run-complete.json').read_text())
    assert seen==[original,tmp_path/'fixture-1']
    assert manifest['status']=='DEVELOPMENT_PIPELINE_COMPLETE'
    assert not manifest['research_ready']

def test_pipeline_failure_stops_following_stages(tmp_path):
    original=source(tmp_path)
    def failure(root,previous): raise ValueError('synthetic failure')
    def forbidden(root,previous): pytest.fail('must not execute after failure')
    with pytest.raises(ValueError):run(tmp_path,original,[('first',failure,'source'),('second',forbidden,'source')])
    failed=list((tmp_path/'artifacts/private').glob('*/run-failed.json'))
    assert len(failed)==1
    assert json.loads(failed[0].read_text())['failed_stage']=='first'
    assert not (failed[0].parent/'run-complete.json').exists()

def test_format_example_cannot_enter_pipeline(tmp_path):
    with pytest.raises(ValueError,match='annual'):run(tmp_path,source(tmp_path,'format_example'),[])


def test_default_pipeline_requires_verified_vintage():
    assert STAGES[-1]==('vintage',verified_vintage,'canonical')


def test_vintage_verification_failure_blocks_pipeline_completion(tmp_path,monkeypatch):
    from crsl import pipeline
    original=source(tmp_path)
    produced=tmp_path/'vintage-fixture';produced.mkdir()
    monkeypatch.setattr(pipeline.vintage,'run',lambda root,previous:produced)
    def reject(root,path):
        raise ValueError('source mismatch')
    monkeypatch.setattr(pipeline.verify_vintage,'verify',reject)
    with pytest.raises(ValueError,match='source mismatch'):
        run(tmp_path,original,[('vintage',verified_vintage,'source')])
    failed=list((tmp_path/'artifacts/private').glob('*/run-failed.json'))
    assert len(failed)==1
    assert not (failed[0].parent/'run-complete.json').exists()
    assert not (produced/'verification.json').exists()
