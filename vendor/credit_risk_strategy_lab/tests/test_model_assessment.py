import pytest
pytest.importorskip('sklearn')

from crsl.models.assessment import assess

FEATURES = {'numeric': ['classic_fico'], 'categorical': ['occupancy']}
SETTINGS = dict(train_cutoff='2014-01-01', calibration_cutoff='2016-01-01',
    evaluation_cutoff='2018-01-01', logistic_C=1, calibration_C=1,
    minimum_events=10, bin_edges=['0','.1','.5','1'])


def rows():
    output = []
    for role, year in [('train', 2012), ('calibration', 2014), ('validation', 2016)]:
        for i in range(100):
            output.append(dict(loan_id=f'{role}-{i}', partition=role, included=True,
                landmark=f'{year}-01-01', label_known_month=f'{year+1}-01-01',
                classic_fico=600 if i < 50 else 780, occupancy='P',
                target=int(i % 4 != 0) if i < 50 else int(i % 4 == 0)))
    return output


def test_complete_synthetic_assessment_preserves_all_models_and_cohorts():
    result = assess(rows(), FEATURES, SETTINGS, evidence_class='synthetic_demo')
    assert result['cohort_counts'] == {'train': 100, 'calibration': 100, 'validation': 100}
    assert set(result['models']) == {'constant', 'logistic'}
    assert not result['champion_selected'] and not result['final_test_access']
    for model in result['models'].values():
        assert set(model['validation_metrics']) == {'raw', 'calibrated'}
        assert model['validation_metrics']['raw']['loans'] == 100
        assert model['validation_metrics']['calibrated']['loans'] == 100


def test_repeated_loan_across_partitions_fails():
    data = rows()
    data[100]['loan_id'] = data[0]['loan_id']
    with pytest.raises(ValueError, match='overlap'):
        assess(data, FEATURES, SETTINGS, evidence_class='synthetic_demo')


def test_test_data_and_ungated_real_assessment_refused():
    data = rows()
    data[-1]['partition'] = 'test'
    with pytest.raises(ValueError, match='final test'):
        assess(data, FEATURES, SETTINGS, evidence_class='synthetic_demo')
    with pytest.raises(ValueError, match='qualified split'):
        assess(rows(), FEATURES, SETTINGS, evidence_class='retrospective_development')


def test_validation_outcomes_cannot_change_fit_or_calibration():
    original = assess(rows(), FEATURES, SETTINGS, evidence_class='synthetic_demo')
    altered_rows = [{**r, 'target': 0} if r['partition'] == 'validation' else r for r in rows()]
    altered = assess(altered_rows, FEATURES, SETTINGS, evidence_class='synthetic_demo')
    for kind in ('constant', 'logistic'):
        assert original['models'][kind]['model'] == altered['models'][kind]['model']
        assert original['models'][kind]['calibration'] == altered['models'][kind]['calibration']
        assert original['models'][kind]['private_validation_scores'] == altered['models'][kind]['private_validation_scores']


def test_tuning_output_drives_final_logistic_fit():
    data = [r for r in rows() if r['partition'] != 'train']
    for year in (2006, 2008, 2010):
        data.extend({**r, 'loan_id': f"{year}-{r['loan_id']}", 'landmark': f'{year}-01-01',
                     'label_known_month': f'{year+1}-01-01'} for r in rows() if r['partition'] == 'train')
    settings = SETTINGS | {'logistic_C': None, 'logistic_tuning': dict(C_grid=['.1','1'],
        minimum_train_class=10, minimum_holdout_class=10, folds=[
        dict(fit_cutoff='2008-01-01',holdout_landmark_end='2009-01-01',evaluation_cutoff='2010-01-01'),
        dict(fit_cutoff='2010-01-01',holdout_landmark_end='2011-01-01',evaluation_cutoff='2012-01-01')])}
    result = assess(data, FEATURES, settings, evidence_class='synthetic_demo')
    assert result['models']['logistic']['model']['state']['C'] == float(result['logistic_tuning']['selected_C'])
    assert result['cohort_counts']['train'] == 300
    with pytest.raises(ValueError, match='not both'):
        assess(data, FEATURES, settings | {'logistic_C': 1}, evidence_class='synthetic_demo')
