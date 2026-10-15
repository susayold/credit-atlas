"""Source-bound aggregate exposure inventory; no private position rows served."""
import copy
import threading
from pathlib import Path

from .exposure_imports import methods, verify_import
from .workspace import contained, read_json, sha256


def serving_methods():
    return {**methods(), 'exposure_views': sha256(Path(__file__))}


class ExposureViews:
    def __init__(self, root):
        self.root = root; self.cache = {}; self.lock = threading.RLock(); self.methods = serving_methods()

    def evidence(self, identifier):
        if self.methods != serving_methods(): raise ValueError('Exposure serving methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder, receipt, report = verify_import(self.root, identifier)
                metadata = read_json(folder / 'metadata.json')
                pins = {folder / 'import-complete.json': sha256(folder / 'import-complete.json')}
                pins.update({folder / name: digest for name, digest in receipt['outputs_sha256'].items()})
                pins.update({contained(self.root, row['path']): row['sha256'] for row in metadata['source_lineage']})
                self.cache[identifier] = (copy.deepcopy(receipt), copy.deepcopy(report), pins)
            receipt, report, pins = self.cache[identifier]
            if any(sha256(path) != digest for path, digest in pins.items()): raise ValueError('Frozen exposure source/import changed')
            return copy.deepcopy(receipt), copy.deepcopy(report), pins[contained(self.root, 'artifacts/private/' + identifier + '/import-complete.json')]

    def catalog(self):
        imports = []
        for path in (self.root / 'artifacts/private').glob('exposure-import-*/import-complete.json'):
            try:
                receipt, report, _ = self.evidence(path.parent.name)
                imports.append({'import_id': path.parent.name, 'status': 'verified', 'completed_at': receipt['completed_at'],
                                'records': report['records'], 'dataset_kind': report['dataset_kind']})
            except (OSError, KeyError, ValueError, TypeError): imports.append({'import_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'imports': sorted(imports, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, query):
        if not isinstance(query, dict) or set(query) - {'import_id', 'currency', 'dimension'} or 'import_id' not in query:
            raise ValueError('Exposure aggregate accepts import_id/currency/dimension only')
        receipt, report, digest = self.evidence(query['import_id'])
        currency = query.get('currency', 'all'); dimension = query.get('dimension', 'region')
        if currency != 'all' and currency not in [row['currency'] for row in report['currencies']]: raise ValueError('Currency absent from imported source')
        if dimension not in ('segment', 'region', 'source_state', 'representation'): raise ValueError('Unknown concentration dimension')
        report['currencies'] = [row for row in report['currencies'] if currency == 'all' or row['currency'] == currency]
        report['concentrations'] = [row for row in report['concentrations'] if row['dimension'] == dimension and (currency == 'all' or row['currency'] == currency)]
        report['records'] = sum(row['records'] for row in report['currencies'])
        report.update(import_id=receipt['import_id'], import_receipt_sha256=digest, filters={'currency': currency, 'dimension': dimension})
        return report
