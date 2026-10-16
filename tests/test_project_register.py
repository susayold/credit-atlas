from copy import deepcopy
from pathlib import Path

import pytest

from credit_atlas import project_register as module


def test_project_register_exposes_the_source_and_plan_inventory():
    result = module.project_register()

    assert len(result["source_records"]) == 91
    assert len(result["datasets"]) == 27
    assert len(result["method_cards"]) == 15
    assert len(result["capabilities"]) == 50
    assert result["progress"]["completed"] == 26
    hamp = next(row for row in result["datasets"] if row["id"] == "treasury-hamp")
    assert set(hamp["source_release_record_ids"]) == {
        "treasury-hamp-performance-update-2023-02",
        "treasury-hamp-performance-user-guide-v1",
    }
    wdi = next(row for row in result["datasets"] if row["id"] == "world-bank-wdi")
    assert len(wdi["source_release_record_ids"]) == 22
    assert set(wdi["source_release_record_ids"]).issubset({row["source_id"] for row in result["source_records"]})
    sovereign = next(row for row in result["datasets"] if row["id"] == "sovereign-archive")
    assert len(sovereign["source_release_record_ids"]) == 12
    assert set(sovereign["source_release_record_ids"]).issubset({row["source_id"] for row in result["source_records"]})
    hmda_method = next(row for row in result["method_cards"] if row["id"] == "hmda-denial-share-by-decided")
    assert len(hmda_method["source_release_record_ids"]) == 9
    assert "n_1+n_2+n_3" in hmda_method["method"] and "n_3" in hmda_method["method"]
    assert (Path(__file__).resolve().parents[1] / hmda_method["evidence"]).is_file()
    nmdb_method = next(row for row in result["method_cards"] if row["id"] == "nmdb-origination-stock-market-context")
    assert len(nmdb_method["source_release_record_ids"]) == 2
    assert "VALUE1" in nmdb_method["method"] and "VALUE2" in nmdb_method["method"]
    assert (Path(__file__).resolve().parents[1] / nmdb_method["evidence"]).is_file()


@pytest.mark.parametrize(
    ("filename", "mutate", "message"),
    [
        (
            "creditatlas-project-register-2026-10-17.json",
            lambda data: data["datasets"][0].update(source_release_record_ids=["missing-source"]),
            "Dataset registry references unknown IDs",
        ),
        (
            "creditatlas-source-release-register-2026-10-17.json",
            lambda data: data["source_records"][0].update(method_card_ids=["missing-method-card"]),
            "Source release register references unknown IDs",
        ),
        (
            "creditatlas-source-release-register-2026-10-17.json",
            lambda data: data["source_records"][0].update(registry_group_id="missing-dataset-group"),
            "Source release register references unknown IDs",
        ),
        (
            "n02-source-to-kpi-map-2026-10-17.json",
            lambda data: data["supplemental_source_record_crosswalk"][0].update(
                source_release_record_id="missing-source"
            ),
            "N02 supplemental crosswalk references unknown IDs",
        ),
        (
            "n02-source-to-kpi-map-2026-10-17.json",
            lambda data: data["registry_source_id_crosswalk"][0].update(
                parent_registry_id="missing-dataset-group"
            ),
            "N02 registry-source crosswalk references unknown IDs",
        ),
    ],
)
def test_project_register_rejects_dangling_lineage_ids(monkeypatch, filename, mutate, message):
    read_json = module._read_json

    def read_with_mutation(path):
        data = read_json(path)
        if path.name == filename:
            data = deepcopy(data)
            mutate(data)
        return data

    monkeypatch.setattr(module, "_read_json", read_with_mutation)
    with pytest.raises(ValueError, match=message):
        module.project_register()
