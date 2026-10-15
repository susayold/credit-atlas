import subprocess
import sys

import pytest

from crsl.evidence_checks import require_hash, require_outcome_totals
from crsl.source import sha256


def test_valid_outcomes():
    require_outcome_totals([{'outcome': 'a', 'loans': 2}], 2)


@pytest.mark.parametrize('rows,total', [
    ([{'outcome': 'a', 'loans': 1}], 2),
    ([{'outcome': 'a', 'loans': -1}], 1),
    ([{'outcome': 'a', 'loans': True}], 1),
    ([{'outcome': 'a', 'loans': 1.0}], 1),
    ([{'outcome': '', 'loans': 1}], 1),
    ([{'outcome': 'a', 'loans': 1}, {'outcome': 'a', 'loans': 1}], 2),
    ([], 0),
])
def test_invalid_outcomes(rows, total):
    with pytest.raises(ValueError):
        require_outcome_totals(rows, total)


def test_modified_evidence_rejected(tmp_path):
    path = tmp_path / 'evidence.json'
    path.write_text('{}')
    expected = sha256(path)
    require_hash(path, expected)
    path.write_text('{"changed":true}')
    with pytest.raises(ValueError, match='hash mismatch'):
        require_hash(path, expected)


def test_guard_survives_optimized_python():
    result = subprocess.run([sys.executable, '-O', '-c',
        'from crsl.evidence_checks import require; require(False, "guard active")'],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert 'ValueError: guard active' in result.stderr
