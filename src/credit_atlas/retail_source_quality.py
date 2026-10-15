"""Serve the acquisition-time aggregate profile, without reopening client rows."""
from .workspace import contained, read_json, sha256
from .retail import FEATURE_NAMES


def report(views, identifier, query=None):
    query = query or {}
    if set(query) - {'view_id'} or query.get('view_id', identifier) != identifier:
        raise ValueError('Only the verified suite view scope is supported')
    snapshot = views.view(identifier)
    anchor = read_json(contained(views.root, 'artifacts/private/' + identifier + '/view-complete.json'))
    relative = 'data/private/public-suite/' + snapshot['suite_id'] + '/uci-retail-receipt.json'
    pins = {k.replace('\\', '/'): v for k, v in anchor['inputs_sha256'].items()}
    path = contained(views.root, relative)
    if relative not in pins or sha256(path) != pins[relative]:
        raise ValueError('Retail acquisition profile is not bound to the suite view')
    source = read_json(path)
    if source.get('source_id') != 'uci-retail' or source.get('status') != 'DOWNLOADED_AND_PROFILED':
        raise ValueError('Verified retail acquisition profile required')
    profile = source['profile']
    fields = ['ID'] + ['X' + str(i) for i in range(1, 24)] + ['Y']
    rows = profile['rows']
    counts = profile['null_counts']
    if (type(rows) is not int or rows <= 0 or profile['fields'] != fields
            or profile['columns'] != len(fields) or set(counts) != set(fields)
            or any(type(n) is not int or not 0 <= n <= rows for n in counts.values())):
        raise ValueError('Malformed source profile population/field counts')
    features = [{'source_field': field, 'feature': name, 'population': rows,
                 'missing_cells': counts[field], 'missing_share': counts[field] / rows}
                for field, name in zip(fields[1:-1], FEATURE_NAMES, strict=True)]
    missing = sum(x['missing_cells'] for x in features)
    return {'schema_version': 1, 'visibility': 'private', 'public_release_approved': False,
            'view_id': identifier, 'suite_id': snapshot['suite_id'],
            'method_version': 'acquisition-profile-projection-v1',
            'scope': 'Whole acquisition population; 23 raw predictor columns; ID and target excluded; not final-test missingness',
            'rows': rows, 'feature_count': len(features), 'feature_cells': rows * len(features),
            'missing_feature_cells': missing, 'missing_feature_share': missing / (rows * len(features)),
            'missing_definition': 'Acquisition CSV parser: stripped cell in empty string, ?, ., NaN, nan',
            'features': features,
            'excluded_fields': [{'source_field': f, 'missing_cells': counts[f]} for f in ('ID', 'Y')],
            'source': {k: source[k] for k in ('source_id', 'url', 'metadata_url', 'rights', 'sha256', 'bytes', 'retrieved_at')},
            'profile_receipt_sha256': pins[relative],
            'limitations': ['Saved pre-freeze profile; no client feature rows reread or model refit.',
                            'Zero parser-missing cells does not establish category validity, semantic completeness, drift or temporal validation.']}
