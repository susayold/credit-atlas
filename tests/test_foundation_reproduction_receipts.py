import json

from credit_atlas.foundation import write_reproduction_receipt


def test_repeat_reproduction_preserves_primary_receipt_and_writes_versioned_receipt(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    primary = case / "reproduction.json"
    primary.write_text('{"right_pipeline":"pipeline-original"}\n', encoding="utf-8")
    result = {"status": "PASS", "right_pipeline": "pipeline-new"}

    path = write_reproduction_receipt(case, result)

    assert path == case / "reproduction-pipeline-new.json"
    assert json.loads(primary.read_text(encoding="utf-8")) == {"right_pipeline": "pipeline-original"}
    assert json.loads(path.read_text(encoding="utf-8")) == result


def test_initial_reproduction_uses_primary_receipt(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    result = {"status": "PASS", "right_pipeline": "pipeline-new"}

    path = write_reproduction_receipt(case, result)

    assert path == case / "reproduction.json"
    assert json.loads(path.read_text(encoding="utf-8")) == result
