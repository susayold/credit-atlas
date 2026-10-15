"""Synthetic checks for complete-scope development reproduction comparison."""
import json
from pathlib import Path
import runpy

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from crsl.pipeline import STAGES
from crsl.source import sha256

TOOLS=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/compare_pipeline_runs.py'))
compare=TOOLS['compare']


def make_pipeline(root,suffix):
    base=root/'artifacts/private'
    receipts=[]
    for stage,_,_ in STAGES:
        path=base/f'{stage}-{suffix}'
        path.mkdir(parents=True)
        for name in TOOLS['TABLES'].get(stage,()):
            pq.write_table(pa.table({'synthetic_value':[1,2,2]}),path/name)
        for name in ('findings.json','audit.json','registry.json','summary.json'):
            (path/name).write_text(json.dumps({'synthetic':True}))
        (path/'run-complete.json').write_text(json.dumps({'outputs_sha256':{p.name:sha256(p) for p in path.iterdir()}}))
        receipt=dict(stage=stage,status='PASS',output_run=path.name)
        if stage=='vintage':
            (path/'verification.json').write_text('{"status":"PASS"}')
            receipt.update(verification_sha256=sha256(path/'verification.json'),output_manifest_sha256=sha256(path/'run-complete.json'))
        receipts.append(receipt)
    pipeline=base/f'pipeline-{suffix}'
    pipeline.mkdir()
    (pipeline/'run-complete.json').write_text(json.dumps(dict(status='DEVELOPMENT_PIPELINE_COMPLETE',
        stages=receipts,source_manifest_sha256='synthetic-same-source',code_sha256='synthetic-same-code')))
    return pipeline


def test_complete_eight_stage_reproduction(tmp_path):
    result=compare(tmp_path,make_pipeline(tmp_path,'a'),make_pipeline(tmp_path,'b'))
    assert result['status']=='PASS'
    assert len(result['tables'])==13
    assert result['stable_summaries_checked']==4
    assert not result['research_ready']


def test_no_silent_subset_comparison(tmp_path):
    left=make_pipeline(tmp_path,'a');right=make_pipeline(tmp_path,'b')
    path=right/'run-complete.json'
    receipt=json.loads(path.read_text());receipt['stages'].pop();path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='eight-stage'):
        compare(tmp_path,left,right)


def test_row_multiplicity_difference_detected_even_with_updated_child_hash(tmp_path):
    left=make_pipeline(tmp_path,'a');right=make_pipeline(tmp_path,'b')
    target=tmp_path/'artifacts/private/labels-b/labels.parquet'
    pq.write_table(pa.table({'synthetic_value':[1,2]}),target)
    path=target.parent/'run-complete.json'
    receipt=json.loads(path.read_text());receipt['outputs_sha256'][target.name]=sha256(target)
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='Non-reproducible'):
        compare(tmp_path,left,right)


def test_stable_summary_difference_detected(tmp_path):
    left=make_pipeline(tmp_path,'a');right=make_pipeline(tmp_path,'b')
    (tmp_path/'artifacts/private/metrics-b/registry.json').write_text('{"synthetic":false}')
    with pytest.raises(ValueError,match='summary differs'):
        compare(tmp_path,left,right)
