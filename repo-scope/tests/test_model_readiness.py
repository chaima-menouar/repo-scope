from __future__ import annotations

from scripts.evaluate_model_readiness import evaluate


def test_readiness_blocks_without_human_validation():
    progress = {"deep_snapshots": 1500}
    quality = {"warnings": []}
    metrics = {
        "class_counts": {"healthy": 100, "watch": 80, "risky": 70},
        "cross_validation": {"macro_f1": 0.8, "balanced_accuracy": 0.79},
        "temporal_holdout": {"available": True, "macro_f1": 0.72, "missing_test_classes": []},
        "calibration": {"status": "analysis_only_uncalibrated", "expected_calibration_error_10_bin": 0.08},
    }
    human = {"status": "insufficient_human_review"}
    report = evaluate(progress, quality, metrics, human)
    assert report["eligible"] is False
    assert any("human-reviewed validation subset" in reason for reason in report["blocking_reasons"])


def test_readiness_allows_manual_review_when_all_gates_pass():
    progress = {"deep_snapshots": 1500}
    quality = {"warnings": []}
    metrics = {
        "class_counts": {"healthy": 100, "watch": 80, "risky": 70},
        "cross_validation": {"macro_f1": 0.8, "balanced_accuracy": 0.79},
        "temporal_holdout": {"available": True, "macro_f1": 0.72, "missing_test_classes": []},
        "calibration": {"status": "analysis_only_uncalibrated", "expected_calibration_error_10_bin": 0.08},
    }
    human = {"status": "ready_for_comparison", "agreement_rate": 0.82}
    report = evaluate(progress, quality, metrics, human)
    assert report["eligible"] is True
    assert report["promotion_status"] == "eligible_for_manual_review"
    assert report["blocking_reasons"] == []
