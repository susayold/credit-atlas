import shutil
from pathlib import Path

from credit_atlas.nmdb_aggregate import read


def test_public_nmdb_context_falls_back_to_receipted_national_slice(tmp_path):
    source = Path(__file__).parents[1] / "docs" / "data"
    target = tmp_path / "docs" / "data"
    target.mkdir(parents=True)
    for name in (
        "nmdb-performance-national-quarterly-2026q2.csv",
        "nmdb-performance-national-quarterly-2026q2-receipt.json",
    ):
        shutil.copyfile(source / name, target / name)

    report = read(tmp_path)

    assert report["status"] == "AVAILABLE"
    assert report["source_package_scope"] == "National / Census Areas package · National rows only"
    assert report["periods"] == 98
    assert (report["first_period"], report["last_period"]) == ("2002Q1", "2026Q2")
    assert len(report["rows"]) == 98
    assert report["quality"]["coverage_observations"] == 392
    assert report["quality"]["all_geography_rows"] is None
    assert report["quality"]["suppressed_rows"] == 0
    assert report["rows"][0]["PFORB"] is None
    assert report["rows"][-1]["PFORB"] == 0.5
    assert any("does not expose or count the all-geography archive" in note
               for note in report["scope_notes"])


def test_private_all_geography_nmdb_package_remains_primary_when_present():
    root = Path(__file__).parents[1]
    packages = list((root / "data" / "private" / "public-context").glob("fhfa-nmdb-performance-*"))
    package = next((path for path in packages if (path / "official-performance-quarterly.zip").is_file()), None)
    if package is None:
        return

    report = read(root)

    assert report["status"] == "AVAILABLE"
    assert report["quality"]["all_geography_rows"] == 261_856
    assert report["quality"]["coverage_observations"] == 261_856
    assert report["source_url"].endswith("nmdb-mortgage-performance-statistics-all-quarterly.zip")
