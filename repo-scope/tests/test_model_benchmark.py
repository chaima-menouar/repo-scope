from __future__ import annotations

import csv

from repo_scope.ml.training import FEATURE_COLUMNS
from scripts.benchmark_risk_models import benchmark


def test_benchmark_compares_interpretable_and_tree_baselines(tmp_path):
    path = tmp_path / "training.csv"
    rows = []
    labels = ["healthy", "watch", "risky"]
    for index in range(18):
        label = labels[index % 3]
        rows.append(
            {
                "repo": f"org/repo-{index}",
                "days_since_last_commit": index * 3,
                "bus_factor": 1 + index % 4,
                "issue_closure_rate_pct": 30 + index * 2,
                "pr_merge_rate_pct": 35 + index * 2,
                "commits_90d": 3 + index,
                "contributors_sampled": 2 + index % 7,
                "has_ci": index % 2,
                "has_tests": int(index % 3 != 0),
                "label": label,
            }
        )

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo", *FEATURE_COLUMNS, "label"])
        writer.writeheader()
        writer.writerows(rows)

    report = benchmark(path)

    assert report["repositories"] == 18
    assert set(report["models"]) == {"logistic_regression", "random_forest"}
    assert report["best_experimental_baseline"] in report["models"]
    for result in report["models"].values():
        assert 0 <= result["macro_f1"] <= 1
        assert 0 <= result["balanced_accuracy"] <= 1
