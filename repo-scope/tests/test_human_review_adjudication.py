from __future__ import annotations

from scripts.adjudicate_human_reviews import adjudicate


def _decision(repo: str, label: str, reviewer: str) -> dict[str, str]:
    return {
        "repo": repo,
        "human_label": label,
        "review_notes": f"evidence from {reviewer}",
        "reviewer": reviewer,
        "reviewed_at_utc": "2026-09-05T12:00:00+00:00",
    }


def test_adjudication_requires_multiple_reviewers():
    labels, report = adjudicate([_decision("org/a", "healthy", "reviewer-a")])

    assert labels == []
    assert report["insufficient_reviewer_repositories"] == 1
    assert report["adjudicated_repositories"] == 0


def test_adjudication_does_not_resolve_two_reviewer_disagreement():
    labels, report = adjudicate(
        [
            _decision("org/a", "healthy", "reviewer-a"),
            _decision("org/a", "risky", "reviewer-b"),
        ]
    )

    assert labels == []
    assert report["disagreement_repositories"] == 1
    assert report["disagreements"][0]["reason"] == "no_unique_majority"


def test_adjudication_emits_strict_majority_and_preserves_provenance():
    labels, report = adjudicate(
        [
            _decision("org/a", "watch", "reviewer-a"),
            _decision("org/a", "watch", "reviewer-b"),
            _decision("org/a", "risky", "reviewer-c"),
        ]
    )

    assert report["adjudicated_repositories"] == 1
    assert labels[0]["repo"] == "org/a"
    assert labels[0]["human_label"] == "watch"
    assert labels[0]["reviewer"] == "adjudicated:reviewer-a+reviewer-b+reviewer-c"
    assert "reviewer-a:" in labels[0]["review_notes"]
    assert "reviewer-b:" in labels[0]["review_notes"]
