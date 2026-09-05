from __future__ import annotations

import json

from scripts.generate_model_card import build_model_card


def test_model_card_uses_committed_artifact_values(tmp_path):
    progress = tmp_path / "progress.json"
    quality = tmp_path / "quality.json"
    metrics = tmp_path / "metrics.json"
    progress.write_text(json.dumps({
        "catalog_target": 100000,
        "catalog_repositories": 5000,
        "deep_profile_target": 10000,
        "deep_snapshots": 100,
        "labelled_snapshots": 72,
        "human_review_queue": 28,
    }), encoding="utf-8")
    quality.write_text(json.dumps({
        "training": {
            "labels": {"healthy": 50, "watch": 12, "risky": 10},
            "label_sources": {"recent_release_evidence": 50, "stale_release_evidence": 12, "github_archived_flag": 10},
        },
        "warnings": ["at least one label class has fewer than 20 examples"],
    }), encoding="utf-8")
    metrics.write_text(json.dumps({
        "model_type": "RandomForestClassifier",
        "source_csv": "data/train.csv",
        "dataset_sha256": "abc123",
        "trained_at_utc": "2026-09-05T00:00:00+00:00",
        "scikit_learn_version": "1.9.0",
        "repositories": 72,
        "train_repositories": 54,
        "test_repositories": 18,
        "cross_validation": {
            "strategy": "stratified_group_k_fold",
            "folds": 5,
            "labels": ["healthy", "watch", "risky"],
            "accuracy": 0.8,
            "balanced_accuracy": 0.71,
            "macro_f1": 0.74,
            "confusion_matrix": [[45, 3, 2], [2, 8, 2], [1, 2, 7]],
        },
        "heldout": {
            "labels": ["healthy", "watch", "risky"],
            "accuracy": 0.78,
            "balanced_accuracy": 0.68,
            "macro_f1": 0.66,
            "confusion_matrix": [[12, 1, 0], [1, 2, 1], [0, 1, 2]],
        },
        "evaluation_warning": "experimental data warning",
    }), encoding="utf-8")

    card = build_model_card(progress, quality, metrics)
    assert "Catalog repositories collected: 5000" in card
    assert "Deep snapshots collected: 100" in card
    assert "`healthy`: 50" in card
    assert "Cross-validation macro F1: 0.74" in card
    assert "Cross-validation balanced accuracy: 0.71" in card
    assert "Holdout balanced accuracy: 0.68" in card
    assert "| healthy | 45 | 3 | 2 |" in card
    assert "`abc123`" in card
    assert "experimental data warning" in card
    assert "experimental weak supervision" in card
