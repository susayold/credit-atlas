import json
from copy import deepcopy
from pathlib import Path

import pytest

from credit_atlas import project_register as module


def test_project_register_exposes_the_source_and_plan_inventory():
    result = module.project_register()

    assert len(result["source_records"]) == 123
    assert len(result["datasets"]) == 28
    assert len(result["method_cards"]) == 15
    assert len(result["capabilities"]) == 50
    assert result["progress"]["completed"] == 26
    assert result["source_group_disposition_summary"] == {
        "groups": 5,
        "private_source_or_input_present": 1,
        "derived_output_present": 3,
        "access_pending_no_production": 1,
    }
    assert len(result["source_group_dispositions"]) == 5
    macro_group = next(row for row in result["datasets"]
                       if row["id"] == "fred-alfred-macro-market-context")
    macro_sources = {row["source_id"]: row for row in result["source_records"]
                     if row["source_id"].startswith(("fred-", "fred-alfred-"))}
    expected_macro_sources = {
        "fred-unrate", "fred-ussthpi", "fred-mortgage30us", "fred-dgs2", "fred-dgs10",
        "fred-dgs30", "fred-bamlc0a0cm", "fred-alfred-unrate-pit",
        "fred-alfred-ussthpi-pit", "fred-alfred-mortgage30us-pit",
    }
    assert set(macro_group["source_release_record_ids"]) == expected_macro_sources
    assert set(macro_sources) == expected_macro_sources
    assert all(row["registry_group_id"] == macro_group["id"] for row in macro_sources.values())
    assert all("NO_PUBLIC" in row["rights_review_status"] or "WRITTEN_THIRD_PARTY" in row["rights_review_status"]
               for row in macro_sources.values())
    freddie = next(row for row in result["source_records"]
                   if row["source_id"] == "freddie-sfll-2012-user-supplied")
    assert freddie["registry_group_id"] == "freddie-2012"
    assert freddie["receipt_received_at_utc"] == "2026-09-09T20:02:22.727558+00:00"
    assert freddie["retrieved_at_utc"] is None
    assert freddie["publisher_release_authenticated"] is False
    assert freddie["public_release_approved_in_receipt"] is False
    assert freddie["sha256_prefix"] == "35c415821578"
    assert freddie["file_profiles"][0]["rows"] == 50000
    assert freddie["file_profiles"][1]["rows"] == 4510559
    assert "2012-01" in freddie["scope_note"] and "2026-03" in freddie["scope_note"]
    assert "D:\\" not in str(freddie) and "data/private/" not in str(freddie)
    assert "35c41582157804e3f632d68140246fcc6eb0973590ba0cf9a0f03600bf8499f9" not in str(freddie)
    apple = {row["source_id"]: row for row in result["source_records"]
             if row["source_id"].startswith("apple-2025-")}
    assert set(apple) == {
        "apple-2025-10k-issuer-html",
        "apple-2025-xbrl-issuer-zip",
        "apple-2025-inline-xbrl-issuer-html",
    }
    assert all(row["registry_group_id"] == "sec-filings-financials"
               and row["sec_accession"] == "0000320193-25-000079"
               and row["issuer_copy_byte_parity_verified"] is False
               and row["public_release_approved_in_receipt"] is False
               for row in apple.values())
    assert "D:\\" not in str(apple) and "data/private/" not in str(apple)
    private_evidence_ids = [
        ref for row in result["source_group_dispositions"] for ref in row["evidence_refs"]
        if ref.startswith("local-private-id:")
    ]
    assert private_evidence_ids
    assert all("/" not in ref and "\\" not in ref for ref in private_evidence_ids)
    ginnie = next(row for row in result["source_group_dispositions"]
                  if row["registry_id"] == "ginnie-loanperf-production")
    assert ginnie["data_state"] == "ACCESS_PENDING_NO_PRODUCTION_DATA"
    assert ginnie["classification"] == "access_pending"
    abs_sources = {row["source_id"]: row for row in result["source_records"]
                   if row["source_id"].startswith("sec-")}
    assert set(abs_sources) == {
        "sec-toyota-2022b-abs-ee-history", "sec-toyota-2022b-10d-certificates",
        "sec-toyota-2024b-abs-ee-history", "sec-toyota-2024b-10d-certificates",
        "sec-nissan-2024b-abs-ee-history", "sec-nissan-2024b-10d-certificates",
        "sec-woart-2025a-abs-ee-history",
    }
    assert {source_id: row["file_profiles"][0]["report_count"]
            for source_id, row in abs_sources.items()} == {
        "sec-toyota-2022b-abs-ee-history": 51,
        "sec-toyota-2022b-10d-certificates": 51,
        "sec-toyota-2024b-abs-ee-history": 29,
        "sec-toyota-2024b-10d-certificates": 29,
        "sec-nissan-2024b-abs-ee-history": 23,
        "sec-nissan-2024b-10d-certificates": 23,
        "sec-woart-2025a-abs-ee-history": 20,
    }
    assert all(row["public_release_approved_in_receipt"] is False
               and row["sha256_prefix"] is None for row in abs_sources.values())
    assert "data/private/" not in str(abs_sources)
    assert not any(row["registry_id"] in {"toyota-2022b-absee", "toyota-2024b-absee",
                                          "nissan-2024b-absee", "world-omni-2025a"}
                   for row in result["source_group_dispositions"])
    hamp_source = next(row for row in result["source_records"]
                       if row["source_id"] == "treasury-hamp-performance-update-2023-02")
    assert hamp_source["retrieved_at_utc"] == "2026-10-16T03:12:09.620901+00:00"
    assert hamp_source["source_object_url"] == "https://home.treasury.gov/system/files/256/HMP_Govt_Agency_Perf_Data.zip"
    assert hamp_source["observed_period_start"] == "2022-01-01"
    assert hamp_source["observed_period_end"] == "2023-02-01"
    assert hamp_source["endpoint_linkage_check_reference"].startswith("local-private-id:")
    assert "2018–2021" in hamp_source["scope_note"] and "Do not infer zero" in hamp_source["scope_note"]
    assert "D:" not in str(hamp_source) and "data/private/" not in str(hamp_source)
    repo = Path(__file__).resolve().parents[1]
    source_register = json.loads((repo / "docs/data/creditatlas-source-release-register-2026-10-17.json").read_text(encoding="utf-8"))
    trace_map = json.loads((repo / "docs/data/n02-source-to-kpi-map-2026-10-17.json").read_text(encoding="utf-8"))
    project_register = json.loads((repo / "docs/data/creditatlas-project-register-2026-10-17.json").read_text(encoding="utf-8"))
    crosswalk = trace_map["supplemental_source_record_crosswalk"]
    assert source_register["record_count"] == len(source_register["source_records"]) == 123
    assert source_register["supplemental_source_records"] == len(source_register["source_records"]) - 20 == 103
    assert trace_map["source_release_register"]["supplemental_source_records"] == len(crosswalk) == 103
    assert trace_map["source_release_register"]["supplemental_source_families"] == 17
    assert trace_map["counts"]["source_level_records"] == trace_map["counts"]["supplemental_source_records"] == 103
    assert trace_map["counts"]["registered_dataset_domain_records"] == 28
    assert trace_map["counts"]["registry_groups_with_source_objects"] == 23
    assert trace_map["counts"]["source_catalog_ids_with_parent_record"] == 20
    assert trace_map["counts"]["source_catalog_ids_without_parent_record"] == 0
    assert project_register["source_group_disposition_summary"] == result["source_group_disposition_summary"]
    freddie_trace = next(row for row in trace_map["registered_record_trace"]
                         if row["registry_id"] == "freddie-2012")
    assert freddie_trace["source_release_record_ids"] == ["freddie-sfll-2012-user-supplied"]
    assert not any(row["registry_id"] == "freddie-2012"
                   for row in trace_map["source_group_dispositions"])
    apple_trace = next(row for row in trace_map["registered_record_trace"]
                       if row["registry_id"] == "sec-filings-financials")
    assert set(apple_trace["source_release_record_ids"]) == set(apple)
    assert not any(row["registry_id"] == "sec-filings-financials"
                   for row in trace_map["source_group_dispositions"])
    exposure = next(row for row in result["datasets"] if row["id"] == "exposure-actual-2026-03")
    assert "not owned" in exposure["grain"]
    assert "not an actual lender book" in exposure["use"]
    exposure_disposition = next(row for row in result["source_group_dispositions"]
                                if row["registry_id"] == "exposure-actual-2026-03")
    assert exposure_disposition["data_state"] == "PRIVATE_FREDDIE_SAMPLE_DERIVED_UPB_DIAGNOSTIC"
    assert "ownership" in exposure_disposition["formal_binding"]
    assert (repo / "docs/SEC_APPLE_2025_FILING_AND_EXPOSURE_ORIGIN_REVIEW_VI.md").is_file()
    hud_flow = next(row for row in result["source_records"] if row["source_id"] == "hud-fha-production-transitions-2026-08")
    assert hud_flow["native_row_count"] == 13 and hud_flow["sha256_prefix"] is None
    hamp = next(row for row in result["datasets"] if row["id"] == "treasury-hamp")
    assert {
        "treasury-hamp-performance-update-2023-02",
        "treasury-hamp-performance-user-guide-v1",
    }.issubset(set(hamp["source_release_record_ids"]))
    hamp_quarterly = {source_id for source_id in hamp["source_release_record_ids"]
                      if source_id.startswith("treasury-hamp-summary-")}
    assert len(hamp_quarterly) == 20
    assert "treasury-hamp-summary-2021q3" not in hamp_quarterly
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
    method_by_id = {row["id"]: row for row in result["method_cards"]}
    source_by_id = {row["source_id"]: row for row in result["source_records"]}
    assert len(method_by_id) == 15
    assert all(row["source_release_record_ids"] for row in method_by_id.values())
    for method in method_by_id.values():
        assert method["evidence_refs"]
        assert all((repo / ref).is_file() for ref in method["evidence_refs"])
        for source_id in method["source_release_record_ids"]:
            assert method["id"] in source_by_id[source_id]["method_card_ids"]
    for source in source_by_id.values():
        for method_id in source["method_card_ids"]:
            assert source["source_id"] in method_by_id[method_id]["source_release_record_ids"]
    assert method_by_id["d01-adjacent-transition-share"]["source_release_record_ids"] == [
        "freddie-sfll-2012-user-supplied"
    ]
    assert method_by_id["uci350-next-month-benchmark"]["source_release_record_ids"] == [
        "uci-retail", "uci-retail-metadata"
    ]
    assert method_by_id["uci365-bankruptcy-one-year"]["source_release_record_ids"] == [
        "uci-bankruptcy", "uci-bankruptcy-metadata"
    ]
    assert method_by_id["p4-declared-ecl"]["source_linkage_note"].startswith("Freddie 2012 sample is upstream")
    assert "World Omni" in method_by_id["structured-abs-surveillance"]["source_linkage_note"]
    assert "P4" in source_by_id["freddie-sfll-2012-user-supplied"]["modules"]
    lendingclub = method_by_id["lendingclub-source-population-and-label-readiness"]
    assert lendingclub["evidence_refs"] == [
        "docs/LENDINGCLUB_FULL_SOURCE_VI.md",
        "docs/LENDINGCLUB_SOURCE_PROFILE_VI.md",
        "docs/LENDINGCLUB_DICTIONARY_REVIEW_VI.md",
    ]


@pytest.mark.parametrize(
    ("filename", "mutate", "message"),
    [
        (
            "creditatlas-project-register-2026-10-17.json",
            lambda data: data["datasets"][0].update(source_release_record_ids=["missing-source"]),
            "Dataset registry references unknown IDs",
        ),
        (
            "creditatlas-project-register-2026-10-17.json",
            lambda data: data["method_cards"][0].update(source_release_record_ids=["missing-source"]),
            "Method cards references unknown IDs",
        ),
        (
            "creditatlas-project-register-2026-10-17.json",
            lambda data: data["method_cards"][0].update(evidence="docs/missing-evidence.md"),
            "Method card evidence path is missing",
        ),
        (
            "creditatlas-source-release-register-2026-10-17.json",
            lambda data: data["source_records"][0].update(method_card_ids=[]),
            "trace is not reciprocal",
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
        (
            "n02-source-to-kpi-map-2026-10-17.json",
            lambda data: data["source_group_dispositions"].pop(),
            "N02 source-group dispositions must cover every unbound registry group exactly once",
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
