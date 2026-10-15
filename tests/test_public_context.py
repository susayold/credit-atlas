"""Actual public-series format, missingness and native-frequency constraints."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = spec_from_file_location("public_context", Path(__file__).resolve().parents[1] / "scripts/acquire_public_mortgage_context.py")
module = module_from_spec(spec)
spec.loader.exec_module(module)


def test_native_frequency_missingness_and_monthly_weekly_mean():
    u = module.parse_csv(b"observation_date,UNRATE\n2020-01-01,3.5\n2020-02-01,.\n", "UNRATE")
    m = module.parse_csv(b"observation_date,MORTGAGE30US\n2020-01-02,3\n2020-01-09,5\n", "MORTGAGE30US")
    result = module.monthly_context(["2020-01", "2020-02"], u + m)
    assert result[0]["mortgage30_percent_monthly_mean"] == 4
    assert result[0]["mortgage30_observations_in_month"] == 2
    assert result[1]["unemployment_percent_latest_revised"] is None
    assert result[1]["mortgage30_percent_monthly_mean"] is None


@pytest.mark.parametrize("raw,series", [
    (b"DATE,UNRATE\n2020-01-01,3\n", "UNRATE"),
    (b"observation_date,UNRATE\n2020-01-01,3\n2020-01-01,4\n", "UNRATE"),
    (b"observation_date,UNRATE\n2020-01-01,nan\n", "UNRATE"),
    (b"observation_date,USSTHPI\n2020-02-01,200\n", "USSTHPI"),
    (b"observation_date,UNRATE\n2020-01-02,3\n", "UNRATE"),
])
def test_invalid_schema_grain_and_values_are_rejected(raw, series):
    with pytest.raises(ValueError):
        module.parse_csv(raw, series)


def test_http_transport_retries_timeout_and_records_actual_bytes(tmp_path, monkeypatch):
    calls = []
    raw = b"observation_date,UNRATE\n2020-01-01,3.5\n"

    def download(arguments, **kwargs):
        calls.append(arguments)
        assert "--location" not in arguments and "--proto" in arguments
        assert arguments[-1] == "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE"
        return SimpleNamespace(returncode=28 if len(calls) == 1 else 0, stdout=raw + b"\n200")

    monkeypatch.setattr(module.subprocess, "run", download)
    records, metadata = module.fetch("UNRATE", tmp_path)
    assert len(records) == 1 and metadata["download_attempts"] == 2
    assert metadata["bytes"] == len(raw)
    assert (tmp_path / "UNRATE.csv").read_bytes() == raw


def test_http_redirect_is_rejected_without_writing_source(tmp_path, monkeypatch):
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=0, stdout=b"redirect\n302"))
    with pytest.raises(ValueError, match="HTTP status"):
        module.fetch("UNRATE", tmp_path)
    assert not (tmp_path / "UNRATE.csv").exists()
