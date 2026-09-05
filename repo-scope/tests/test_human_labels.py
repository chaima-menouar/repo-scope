from __future__ import annotations

import csv

from scripts.merge_human_labels import merge_labels
from repo_scope.ml.training import FEATURE_COLUMNS


def _snapshot(repo: str) -> dict[str, object]:
    return {
        "repo": repo,
        "days_since_last_commit": 10,
        "bus_factor": 2,
        "issue_closure_rate_pct": 80,
        "pr_merge_rate_pct": 70,
        "commits_90d": 12,
        "contributors_sampled": 4,
        "has_ci": 1,
        "has_tests": 1,
        "snapshot_at_utc": "2026-09-05T00:00:00+00:00",
        "archived": 0,
        "latest_release_age_days": 165,
        "latest_release_at": "2026-03-24T00:00:00Z",
        "label": "",
    }


def _write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_human_labels_add_ambiguous_repo_and_override_weak_label(tmp_path):
    unlabelled = tmp_path / "unlabelled.csv"
    weak = tmp_path / "weak.csv"
    human = tmp_path / "human.csv"
    output = tmp_path / "combined.csv"

    source_rows = [_snapshot("org/ambiguous"), _snapshot("org/weak")]
    source_rows[1]["latest_release_age_days"] = 30
    _write_csv(
        unlabelled,
        source_rows,
        ["repo", *FEATURE_COLUMNS, "snapshot_at_utc", "archived", "latest_release_age_days", "latest_release_at", "label"],
    )

    weak_row = dict(source_rows[1])
    weak_row["label"] = "healthy"
    weak_row["label_source"] = "recent_release_evidence"
    weak_row["label_evidence"] = "latest release age=30 days"
    _write_csv(
        weak,
        [weak_row],
        ["repo", *FEATURE_COLUMNS, "snapshot_at_utc", "archived", "latest_release_age_days", "latest_release_at", "label", "label_source", "label_evidence"],
    )

    _write_csv(
        human,
        [
            {
                "repo": "org/ambiguous",
                "human_label": "watch",
                "review_notes": "maintenance looks intermittent",
                "reviewer": "reviewer-a",
                "reviewed_at_utc": "2026-09-05T10:00:00Z",
            },
            {
                "repo": "org/weak",
                "human_label": "risky",
                "review_notes": "manual review contradicts weak label",
                "reviewer": "reviewer-a",
                "reviewed_at_utc": "2026-09-05T10:05:00Z",
            },
        ],
        ["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"],
    )

    result = merge_labels(unlabelled, weak, human, output)
    rows = {row["repo"]: row for row in csv.DictReader(output.open(encoding="utf-8"))}

    assert result["human_added"] == 1
    assert result["weak_labels_overridden"] == 1
    assert rows["org/ambiguous"]["label"] == "watch"
    assert rows["org/ambiguous"]["label_source"] == "human_review"
    assert rows["org/weak"]["label"] == "risky"
    assert rows["org/weak"]["label_source"] == "human_review"


def test_human_labels_reject_unknown_label(tmp_path):
    unlabelled = tmp_path / "unlabelled.csv"
    weak = tmp_path / "weak.csv"
    human = tmp_path / "human.csv"
    output = tmp_path / "combined.csv"

    row = _snapshot("org/a")
    _write_csv(
        unlabelled,
        [row],
        ["repo", *FEATURE_COLUMNS, "snapshot_at_utc", "archived", "latest_release_age_days", "latest_release_at", "label"],
    )
    _write_csv(
        weak,
        [],
        ["repo", *FEATURE_COLUMNS, "snapshot_at_utc", "archived", "latest_release_age_days", "latest_release_at", "label", "label_source", "label_evidence"],
    )
    _write_csv(
        human,
        [{"repo": "org/a", "human_label": "maybe", "review_notes": "", "reviewer": "", "reviewed_at_utc": ""}],
        ["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"],
    )

    try:
        merge_labels(unlabelled, weak, human, output)
    except ValueError as exc:
        assert "must be one of" in str(exc)
    else:
        raise AssertionError("Expected invalid human label to be rejected")
