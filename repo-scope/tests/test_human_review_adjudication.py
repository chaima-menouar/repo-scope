from __future__ import annotations

import csv
import json

import pytest

from scripts.adjudicate_human_reviews import adjudicate, load_decisions, write_report


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
    assert report["status"] == "partial_adjudication"
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
    assert report["status"] == "partial_adjudication"
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

    assert report["status"] == "fully_adjudicated"
    assert report["adjudicated_repositories"] == 1
    assert labels[0]["repo"] == "org/a"
    assert labels[0]["human_label"] == "watch"
    assert labels[0]["reviewer"] == "adjudicated:reviewer-a+reviewer-b+reviewer-c"
    assert "reviewer-a:" in labels[0]["review_notes"]
    assert "reviewer-b:" in labels[0]["review_notes"]


def test_empty_decision_set_has_explicit_status():
    labels, report = adjudicate([])

    assert labels == []
    assert report["status"] == "no_human_decisions"


def test_load_decisions_rejects_missing_evidence_notes(tmp_path):
    path = tmp_path / "decisions.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "repo": "org/a",
                "human_label": "healthy",
                "review_notes": "",
                "reviewer": "reviewer-a",
                "reviewed_at_utc": "2026-09-05T12:00:00+00:00",
            }
        )

    with pytest.raises(ValueError, match="Missing evidence notes"):
        load_decisions(path)


def test_load_decisions_rejects_missing_timestamp(tmp_path):
    path = tmp_path / "decisions.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "repo": "org/a",
                "human_label": "healthy",
                "review_notes": "direct maintenance evidence",
                "reviewer": "reviewer-a",
                "reviewed_at_utc": "",
            }
        )

    with pytest.raises(ValueError, match="Missing review timestamp"):
        load_decisions(path)


def test_write_report_persists_machine_readable_audit(tmp_path):
    path = tmp_path / "adjudication.json"
    report = {"status": "partial_adjudication", "adjudicated_repositories": 3}

    write_report(path, report)

    assert json.loads(path.read_text(encoding="utf-8")) == report
