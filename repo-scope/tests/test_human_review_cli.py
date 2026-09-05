from __future__ import annotations

import csv

import pytest

from scripts.review_human_labels import pending_reviews, save_review, visible_evidence


def test_visible_evidence_hides_automation_fields():
    row = {
        "repo": "org/example",
        "snapshot_at_utc": "2026-09-05T00:00:00+00:00",
        "language": "Python",
        "stars": "10",
        "archived": "0",
        "latest_release_age_days": "165",
        "review_reason": "ambiguous_release_boundary",
        "weak_label": "watch",
        "predicted_label": "healthy",
        "confidence": "0.91",
        "health_score": "88",
    }

    evidence = visible_evidence(row)

    assert evidence["repo"] == "org/example"
    assert "review_reason" not in evidence
    assert "weak_label" not in evidence
    assert "predicted_label" not in evidence
    assert "confidence" not in evidence
    assert "health_score" not in evidence


def test_pending_reviews_is_reviewer_specific():
    queue = [{"repo": "org/a"}, {"repo": "org/b"}]
    decisions = [
        {"repo": "org/a", "human_label": "healthy", "reviewer": "reviewer-a"},
        {"repo": "org/b", "human_label": "watch", "reviewer": "reviewer-b"},
    ]

    pending_for_a = pending_reviews(queue, decisions, "reviewer-a")
    pending_for_b = pending_reviews(queue, decisions, "reviewer-b")

    assert [row["repo"] for row in pending_for_a] == ["org/b"]
    assert [row["repo"] for row in pending_for_b] == ["org/a"]


def test_save_review_requires_provenance_and_notes(tmp_path):
    decisions = tmp_path / "decisions.csv"

    with pytest.raises(ValueError, match="Reviewer is required"):
        save_review(decisions, "org/a", "healthy", "recent activity", "")

    with pytest.raises(ValueError, match="notes are required"):
        save_review(decisions, "org/a", "healthy", "", "reviewer-a")


def test_save_review_preserves_independent_reviewer_decisions(tmp_path):
    decisions = tmp_path / "decisions.csv"

    save_review(
        decisions,
        "org/a",
        "watch",
        "mixed maintenance evidence",
        "reviewer-a",
        reviewed_at_utc="2026-09-05T10:00:00+00:00",
    )
    save_review(
        decisions,
        "org/a",
        "risky",
        "strong abandonment evidence",
        "reviewer-b",
        reviewed_at_utc="2026-09-05T11:00:00+00:00",
    )

    rows = list(csv.DictReader(decisions.open(encoding="utf-8")))
    assert len(rows) == 2
    assert {row["reviewer"] for row in rows} == {"reviewer-a", "reviewer-b"}

    with pytest.raises(ValueError, match="already has a decision"):
        save_review(decisions, "org/a", "healthy", "changed mind", "reviewer-a")

    save_review(
        decisions,
        "org/a",
        "healthy",
        "deliberate correction after re-checking evidence",
        "reviewer-a",
        reviewed_at_utc="2026-09-05T12:00:00+00:00",
        replace=True,
    )
    rows = list(csv.DictReader(decisions.open(encoding="utf-8")))
    corrected = next(row for row in rows if row["reviewer"] == "reviewer-a")
    assert corrected["human_label"] == "healthy"
    assert len(rows) == 2
