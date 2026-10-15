import csv
from collections import Counter
from pathlib import Path

import pytest

from scripts.build_nsmo_predictor_gate_inventory import build, classify


ROOT = Path(__file__).parents[1]


def test_public_predictor_gate_inventory_covers_all_587_fields_and_stays_unapproved():
    source = ROOT / "docs/data/nsmo-v70-field-dictionary.csv"
    output = ROOT / "docs/data/nsmo-v70-predictor-gates.csv"
    result = build(source, output)
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert result["rows"] == 587
    assert len({row["csv_column"] for row in rows}) == 587
    assert not any(row["decision_status"].startswith("APPROVED") for row in rows)
    buckets = Counter(row["eligibility_bucket"] for row in rows)
    assert buckets["POST_ORIGINATION_RESPONSE_EXCLUDE"] == 319
    assert buckets["DYNAMIC_CANDIDATE_ASOF"] == 125
    assert buckets["DYNAMIC_CANDIDATE_LOOKAHEAD_REVIEW"] == 51
    assert buckets["OUTCOME_HISTORY_OR_LAGGED_ONLY"] == 51
    assert buckets["SENSITIVE_OR_PROXY_POLICY_REVIEW"] == 7
    by_name = {row["csv_column"]: row for row in rows}
    assert by_name["open_year"]["eligibility_bucket"] == "COHORT_AND_TIME_CONTROL_ONLY"
    assert by_name["sex_o1"]["decision_status"] == "NOT_APPROVED_GOVERNANCE_REVIEW_REQUIRED"
    assert by_name["analysis_weight"]["eligibility_bucket"] == "ESTIMATION_WEIGHT_ONLY"


def test_unknown_field_family_fails_closed():
    with pytest.raises(ValueError, match="Unclassified NSMO field family"):
        classify({"csv_column": "surprise", "field_family": "new_unreviewed_family",
                  "timing_class": "unknown", "predictor_use": "REVIEW"})
