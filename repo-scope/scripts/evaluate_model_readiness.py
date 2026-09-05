from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.exists() or not path.stat().st_size:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _number(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate(progress: dict, quality: dict, metrics: dict, human_comparison: dict) -> dict:
    reasons: list[str] = []
    class_counts = metrics.get("class_counts", {})
    cv = metrics.get("cross_validation", {})
    temporal = metrics.get("temporal_holdout", {})
    calibration = metrics.get("calibration", {})
    failure_dimensions = (metrics.get("failure_slices", {}) or {}).get("dimensions", {}) or {}

    deep_snapshots = int(progress.get("deep_snapshots", 0) or 0)
    if deep_snapshots < 1000:
        reasons.append("fewer than 1000 deep repository snapshots collected")

    for label in ("healthy", "watch", "risky"):
        if int(class_counts.get(label, 0) or 0) < 50:
            reasons.append(f"class {label} has fewer than 50 labelled repositories")

    if _number(cv.get("macro_f1")) < 0.65:
        reasons.append("grouped cross-validation macro F1 is below 0.65")
    if _number(cv.get("balanced_accuracy")) < 0.65:
        reasons.append("grouped cross-validation balanced accuracy is below 0.65")

    if not temporal.get("available"):
        reasons.append("temporal holdout is not available")
    else:
        if _number(temporal.get("macro_f1")) < 0.60:
            reasons.append("temporal holdout macro F1 is below 0.60")
        if temporal.get("missing_test_classes"):
            reasons.append("temporal holdout does not contain all three risk classes")

    if calibration.get("status") != "analysis_only_uncalibrated":
        reasons.append("out-of-fold calibration diagnostics are missing")
    if _number(calibration.get("expected_calibration_error_10_bin"), 1.0) > 0.15:
        reasons.append("expected calibration error is above 0.15")

    required_slice_dimensions = {"language", "repository_size", "maintenance_style"}
    missing_slice_dimensions = sorted(required_slice_dimensions - set(failure_dimensions))
    if missing_slice_dimensions:
        reasons.append("failure-slice diagnostics are incomplete: " + ", ".join(missing_slice_dimensions))
    else:
        for dimension in sorted(required_slice_dimensions):
            for slice_row in failure_dimensions.get(dimension, []):
                count = int(slice_row.get("count", 0) or 0)
                accuracy = _number(slice_row.get("accuracy"), 1.0)
                if count >= 20 and accuracy < 0.50:
                    reasons.append(
                        f"failure slice {dimension}/{slice_row.get('slice')} has accuracy below 0.50 with n={count}"
                    )

    if human_comparison.get("status") != "ready_for_comparison":
        reasons.append("human-reviewed validation subset is still too small")
    elif _number(human_comparison.get("agreement_rate")) < 0.70:
        reasons.append("weak-label agreement with human review is below 0.70")

    warnings = quality.get("warnings") or []
    if warnings:
        reasons.append("dataset quality report still contains warnings")

    eligible = not reasons
    return {
        "promotion_status": "eligible_for_manual_review" if eligible else "blocked",
        "eligible": eligible,
        "blocking_reasons": reasons,
        "policy": {
            "deep_snapshots_min": 1000,
            "each_class_min": 50,
            "cv_macro_f1_min": 0.65,
            "cv_balanced_accuracy_min": 0.65,
            "temporal_macro_f1_min": 0.60,
            "ece_max": 0.15,
            "required_failure_slice_dimensions": sorted(required_slice_dimensions),
            "large_slice_accuracy_min": 0.50,
            "large_slice_min_n": 20,
            "human_overlap_min": 60,
            "human_each_class_min": 10,
            "weak_human_agreement_min": 0.70,
        },
        "note": (
            "Eligible means the automated evidence is strong enough for a manual promotion decision. "
            "It never automatically converts the experimental model into a production risk score."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RepoScope scaled-model promotion readiness.")
    parser.add_argument("--progress", default="data/repo_risk_100k_progress.json")
    parser.add_argument("--quality", default="data/repo_risk_100k_quality.json")
    parser.add_argument("--metrics", default="models/repo_risk_100k_metrics.json")
    parser.add_argument("--human-comparison", default="data/repo_risk_human_weak_comparison.json")
    parser.add_argument("--output", default="models/repo_risk_100k_readiness.json")
    args = parser.parse_args()
    report = evaluate(
        _load(Path(args.progress)),
        _load(Path(args.quality)),
        _load(Path(args.metrics)),
        _load(Path(args.human_comparison)),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
