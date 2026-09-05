from __future__ import annotations

import csv
from pathlib import Path

from scripts.report_dataset_quality import build_report


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_quality_report_counts_catalog_and_training(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.csv"
    training = tmp_path / "training.csv"
    _write_csv(
        catalog,
        ["repo", "language", "license", "archived", "created_at", "updated_at", "pushed_at", "default_branch"],
        [
            {"repo": "a/one", "language": "Python", "license": "MIT", "archived": 0, "created_at": "x", "updated_at": "x", "pushed_at": "x", "default_branch": "main"},
            {"repo": "b/two", "language": "Go", "license": "Apache-2.0", "archived": 1, "created_at": "x", "updated_at": "x", "pushed_at": "x", "default_branch": "main"},
        ],
    )
    feature_values = {
        "days_since_last_commit": 5,
        "bus_factor": 2,
        "issue_closure_rate_pct": 80,
        "pr_merge_rate_pct": 75,
        "commits_90d": 30,
        "contributors_sampled": 10,
        "has_ci": 1,
        "has_tests": 1,
    }
    fields = ["repo", *feature_values, "label", "label_source"]
    rows = []
    for index, label in enumerate(["healthy", "risky", "watch"]):
        rows.append({"repo": f"org/repo{index}", **feature_values, "label": label, "label_source": "test_evidence"})
    _write_csv(training, fields, rows)

    report = build_report(catalog, training)
    assert report["catalog"]["rows"] == 2
    assert report["catalog"]["active"] == 1
    assert report["catalog"]["archived"] == 1
    assert report["training"]["rows"] == 3
    assert report["training"]["unique_repositories"] == 3
    assert report["training"]["labels"] == {"healthy": 1, "risky": 1, "watch": 1}
    assert report["training"]["feature_missingness"]["has_ci"]["missing"] == 0


def test_quality_report_flags_imbalance_and_small_classes(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.csv"
    training = tmp_path / "training.csv"
    _write_csv(catalog, ["repo", "archived"], [{"repo": f"org/r{i}", "archived": 0} for i in range(10)])
    fields = [
        "repo", "days_since_last_commit", "bus_factor", "issue_closure_rate_pct",
        "pr_merge_rate_pct", "commits_90d", "contributors_sampled", "has_ci", "has_tests",
        "label", "label_source",
    ]
    rows = []
    for index in range(10):
        rows.append({
            "repo": f"org/r{index}", "days_since_last_commit": 1, "bus_factor": 1,
            "issue_closure_rate_pct": 90, "pr_merge_rate_pct": 90, "commits_90d": 20,
            "contributors_sampled": 4, "has_ci": 1, "has_tests": 1,
            "label": "healthy" if index < 9 else "risky", "label_source": "test",
        })
    _write_csv(training, fields, rows)

    report = build_report(catalog, training)
    assert report["status"] == "needs_review"
    assert any("fewer than 20" in warning for warning in report["warnings"])
    assert any("highly imbalanced" in warning for warning in report["warnings"])
    assert any("archived repositories are under-represented" in warning for warning in report["warnings"])
