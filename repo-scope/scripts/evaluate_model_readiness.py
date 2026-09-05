from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.exists() or not path.stat().st_size:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(progress: dict, quality: dict, metrics: dict, human_comparison: dict) -> dict:
    reasons: list[str] = []
    class_counts = metrics.get("class_counts", {})
    cv = metrics.get("cross_validation", {})
    temporal = metrics.get("temporal_holdout", {})
    calibration = metrics.get("calibration", {})

    deep_snapshots = int(progress.get("deep_snapshots", 0) or 0)
    if deep_snapshots < 1000:
        reasons.append("fewer than 1000 deep repository snapshots collected")

    for label in ("healthy", "watch", "risky"):
        if int(class_counts.get(label, 0) or 0) < 50:
            reasons.append(f"class {label} has fewer than 50 labelled repositories")

    if float(cv.get("macro_f1", 0) or 0) < 0.65:
        reasons.append("grouped cross-validation macro F1 is below 0.65")
    if float(cv.get("balanced_accuracy", 0) or 0) < 0.65:
        reasons.append("grouped cross-validation balanced accuracy is below 0.65")

    if not temporal.get("available"):
        reasons.append("temporal holdout is not available")
    else:
        if float(temporal.get("macro_f1", 0) or 0) < 0.60:
            reasons.append("temporal holdout macro F1 is below 0.60")
        if temporal.get("missing_test_classes"):
            reasons.append("temporal holdout does not contain all three risk classes")

    if calibration.get("status") != "analysis_only_uncalibrated":
        reasons.append("out-of-fold calibration diagnostics are missing")
    if float(calibration.get("expected_calibration_error_10_bin", 1) or 1) > 0.15:
        reasons.append("expected calibration error is above 0.15")

    if human_comparison.get("status") != "ready_for_comparison":
        reasons.append("human-reviewed validation subset is still too small")
    elif float(human_comparison.get("agreement_rate", 0) or 0) < 0.70:
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
