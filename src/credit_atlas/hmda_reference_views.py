"""Source-bound display labels layered over unchanged HMDA aggregate receipts."""
import copy
import re
import threading

from .hmda_references import methods, verify_references
from .workspace import contained, read_json, sha256


class HmdaReferenceViews:
    def __init__(self, root, aggregates):
        self.root = root; self.aggregates = aggregates
        self.cache = {}; self.lock = threading.RLock(); self.methods = methods()

    def reference(self, identifier, source_id):
        if not isinstance(source_id, str) or not re.fullmatch(r'hmda-source-[0-9a-f]{12}', source_id):
            raise ValueError('Invalid bound HMDA source identity')
        if methods() != self.methods: raise ValueError('Reference serving methods changed; restart required')
        with self.lock:
            if identifier not in self.cache:
                folder, receipt, payload = verify_references(self.root, identifier)
                source = contained(self.root, 'data/private/hmda/' + receipt['source_id'])
                pins = {folder / 'reference-complete.json': sha256(folder / 'reference-complete.json'),
                        folder / 'labels.json': receipt['labels_sha256'],
                        source / 'source-complete.json': receipt['source_receipt_sha256']}
                pins.update({folder / row['file']: row['sha256'] for row in receipt['files']})
                pins.update({contained(source, row['file']): row['sha256'] for row in read_json(source / 'source-complete.json')['files']})
                self.cache[identifier] = (copy.deepcopy(receipt), copy.deepcopy(payload), pins)
            receipt, payload, pins = self.cache[identifier]
            if receipt['source_id'] != source_id: raise ValueError('Reference belongs to another HMDA source')
            if any(sha256(path) != digest for path, digest in pins.items()):
                raise ValueError('Frozen HMDA reference/source changed')
            return {'reference_id': identifier, 'source_id': source_id,
                    'reference_receipt_sha256': pins[contained(self.root, 'data/private/hmda/' + identifier + '/reference-complete.json')],
                    **copy.deepcopy(payload)}

    def catalog(self, source_id):
        if not isinstance(source_id, str) or not re.fullmatch(r'hmda-source-[0-9a-f]{12}', source_id):
            raise ValueError('Invalid bound HMDA source identity')
        rows = []
        for path in (self.root / 'data/private/hmda').glob('hmda-reference-*/reference-complete.json'):
            receipt = read_json(path)
            if receipt.get('source_id') != source_id: continue
            try:
                result = self.reference(path.parent.name, source_id)
                rows.append({'reference_id': path.parent.name, 'status': 'verified',
                             'reference_scope': result['reference_scope'], 'completed_at': receipt['completed_at']})
            except (ValueError, OSError, TypeError, KeyError):
                rows.append({'reference_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'source_id': source_id, 'references': sorted(rows, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, identifier, query):
        query = dict(query); query.pop('reference_id', None)
        report = self.aggregates.report(query.get('view_id', ''), query)
        reference = self.reference(identifier, report['source_id'])
        year = report['filters']['year']; dimension = report['filters']['dimension']
        if year not in reference['references']: raise ValueError('Reference year absent; no cross-year fallback')
        if dimension in ('lender', 'county'):
            lookup = reference['references'][year][dimension]
            for row in report['breakdown']:
                row['display_label'] = copy.deepcopy(lookup.get(row['bucket'], {'names': [], 'status': 'UNMATCHED'}))
        report['reference'] = {key: reference[key] for key in ('reference_id', 'source_id', 'reference_receipt_sha256',
            'reference_scope', 'county_names_acquired', 'contract', 'visibility', 'public_release_approved')}
        report['reference']['coverage_whole_year'] = next(row for row in reference['coverage'] if str(row['year']) == year)
        self.reference(identifier, report['source_id'])
        return report
