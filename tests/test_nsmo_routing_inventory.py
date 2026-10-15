import csv
from collections import Counter
from pathlib import Path

import pytest

from scripts.build_nsmo_routing_inventory import build


ROOT = Path(__file__).parents[1]


def test_routing_inventory_covers_survey_fields_and_reconciles_seven_missing_references(tmp_path):
    output = tmp_path / "routing.csv"
    result = build(ROOT / "docs/data/nsmo-v70-field-dictionary.csv", output,
                   ROOT / "docs/data/nsmo-v70-question-reference-reconciliation.csv")
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert result["rows"] == 319
    assert len({row["csv_column"] for row in rows}) == 319
    statuses = Counter(row["route_review_status"] for row in rows)
    assert statuses == {
        "CONDITIONAL_ROUTING_DOCUMENTED": 58,
        "LEGACY_GATEWAY_MAPPING_REQUIRED": 12,
        "NO_CONDITION_LISTED_IN_CODEBOOK": 249,
    }
    assert Counter(row["question_reference_status"] for row in rows) == {
        "EXPLICIT_IN_CODEBOOK": 312, "RECONCILED_FROM_FIELD_ID_AND_QUESTIONNAIRE": 7}
    by_field = {row["csv_column"]: row for row in rows}
    assert by_field["x53b_1"]["route_review_status"] == "LEGACY_GATEWAY_MAPPING_REQUIRED"
    assert by_field["x53b_1"]["resolved_question_refs"] == "Q53"
    assert by_field["x53b_1"]["question_reference_status"] == "RECONCILED_FROM_FIELD_ID_AND_QUESTIONNAIRE"
    assert by_field["x80s_1"]["route_review_status"] == "CONDITIONAL_ROUTING_DOCUMENTED"
    assert by_field["x14d_1"]["resolved_question_refs"] == "Q14"
    assert by_field["x14d_1"]["label_phrase_check"] == "MATCHED_IN_QUESTIONNAIRE_TEXT"
    assert by_field["x17g_1"]["route_review_status"] == "NO_CONDITION_LISTED_IN_CODEBOOK"
    assert "historical wording/scale variant" in by_field["x17g_1"]["routing_review_required"]
    assert by_field["x17g_1"]["label_phrase_check"] == "WAVE_VARIANT_REVIEW"
    assert "not proof" in by_field["x05a"]["routing_review_required"]


def test_question_reference_reconciliation_requires_full_wave_coverage(tmp_path):
    source = ROOT / "docs/data/nsmo-v70-field-dictionary.csv"
    original = ROOT / "docs/data/nsmo-v70-question-reference-reconciliation.csv"
    with original.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["questionnaire_wave_coverage"] = "1-6"
    broken = tmp_path / "reconciliation.csv"
    with broken.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="identifier/wave/evidence checks"):
        build(source, tmp_path / "routing.csv", broken)
