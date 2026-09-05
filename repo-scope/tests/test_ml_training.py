from __future__ import annotations

import csv
import hashlib

import joblib

from repo_scope.ml.training import FEATURE_COLUMNS, FEATURE_SCHEMA_VERSION, LABEL_ORDER, train_from_csv


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


def _write_temporal_training_csv(path):
    rows = []
    labels = ["healthy", "watch", "risky"]
    for repo_index in range(24):
        rows.append(
            {
                "repo": f"org/temporal-{repo_index:02d}",
                "days_since_last_commit": repo_index,
                "bus_factor": 1 + (repo_index % 5),
                "issue_closure_rate_pct": 30 + repo_index,
                "pr_merge_rate_pct": 25 + repo_index,
                "commits_90d": 3 + repo_index,
                "contributors_sampled": 2 + (repo_index % 8),
                "has_ci": int(repo_index % 2 == 0),
                "has_tests": int(repo_index % 3 != 0),
                "snapshot_at_utc": f"2026-08-{repo_index + 1:02d}T12:00:00+00:00",
                "label": labels[repo_index % 3],
            }
        )

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["repo", *FEATURE_COLUMNS, "snapshot_at_utc", "label"],
        )
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
    assert result["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert result["artifact_fit_strategy"] == "refit_on_all_rows_after_isolated_evaluation"
    assert result["cross_validation"]["labels"] == LABEL_ORDER
    assert 0 <= result["cross_validation"]["balanced_accuracy"] <= 1
    assert len(result["cross_validation"]["confusion_matrix"]) == 3
    assert result["heldout"]["labels"] == LABEL_ORDER
    assert 0 <= result["heldout"]["balanced_accuracy"] <= 1
    assert len(result["heldout"]["confusion_matrix"]) == 3
    assert result["temporal_holdout"]["available"] is False
    assert model_path.exists()

    artifact = joblib.load(model_path)
    metadata = artifact["training_metadata"]
    assert artifact["features"] == FEATURE_COLUMNS
    assert artifact["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert metadata["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert metadata["artifact_fit_strategy"] == "refit_on_all_rows_after_isolated_evaluation"
    assert metadata["split_strategy"] == "group_shuffle_by_repository"
    assert metadata["dataset_sha256"] == expected_hash
    assert metadata["trained_at_utc"]
    assert metadata["model_type"] == "RandomForestClassifier"


def test_training_reports_temporal_holdout_for_timestamped_repositories(tmp_path):
    csv_path = tmp_path / "temporal.csv"
    model_path = tmp_path / "temporal.joblib"
    _write_temporal_training_csv(csv_path)

    result = train_from_csv(str(csv_path), str(model_path))

    temporal = result["temporal_holdout"]
    assert temporal["available"] is True
    assert temporal["strategy"] == "newest_25pct_repositories_by_snapshot_time"
    assert temporal["train_repositories"] == 18
    assert temporal["test_repositories"] == 6
    assert temporal["train_rows"] == 18
    assert temporal["test_rows"] == 6
    assert temporal["cutoff_utc"].startswith("2026-08-19")
    assert temporal["missing_test_classes"] == []
    assert 0 <= temporal["balanced_accuracy"] <= 1
    assert len(temporal["confusion_matrix"]) == 3

    artifact = joblib.load(model_path)
    assert artifact["training_metadata"]["temporal_holdout_available"] is True
    assert artifact["training_metadata"]["artifact_fit_strategy"] == "refit_on_all_rows_after_isolated_evaluation"


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
