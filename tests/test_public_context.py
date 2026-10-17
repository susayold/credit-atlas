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


def test_direct_fhfa_hpi_is_pinned_normalized_and_attributed(tmp_path, monkeypatch):
    import io

    codes = ["USA", "DV_ENC", "DV_ESC", "DV_MA", "DV_MT", "DV_NE", "DV_PAC", "DV_SA", "DV_WNC", "DV_WSC"]
    raw = "".join(f"{code},2025,{quarter},{100 + quarter}.00\n"
                  for code in codes for quarter in (1, 2)).encode()

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Type": "text/csv; charset=utf-8", "Content-Length": str(len(raw))}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

        def geturl(self):
            return module.FHFA_US_CENSUS_HPI_URL

    monkeypatch.setattr(module, "urlopen", lambda request, timeout: Response(raw))
    records, metadata = module.fetch_fhfa_us_hpi(tmp_path)

    assert len(records) == 2
    assert [row["observation_date"].isoformat() for row in records] == ["2025-01-01", "2025-04-01"]
    assert metadata["source_url"] == module.FHFA_US_CENSUS_HPI_URL
    assert metadata["rights_review_status"].startswith("FHFA_SAYS_DATA_FREELY_AVAILABLE")
    assert metadata["attribution"].startswith("Source: FHFA HPI")
    assert metadata["source_object_sha256"]
    assert (tmp_path / "fhfa-us-census-hpi-source.csv").read_bytes() == raw
    assert (tmp_path / "USSTHPI.csv").read_text(encoding="utf-8").splitlines() == [
        "observation_date,USSTHPI", "2025-01-01,101.00", "2025-04-01,102.00"
    ]


def test_direct_fhfa_hpi_redirect_fails_closed(tmp_path, monkeypatch):
    import io

    raw = b"USA,2025,1,100.00\n"

    class RedirectedResponse(io.BytesIO):
        status = 200
        headers = {"Content-Type": "text/csv"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

        def geturl(self):
            return "https://example.invalid/redirected.csv"

    monkeypatch.setattr(module, "urlopen", lambda request, timeout: RedirectedResponse(raw))
    with pytest.raises(ValueError, match="status or redirect"):
        module.fetch_fhfa_us_hpi(tmp_path)
    assert not (tmp_path / "fhfa-us-census-hpi-source.csv").exists()
