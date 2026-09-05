from __future__ import annotations

import argparse
import json
from pathlib import Path

from repo_scope.ml.training import EXPECTED_LABELS, FEATURE_COLUMNS


def benchmark(csv_path: Path) -> dict:
    try:
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
        from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("Install ML dependencies with: pip install -e .[ml]") from exc

    frame = pd.read_csv(csv_path)
    required = ["repo", "label", *FEATURE_COLUMNS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Benchmark CSV is missing columns: " + ", ".join(missing))

    labels = frame["label"].astype(str).str.strip()
    if set(labels) != EXPECTED_LABELS:
        raise ValueError("Benchmark requires healthy, watch and risky classes.")

    groups = frame["repo"].astype(str).str.strip()
    x = frame[FEATURE_COLUMNS].fillna(0)
    class_counts = labels.value_counts()
    folds = min(5, int(class_counts.min()))
    if folds < 2:
        raise ValueError("Each risk class needs at least two rows for grouped benchmarking.")

    cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=42)
    models = {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
    }

    results: dict[str, dict[str, float]] = {}
    for name, model in models.items():
        predictions = cross_val_predict(model, x, labels, groups=groups, cv=cv, n_jobs=-1)
        results[name] = {
            "accuracy": round(float(accuracy_score(labels, predictions)), 6),
            "balanced_accuracy": round(float(balanced_accuracy_score(labels, predictions)), 6),
            "macro_f1": round(float(f1_score(labels, predictions, average="macro", zero_division=0)), 6),
        }

    ranking = sorted(
        results,
        key=lambda name: (results[name]["macro_f1"], results[name]["balanced_accuracy"]),
        reverse=True,
    )
    return {
        "rows": len(frame),
        "repositories": int(groups.nunique()),
        "folds": folds,
        "class_counts": {str(label): int(count) for label, count in class_counts.sort_index().items()},
        "models": results,
        "best_experimental_baseline": ranking[0],
        "selection_metric": "macro_f1_then_balanced_accuracy",
        "note": "This benchmark compares grouped out-of-fold predictions; it does not automatically promote a model.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark RepoScope risk-model baselines with grouped CV.")
    parser.add_argument("input", nargs="?", default="data/repo_risk_training_combined_100k.csv")
    parser.add_argument("--output", default="models/repo_risk_100k_benchmark.json")
    args = parser.parse_args()
    report = benchmark(Path(args.input))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
