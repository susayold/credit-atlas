"""Create a canonical aggregate report payload for the private UI.

The frontend is a reader of this contract. It must not recompute risk logic or
receive loan-level IDs/predictions. The same payload can feed website and
workbook builders after an external rights review.
"""
from __future__ import annotations

import copy
import json
import re

from ..evidence_checks import require
from ..metrics import REGISTRY


def _assert_safe(value):
    if isinstance(value, dict):
        for key, child in value.items():
            require(key not in {'loan_id', 'borrower_id', 'account_id', 'prediction'},
                    'Report payload cannot contain row-level identity or prediction')
            _assert_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child)
    elif isinstance(value, str):
        require(not re.search(r'[A-Z]:[\\/]|/Users/|/home/', value), 'Private filesystem path in report payload')


def build(snapshot):
    """Return a versioned report payload from the already validated snapshot."""
    require(isinstance(snapshot, dict), 'Snapshot object required')
    require(snapshot.get('visibility') == 'private' and snapshot.get('public_release_approved') is False,
            'Private snapshot required')
    require(isinstance(snapshot.get('pipeline_run'), str) and snapshot['pipeline_run'], 'Pipeline identity required')
    tables = []
    for table_id, rows, grain, source in (
        ('label_outcomes', snapshot.get('outcomes', []), 'loan_12m_outcome', 'labels'),
        ('portfolio_monthly', snapshot.get('monthly', []), 'reporting_month', 'portfolio'),
        ('state_transitions', snapshot.get('transitions', []), 'adjacent_month_pair', 'portfolio'),
        ('segmented_transitions', (snapshot.get('segmented_transitions') or {}).get('rows', []),
         'segment_adjacent_month_pair', 'segmented_transitions'),
        ('portfolio_profile', (snapshot.get('portfolio_profile') or {}).get('rows', []),
         'segment_origination_bucket', 'portfolio_profile'),
        ('vintage_competing_risk', (snapshot.get('vintage_evidence') or {}).get('rows', []), 'loan_horizon_aggregate', 'vintage'),
    ):
        require(isinstance(rows, list), f'{table_id} must be a list')
        tables.append({'table_id': table_id, 'grain': grain, 'source_stage': source,
                       'pipeline_run': snapshot['pipeline_run'], 'rows': copy.deepcopy(rows)})
    loss = copy.deepcopy(snapshot.get('loss_summary'))
    if loss is not None:
        tables.append({'table_id': 'observed_loss_summary', 'grain': 'resolved_terminal_loan_aggregate',
                       'source_stage': 'audit', 'pipeline_run': snapshot['pipeline_run'], 'rows': [loss]})
    result = {'schema_version': 1, 'visibility': 'private_aggregate',
              'public_release_approved': False, 'pipeline_run': snapshot['pipeline_run'],
              'evidence_class': 'derived_observed_sample',
              'metric_registry': copy.deepcopy(REGISTRY), 'tables': tables,
              'contract_rules': {'null_means': 'unavailable_not_zero',
                                 'frontend_recompute': False,
                                 'raw_identifiers_included': False,
                                 'prediction_rows_included': False}}
    _assert_safe(result)
    return result


def dumps(snapshot):
    """Serialize the report contract deterministically for hashing and tests."""
    return json.dumps(build(snapshot), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
