from __future__ import annotations

import csv
import hashlib

import joblib

from repo_scope.ml.training import FEATURE_COLUMNS, train_from_csv


def _write_training_csv(path):
    rows = []
    labels = ["healthy", "watch", "risky"]
    for repo_index in range(12):
        label = labels[repo_index % len(labels)]
        for snapshot in range(2):
            rows.append(
                {
                    "repo": f"org/repo-{repo_index}",
                    "days_since_last_commit": repo_index + snapshot,
                    "bus_factor": 1 + (repo_index % 4),
                    "issue_closure_rate_pct": 40 + repo_index * 3,
                    "pr_merge_rate_pct": 35 + repo_index * 4,
                    "commits_90d": 5 + repo_index * 2,
                    "contributors_sampled": 2 + repo_index,
                    "has_ci": int(repo_index % 2 == 0),
                    "has_tests": int(repo_index % 3 != 0),
                    "label": label,
                }
            )

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo", *FEATURE_COLUMNS, "label"])
        writer.writeheader()
        writer.writerows(rows)


def test_training_uses_repository_level_split_and_saves_metadata(tmp_path):
    csv_path = tmp_path / "training.csv"
    model_path = tmp_path / "model.joblib"
    _write_training_csv(csv_path)
    expected_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    result = train_from_csv(str(csv_path), str(model_path))

    assert result["repositories"] == 12
    assert result["train_repositories"] + result["test_repositories"] == 12
    assert set(result["feature_importance"]) == set(FEATURE_COLUMNS)
    assert result["dataset_sha256"] == expected_hash
    assert result["trained_at_utc"]
    assert result["model_type"] == "RandomForestClassifier"
    assert result["scikit_learn_version"]
    assert model_path.exists()

    artifact = joblib.load(model_path)
    metadata = artifact["training_metadata"]
    assert artifact["features"] == FEATURE_COLUMNS
    assert metadata["split_strategy"] == "group_shuffle_by_repository"
    assert metadata["dataset_sha256"] == expected_hash
    assert metadata["trained_at_utc"]
    assert metadata["model_type"] == "RandomForestClassifier"


def test_training_rejects_blank_labels(tmp_path):
    csv_path = tmp_path / "training.csv"
    _write_training_csv(csv_path)

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[0]["label"] = ""
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo", *FEATURE_COLUMNS, "label"])
        writer.writeheader()
        writer.writerows(rows)

    try:
        train_from_csv(str(csv_path), str(tmp_path / "model.joblib"))
    except ValueError as exc:
        assert "non-empty evidence-backed or human-reviewed label" in str(exc)
    else:
        raise AssertionError("Expected blank labels to be rejected")


def test_training_rejects_dataset_missing_a_risk_class(tmp_path):
    csv_path = tmp_path / "training.csv"
    _write_training_csv(csv_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    for row in rows:
        if row["label"] == "risky":
            row["label"] = "healthy"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo", *FEATURE_COLUMNS, "label"])
        writer.writeheader()
        writer.writerows(rows)

    try:
        train_from_csv(str(csv_path), str(tmp_path / "model.joblib"))
    except ValueError as exc:
        assert "missing classes: risky" in str(exc)
    else:
        raise AssertionError("Expected incomplete risk-class data to be rejected")
