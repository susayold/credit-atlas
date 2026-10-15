import argparse
import json
from credit_atlas.bankruptcy import acquire_reference, prepare_bankruptcy, verify_bankruptcy
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', required=True)
    parser.add_argument('--reference', help='Previously downloaded official original ARFF reference ID')
    args = parser.parse_args()
    reference = args.reference or acquire_reference(app_root())
    print('Official reference: ' + reference, flush=True)
    result = prepare_bankruptcy(app_root(), args.suite, reference)
    verify_bankruptcy(app_root(), result['case_id'])
    print(json.dumps({key: result[key] for key in ('case_id', 'status', 'rows', 'horizons',
        'overlap_diagnostics', 'original_arff_audits', 'independent_csv_differing_rows')}, indent=2))
