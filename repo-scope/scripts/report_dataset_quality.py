from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

FEATURES = [
    "days_since_last_commit",
    "bus_factor",
    "issue_closure_rate_pct",
    "pr_merge_rate_pct",
    "commits_90d",
    "contributors_sampled",
    "has_ci",
    "has_tests",
]


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _counter(rows: list[dict[str, str]], column: str) -> dict[str, int]:
    values = Counter((row.get(column) or "unknown").strip() or "unknown" for row in rows)
    return dict(sorted(values.items(), key=lambda item: (-item[1], item[0])))


def _missingness(rows: list[dict[str, str]], columns: list[str]) -> dict[str, dict[str, float | int]]:
    total = len(rows)
    result: dict[str, dict[str, float | int]] = {}
    for column in columns:
        missing = sum(1 for row in rows if not (row.get(column) or "").strip())
        result[column] = {
            "missing": missing,
            "missing_pct": round((missing / total * 100) if total else 0.0, 3),
        }
    return result


def build_report(catalog_path: Path, training_path: Path) -> dict:
    catalog = _rows(catalog_path)
    training = _rows(training_path)
    unique_training_repos = {row.get("repo", "").strip() for row in training if row.get("repo", "").strip()}
    labels = _counter(training, "label")
    label_total = sum(labels.values())
    label_balance = {
        label: round(count / label_total, 4) if label_total else 0.0
        for label, count in labels.items()
    }

    archived_count = sum(1 for row in catalog if (row.get("archived") or "").strip() in {"1", "true", "True"})
    active_count = max(0, len(catalog) - archived_count)

    warnings: list[str] = []
    if training and len(unique_training_repos) != len(training):
        warnings.append("training data contains multiple snapshots for at least one repository; grouped evaluation is required")
    if label_total and min(labels.values()) < 20:
        warnings.append("at least one label class has fewer than 20 examples")
    if label_total and max(label_balance.values()) > 0.80:
        warnings.append("label distribution is highly imbalanced")
    if catalog and archived_count / len(catalog) < 0.10:
        warnings.append("archived repositories are under-represented in the catalog")

    return {
        "catalog": {
            "rows": len(catalog),
            "active": active_count,
            "archived": archived_count,
            "languages": _counter(catalog, "language"),
            "licenses": _counter(catalog, "license"),
            "missingness": _missingness(
                catalog,
                ["repo", "language", "created_at", "updated_at", "pushed_at", "default_branch", "license"],
            ),
        },
        "training": {
            "rows": len(training),
            "unique_repositories": len(unique_training_repos),
            "labels": labels,
            "label_balance": label_balance,
            "label_sources": _counter(training, "label_source"),
            "feature_missingness": _missingness(training, FEATURES),
        },
        "warnings": warnings,
        "status": "needs_review" if warnings else "healthy",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a quality report for RepoScope ML datasets.")
    parser.add_argument("--catalog", default="data/repository_catalog_100k.csv")
    parser.add_argument("--training", default="data/repo_risk_training_100k.csv")
    parser.add_argument("--output", default="data/repo_risk_100k_quality.json")
    args = parser.parse_args()

    report = build_report(Path(args.catalog), Path(args.training))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
