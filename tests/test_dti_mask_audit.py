from __future__ import annotations

import pytest

from credit_atlas.dti_mask_audit import aggregate_train_rows, require_no_final_test_source


def row(identity, *, segment=False, raw="20", value=20, target=0, partition="train", included=True):
    return {
        "loan_id": identity,
        "partition": partition,
        "included": included,
        "target": target,
        "is_relief_refinance": segment,
        "raw_original_dti": raw,
        "original_dti": value,
    }


def test_zero_dti_is_observed_not_missing():
    result = aggregate_train_rows([row("a", raw="0", value=0)])
    assert result == [{"segment": "Non-Relief", "dti_status": "observed",
                       "loans": 1, "positive": 0, "negative": 1}]


def test_relief_999_and_nonrelief_999_remain_same_ambiguous_source_status():
    result = aggregate_train_rows([
        row("a", segment=True, raw="999", value=None, target=1),
        row("b", segment=False, raw="999", value=None),
    ])
    assert result == [
        {"segment": "Non-Relief", "dti_status": "sentinel_999_censored_or_unavailable",
         "loans": 1, "positive": 0, "negative": 1},
        {"segment": "Relief", "dti_status": "sentinel_999_censored_or_unavailable",
         "loans": 1, "positive": 1, "negative": 0},
    ]


def test_final_test_vintage_is_rejected_before_source_scan():
    study = {"protocol": {"test_years": [2018]}, "source_years": [2012],
             "support": {"test": {"positive": 0, "negative": 0}}}
    require_no_final_test_source(study)
    study["source_years"].append(2018)
    with pytest.raises(ValueError, match="final-test vintages"):
        require_no_final_test_source(study)


@pytest.mark.parametrize("rows", [
    [row("a"), row("a")],
    [row("a", partition="test")],
    [row("a", included=False)],
    [row("a", raw="999", value=65)],
    [row("a", raw="66", value=66)],
    [row("a", target=2)],
])
def test_rejects_bad_grain_scope_or_sentinel_mapping(rows):
    with pytest.raises(ValueError):
        aggregate_train_rows(rows)

