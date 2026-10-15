import pytest

from scripts.audit_nsmo_weighted_tabulations import extract_table1_response_rows


def test_extracts_all_21_response_rows_and_22_year_group_values():
    lines = []
    for item in range(7):
        for label in ("Very", "Somewhat", "Not at all"):
            values = " ".join(f"{(item + index) % 101}%" for index in range(22))
            lines.append(f"{label} {values}")
    result = extract_table1_response_rows("\n".join(lines))

    assert len(result) == 21
    assert result[0] == ("1", list(range(0, 22)))
    assert result[-1] == ("3", list(range(6, 28)))


def test_rejects_incomplete_published_table():
    with pytest.raises(ValueError, match="Expected 22"):
        extract_table1_response_rows("Very 1% 2%")
