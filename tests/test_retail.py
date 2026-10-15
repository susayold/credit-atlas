import copy

import pytest

from credit_atlas.retail import (FEATURE_NAMES, DEMOGRAPHIC_EXCLUSIONS, NUMERIC_FEATURES,
                                 CATEGORICAL_FEATURES, PROTOCOL, canonical_rows, assign_partitions)


def metadata():
    return {"data": {"uci_id": 350, "target_col": ["Y"], "variables": [
        {"name":"X"+str(i),"role":"Feature","description":name}
        for i,name in enumerate(FEATURE_NAMES,1)]}}


def raw_file(tmp_path, **changes):
    fields = ["ID"] + ["X"+str(i) for i in range(1,24)] + ["Y"]
    row = dict.fromkeys(fields, "0")
    row.update(ID="1", X1="20000", X2="1", X3="5", X4="0", X5="30", X6="-2", X12="-100", Y="1")
    row.update(changes)
    path = tmp_path / "retail.csv"
    path.write_text(",".join(fields)+"\n"+",".join(row[name] for name in fields)+"\n")
    return path


def test_source_codes_and_signed_statements_preserved_and_demographics_excluded(tmp_path):
    row = canonical_rows(raw_file(tmp_path), metadata())[0]
    assert row["PAY_0"] == -2 and row["BILL_AMT1"] == -100
    assert row["EDUCATION"] == 5 and row["MARRIAGE"] == 0
    assert not set(DEMOGRAPHIC_EXCLUSIONS + ["source_client_id","target"]) & set(NUMERIC_FEATURES+CATEGORICAL_FEATURES)
    assert set(FEATURE_NAMES) == set(NUMERIC_FEATURES+CATEGORICAL_FEATURES+DEMOGRAPHIC_EXCLUSIONS)


@pytest.mark.parametrize("changes", [{"Y":"2"}, {"Y":"1.0"}, {"X1":"nan"}, {"X18":"-1"}, {"X6":"10"}])
def test_invalid_source_target_and_values_rejected(tmp_path, changes):
    with pytest.raises(ValueError):
        canonical_rows(raw_file(tmp_path, **changes), metadata())


def test_metadata_mapping_change_rejected_before_canonical_parse(tmp_path):
    changed = copy.deepcopy(metadata())
    changed["data"]["variables"][0]["description"] = "post_outcome_balance"
    with pytest.raises(ValueError, match="metadata"):
        canonical_rows(raw_file(tmp_path), changed)


def test_partitions_order_invariant_disjoint_and_class_stratified():
    rows = [{"source_client_id":i+1,"target":i%2} for i in range(200)]
    assignments = assign_partitions(rows)
    assert assignments == assign_partitions(rows[::-1])
    assert len(assignments)==len({row["source_client_id"] for row in assignments})==200
    assert {row["partition"] for row in assignments} == set(PROTOCOL["fractions"])
    for target in (0,1):
        assert [sum(row["target"]==target and row["partition"]==role for row in assignments)
                for role in PROTOCOL["fractions"]] == [60,15,15,10]
    with pytest.raises(ValueError, match="Duplicate"):
        assign_partitions(rows+[rows[0]])
    with pytest.raises(ValueError, match="binary"):
        assign_partitions([{ "source_client_id":1, "target":2}])
