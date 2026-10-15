import pytest

from crsl.reporting.export import build


def snapshot():
    return {'visibility': 'private', 'public_release_approved': False, 'pipeline_run': 'pipeline-test',
            'outcomes': [{'outcome': 'd3_event', 'loans': 2}], 'monthly': [], 'transitions': [],
            'vintage_evidence': {'rows': []}, 'loss_summary': {'reported_loss_loans': 2}}


def test_report_contract_has_lineage_and_safe_tables():
    report = build(snapshot())
    assert report['visibility'] == 'private_aggregate'
    assert report['tables'][0]['pipeline_run'] == 'pipeline-test'
    assert report['contract_rules']['null_means'] == 'unavailable_not_zero'


def test_report_contract_rejects_row_level_identity():
    bad = snapshot()
    bad['monthly'] = [{'loan_id': 'L1'}]
    with pytest.raises(ValueError, match='row-level identity'):
        build(bad)
