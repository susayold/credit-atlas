"""Atomic research-review behavior; all examples are synthetic QA text."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from credit_atlas.reviews import Reviews, ReviewConflict


def payload(**changes):
    return {"title": "Synthetic QA", "body": "<script>untrusted note</script>",
            "view": "portfolio", "filters": {"segment": "relief", "basis": "count"},
            "evidence_refs": ["portfolio_monthly"], **changes}


def test_review_reopens_with_original_context_and_append_only_history(tmp_path):
    path = tmp_path / "reviews.sqlite3"
    first = Reviews(path).save("case-A", payload())
    reopened = Reviews(path)
    assert reopened.list("case-A") == [first]
    second = reopened.save("case-A", payload(revision=1, status="reviewed"), first["id"])
    assert second["created_at"] == first["created_at"]
    assert [r["record"] for r in reopened.history("case-A", first["id"])] == [first, second]
    assert reopened.list("case-B") == []
    with pytest.raises(KeyError):
        reopened.history("case-B", first["id"])
    with pytest.raises(KeyError):
        reopened.save("case-B", payload(revision=2), first["id"])
    assert reopened.list("case-A") == [second]


def test_two_reviewers_cannot_silently_overwrite_each_other(tmp_path):
    reviews = Reviews(tmp_path / "reviews.sqlite3")
    first = reviews.save("case-A", payload())

    def update(title):
        try:
            return reviews.save("case-A", payload(title=title, revision=1), first["id"])
        except ReviewConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, ["reviewer A", "reviewer B"]))
    assert results.count("conflict") == 1
    assert reviews.list("case-A")[0]["revision"] == 2
    assert len(reviews.history("case-A", first["id"])) == 2


@pytest.mark.parametrize("changes", [
    {"view": []}, {"status": {}}, {"evidence_refs": [[]]},
    {"evidence_refs": ["portfolio_monthly", "portfolio_monthly"]},
    {"filters": {"loan_id": "private-source-id"}}, {"title": " "},
    {"body": "x" * 10001},
])
def test_invalid_review_cannot_create_partial_history(tmp_path, changes):
    reviews = Reviews(tmp_path / "reviews.sqlite3")
    with pytest.raises(ValueError):
        reviews.save("case-A", payload(**changes))
    assert reviews.list("case-A") == []


@pytest.mark.parametrize("revision", [True, None, "1", 0])
def test_invalid_revision_does_not_change_finding(tmp_path, revision):
    reviews = Reviews(tmp_path / "reviews.sqlite3")
    first = reviews.save("case-A", payload())
    with pytest.raises(ReviewConflict):
        reviews.save("case-A", payload(revision=revision), first["id"])
    assert reviews.list("case-A") == [first]
    assert len(reviews.history("case-A", first["id"])) == 1
