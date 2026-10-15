"""Private source-bound HMDA cohort receipts; no adaptation of frozen views."""
import copy
import re
import threading
from pathlib import Path

from .hmda_cohorts import COHORTS, methods, verify_cohorts
from .workspace import contained, read_json, sha256


def serving_methods():
    return {**methods(), 'hmda_cohort_views': sha256(Path(__file__))}


class HmdaCohortViews:
    def __init__(self, root, aggregates):
        self.root = root; self.aggregates = aggregates; self.cache = {}
        self.lock = threading.RLock(); self.methods = serving_methods()

    def evidence(self, identifier, case_id):
        if not isinstance(case_id, str) or not re.fullmatch(r'hmda-case-[0-9a-f]{12}', case_id):
            raise ValueError('Invalid bound HMDA case')
        if self.methods != serving_methods(): raise ValueError('Cohort serving methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder, receipt, payload = verify_cohorts(self.root, identifier, self.aggregates)
                pins = {folder / 'cohort-complete.json': sha256(folder / 'cohort-complete.json')}
                pins.update({folder / name: digest for name, digest in receipt['outputs_sha256'].items()})
                self.cache[identifier] = (copy.deepcopy(receipt), copy.deepcopy(payload), pins)
            receipt, payload, pins = self.cache[identifier]
            if receipt['case_id'] != case_id: raise ValueError('Cohort belongs to another HMDA case')
            self.aggregates.case(case_id)
            if any(sha256(path) != digest for path, digest in pins.items()): raise ValueError('Frozen cohort evidence changed')
            return copy.deepcopy(receipt), copy.deepcopy(payload)

    def catalog(self, case_id):
        if not isinstance(case_id, str) or not re.fullmatch(r'hmda-case-[0-9a-f]{12}', case_id):
            raise ValueError('Invalid bound HMDA case')
        rows = []
        for path in (self.root / 'artifacts/private').glob('hmda-cohort-*/cohort-complete.json'):
            try:
                receipt = read_json(path)
                if receipt.get('case_id') != case_id: continue
                self.evidence(path.parent.name, case_id)
                rows.append({'cohort_id': path.parent.name, 'status': 'verified', 'completed_at': receipt['completed_at']})
            except (OSError, ValueError, KeyError, TypeError):
                rows.append({'cohort_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'case_id': case_id, 'cohorts': sorted(rows, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, query):
        if not isinstance(query, dict) or set(query) != {'cohort_id', 'case_id', 'cohort'} or query['cohort'] not in COHORTS:
            raise ValueError('Cohort report accepts exact cohort_id/case_id/cohort only')
        receipt, payload = self.evidence(query['cohort_id'], query['case_id'])
        return {'cohort_id': receipt['cohort_id'], 'case_id': receipt['case_id'], 'source_id': receipt['source_id'],
            'cohort': next(row for row in payload['cohorts'] if row['cohort'] == query['cohort']),
            'contract': payload['contract'], 'source_profiles_whole_case': payload['profiles'],
            'visibility': 'private', 'public_release_approved': False}
