import pytest

from scripts.export_safe_data_package import assert_safe


def test_aggregate_guard_rejects_row_level_identity():
    with pytest.raises(ValueError, match='Forbidden identity key'):
        assert_safe({'loan_id': 'not-exportable'})


def test_aggregate_guard_rejects_private_filesystem_path():
    with pytest.raises(ValueError, match='Private filesystem path'):
        assert_safe({'source': r'C:\private\raw.zip'})
