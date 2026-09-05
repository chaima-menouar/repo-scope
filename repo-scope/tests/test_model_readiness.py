from __future__ import annotations

from scripts.evaluate_model_readiness import evaluate


def _good_metrics():
    return {
        "class_counts": {"healthy": 100, "watch": 80, "risky": 70},
        "cross_validation": {"macro_f1": 0.8, "balanced_accuracy": 0.79},
        "temporal_holdout": {
            "available": True,
            "macro_f1": 0.72,
            "missing_test_classes": [],
            "test_class_counts": {"healthy": 30, "watch": 12, "risky": 15},
        },
        "calibration": {"status": "analysis_only_uncalibrated", "expected_calibration_error_10_bin": 0.08},
        "failure_slices": {
            "dimensions": {
                "language": [{"slice": "Python", "count": 100, "accuracy": 0.75}],
                "repository_size": [{"slice": "small_1mb_10mb", "count": 80, "accuracy": 0.72}],
                "maintenance_style": [{"slice": "recent_active", "count": 120, "accuracy": 0.76}],
            }
        },
    }


def _good_reviewer_audit():
    return {
        "status": "ready_for_inter_reviewer_analysis",
        "repositories_with_multiple_reviewers": 75,
        "duplicate_reviewer_repo_decisions": [],
        "invalid_labels": [],
    }


def test_readiness_blocks_without_human_validation():
    progress = {"deep_snapshots": 1500}
    quality = {"warnings": []}
    human = {"status": "insufficient_human_review"}
    report = evaluate(progress, quality, _good_metrics(), human, _good_reviewer_audit())
    assert report["eligible"] is False
    assert any("human-reviewed validation subset" in reason for reason in report["blocking_reasons"])


def test_readiness_allows_manual_review_when_all_gates_pass():
    progress = {"deep_snapshots": 1500}
    quality = {"warnings": []}
    human = {"status": "ready_for_comparison", "agreement_rate": 0.82}
    report = evaluate(progress, quality, _good_metrics(), human, _good_reviewer_audit())
    assert report["eligible"] is True
    assert report["promotion_status"] == "eligible_for_manual_review"
    assert report["blocking_reasons"] == []


def test_readiness_blocks_large_weak_failure_slice():
    metrics = _good_metrics()
    metrics["failure_slices"]["dimensions"]["language"][0]["accuracy"] = 0.40
    report = evaluate(
        {"deep_snapshots": 1500},
        {"warnings": []},
        metrics,
        {"status": "ready_for_comparison", "agreement_rate": 0.82},
        _good_reviewer_audit(),
    )
    assert report["eligible"] is False
    assert any("failure slice language/Python" in reason for reason in report["blocking_reasons"])


def test_readiness_requires_meaningful_temporal_support_per_class():
    metrics = _good_metrics()
    metrics["temporal_holdout"]["macro_f1"] = 0.2
    metrics["temporal_holdout"]["test_class_counts"]["watch"] = 3
    report = evaluate(
        {"deep_snapshots": 1500},
        {"warnings": []},
        metrics,
        {"status": "ready_for_comparison", "agreement_rate": 0.82},
        _good_reviewer_audit(),
    )
    assert report["eligible"] is False
    assert any("temporal holdout has insufficient per-class test support" in reason for reason in report["blocking_reasons"])
    assert not any("temporal holdout macro F1 is below" in reason for reason in report["blocking_reasons"])


def test_readiness_blocks_invalid_human_review_audit():
    audit = _good_reviewer_audit()
    audit["duplicate_reviewer_repo_decisions"] = ["org/repo:reviewer-a"]
    report = evaluate(
        {"deep_snapshots": 1500},
        {"warnings": []},
        _good_metrics(),
        {"status": "ready_for_comparison", "agreement_rate": 0.82},
        audit,
    )
    assert report["eligible"] is False
    assert any("duplicate reviewer/repository decisions" in reason for reason in report["blocking_reasons"])


def test_readiness_requires_multi_reviewer_overlap_when_human_subset_is_ready():
    audit = _good_reviewer_audit()
    audit["repositories_with_multiple_reviewers"] = 59
    report = evaluate(
        {"deep_snapshots": 1500},
        {"warnings": []},
        _good_metrics(),
        {"status": "ready_for_comparison", "agreement_rate": 0.82},
        audit,
    )
    assert report["eligible"] is False
    assert any("fewer than 60 repositories have multiple independent reviewers" in reason for reason in report["blocking_reasons"])
