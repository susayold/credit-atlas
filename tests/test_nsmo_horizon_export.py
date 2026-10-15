import csv
import json

from scripts.export_nsmo_horizon_sensitivity import export


def test_export_keeps_repeated_and_single_landmark_bases_aggregate_only(tmp_path):
    receipt = {
        "horizon_results": [{
            "horizon_quarters": 2, "approx_months": 6,
            "c_baseline_snapshots_with_full_horizon_unweighted": 4,
            "unique_mortgages_with_at_least_one_c_baseline": 2,
            "snapshot_outcomes_unweighted": {
                "observed_90plus_event": 1,
                "observed_no_90plus_within_2_quarters": 3,
            },
            "unique_mortgages_by_outcome_nonexclusive": {
                "observed_90plus_event": 1,
                "observed_no_90plus_within_2_quarters": 2,
            },
            "by_origination_year": [{
                "origination_year": "2013",
                "c_baseline_snapshots_with_full_horizon_unweighted": 4,
                "unique_mortgages_with_at_least_one_c_baseline": 2,
                "snapshot_outcomes_unweighted": {
                    "observed_90plus_event": 1,
                    "observed_no_90plus_within_2_quarters": 3,
                },
                "unique_mortgages_by_outcome_nonexclusive": {
                    "observed_90plus_event": 1,
                    "observed_no_90plus_within_2_quarters": 2,
                },
            }],
            "one_landmark_per_mortgage": {
                "mortgages_with_eligible_landmark": 2,
                "outcomes_unweighted": {
                    "observed_90plus_event": 1,
                    "observed_no_90plus_within_2_quarters": 1,
                },
                "unique_mortgages_by_outcome": {
                    "observed_90plus_event": 1,
                    "observed_no_90plus_within_2_quarters": 1,
                },
                "by_origination_year": [{
                    "origination_year": "2013",
                    "mortgages_with_eligible_landmark": 2,
                    "outcomes_unweighted": {
                        "observed_90plus_event": 1,
                        "observed_no_90plus_within_2_quarters": 1,
                    },
                    "unique_mortgages_by_outcome": {
                        "observed_90plus_event": 1,
                        "observed_no_90plus_within_2_quarters": 1,
                    },
                }],
            },
        }],
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    interpretations = tmp_path / "interpretations.csv"
    interpretations.write_text(
        "outcome_class,outcome_interpretation\n"
        "90PLUS,Observed 90+\n"
        "NO_90PLUS,No observed 90+\n",
        encoding="utf-8",
    )
    output = tmp_path / "public.csv"

    assert export(receipt_path, output, interpretations) == 8
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["landmark_basis"] for row in rows} == {
        "repeated_c_landmarks", "one_earliest_c_per_mortgage",
    }
    repeated_positive = next(row for row in rows
                             if row["landmark_basis"] == "repeated_c_landmarks"
                             and row["outcome_class"] == "90PLUS" and row["scope"] == "all")
    single_positive = next(row for row in rows
                           if row["landmark_basis"] == "one_earliest_c_per_mortgage"
                           and row["outcome_class"] == "90PLUS" and row["scope"] == "all")
    assert repeated_positive["snapshot_count"] == "1"
    assert repeated_positive["unique_mortgage_count_nonexclusive"] == "1"
    assert single_positive["snapshot_count"] == "1"
    assert "NSMOID" not in output.read_text(encoding="utf-8")
