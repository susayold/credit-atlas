import copy
import re
import threading
from pathlib import Path
from .retail_explanations import guard, methods
from .retail_explanations_saved import verify_base_saved as verify,certificate_pins,CERTIFICATES
from .workspace import sha256


class RetailExplanationViews:
    def __init__(self, root):
        self.root = root
        self.lock = threading.RLock()
        self.cache = {}
        self.methods = self.current_methods()
    def current_methods(self):
        return methods() | {'serving': sha256(Path(__file__)), 'saved_verifier':sha256(Path(__file__).with_name('retail_explanations_saved.py'))}

    def evidence(self, identifier):
        if self.methods != self.current_methods():
            raise ValueError('Explanation methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder, receipt, report = verify(self.root, identifier)
                pins = receipt['inputs_sha256'] | {str((folder / name).relative_to(self.root)): digest
                                                  for name, digest in receipt['outputs_sha256'].items()}
                pins[str((folder / 'explanations-complete.json').relative_to(self.root))] = sha256(folder / 'explanations-complete.json')
                if identifier in CERTIFICATES:pins.update(certificate_pins(self.root,identifier))
                self.cache[identifier] = (report, pins)
            report, pins = self.cache[identifier]
            guard(self.root, pins)
            return copy.deepcopy(report)

    def catalog(self, query):
        if set(query) != {'freeze_id'} or not isinstance(query['freeze_id'], str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}', query['freeze_id']):
            raise ValueError('Frozen-model explanation scope required')
        records = []
        for path in (self.root / 'artifacts/private').glob('retail-explanations-*/explanations-complete.json'):
            try:
                report = self.evidence(path.parent.name)
                if report['freeze_id'] == query['freeze_id']:
                    records.append({'explanations_id': path.parent.name, 'records': report['records'],
                                    'local_cases': report['local_case_count']})
            except (ValueError, KeyError, OSError, TypeError):
                continue
        return {'studies': records, **query}

    def report(self, query):
        if set(query) - {'explanations_id', 'freeze_id', 'case'} or not {'explanations_id', 'freeze_id'} <= set(query):
            raise ValueError('Bound explanation report required')
        report = self.evidence(query['explanations_id'])
        if report['freeze_id'] != query['freeze_id']:
            raise ValueError('Explanation frozen-model mismatch')
        if 'case' in query:
            cases = [row for row in report['local_explanations'] if row['case'] == query['case']]
            if not cases:
                raise ValueError('Selected validation explanation case unavailable')
            report['local_explanations'] = cases
        report.update(explanations_id=query['explanations_id'], filters={'case': query.get('case', 'all')},
                      visibility='private', public_release_approved=False)
        return report
