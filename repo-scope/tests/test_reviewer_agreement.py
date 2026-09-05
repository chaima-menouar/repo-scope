from __future__ import annotations

import csv

from scripts.report_reviewer_agreement import _cohen_kappa, build_report


def _write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_cohen_kappa_perfect_agreement():
    assert _cohen_kappa(["healthy", "watch", "risky"], ["healthy", "watch", "risky"]) == 1.0


def test_reviewer_report_tracks_overlap_disagreement_and_kappa(tmp_path):
    decisions = tmp_path / "decisions.csv"
    _write(
        decisions,
        [
            {"repo": "org/a", "human_label": "healthy", "review_notes": "a", "reviewer": "r1", "reviewed_at_utc": "t1"},
            {"repo": "org/b", "human_label": "watch", "review_notes": "b", "reviewer": "r1", "reviewed_at_utc": "t2"},
            {"repo": "org/c", "human_label": "risky", "review_notes": "c", "reviewer": "r1", "reviewed_at_utc": "t3"},
            {"repo": "org/a", "human_label": "healthy", "review_notes": "a", "reviewer": "r2", "reviewed_at_utc": "t4"},
            {"repo": "org/b", "human_label": "risky", "review_notes": "b", "reviewer": "r2", "reviewed_at_utc": "t5"},
            {"repo": "org/c", "human_label": "risky", "review_notes": "c", "reviewer": "r2", "reviewed_at_utc": "t6"},
        ],
    )

    report = build_report(decisions)

    assert report["reviewers"] == 2
    assert report["repositories_with_multiple_reviewers"] == 3
    assert report["repositories_with_disagreement"] == 1
    pair = report["pairwise_reviewer_agreement"][0]
    assert pair["shared_repositories"] == 3
    assert pair["agreement_count"] == 2
    assert pair["raw_agreement"] == 0.666667
    assert pair["cohen_kappa"] is not None
    assert report["status"] == "ready_for_inter_reviewer_analysis"


def test_reviewer_report_is_not_ready_without_overlap(tmp_path):
    decisions = tmp_path / "decisions.csv"
    _write(
        decisions,
        [
            {"repo": "org/a", "human_label": "healthy", "review_notes": "a", "reviewer": "r1", "reviewed_at_utc": "t1"},
            {"repo": "org/b", "human_label": "watch", "review_notes": "b", "reviewer": "r2", "reviewed_at_utc": "t2"},
        ],
    )

    report = build_report(decisions)

    assert report["repositories_with_multiple_reviewers"] == 0
    assert report["status"] == "insufficient_overlap"
