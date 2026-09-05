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


def test_pending_reviews_excludes_already_reviewed_repositories():
    queue = [{"repo": "org/a"}, {"repo": "org/b"}]
    registry = [{"repo": "org/a", "human_label": "healthy"}]

    pending = pending_reviews(queue, registry)

    assert [row["repo"] for row in pending] == ["org/b"]


def test_save_review_requires_provenance_and_notes(tmp_path):
    registry = tmp_path / "human.csv"

    with pytest.raises(ValueError, match="Reviewer is required"):
        save_review(registry, "org/a", "healthy", "recent activity", "")

    with pytest.raises(ValueError, match="notes are required"):
        save_review(registry, "org/a", "healthy", "", "reviewer-a")


def test_save_review_writes_durable_registry_and_blocks_accidental_overwrite(tmp_path):
    registry = tmp_path / "human.csv"

    save_review(
        registry,
        "org/a",
        "watch",
        "mixed maintenance evidence",
        "reviewer-a",
        reviewed_at_utc="2026-09-05T10:00:00+00:00",
    )

    rows = list(csv.DictReader(registry.open(encoding="utf-8")))
    assert rows == [
        {
            "repo": "org/a",
            "human_label": "watch",
            "review_notes": "mixed maintenance evidence",
            "reviewer": "reviewer-a",
            "reviewed_at_utc": "2026-09-05T10:00:00+00:00",
        }
    ]

    with pytest.raises(ValueError, match="already has a durable human review"):
        save_review(registry, "org/a", "risky", "changed mind", "reviewer-a")

    save_review(
        registry,
        "org/a",
        "risky",
        "adjudicated with stronger abandonment evidence",
        "reviewer-b",
        reviewed_at_utc="2026-09-05T11:00:00+00:00",
        replace=True,
    )
    rows = list(csv.DictReader(registry.open(encoding="utf-8")))
    assert rows[0]["human_label"] == "risky"
    assert rows[0]["reviewer"] == "reviewer-b"
