"""Optional supervised training pipeline for repository risk classification.

This module deliberately does not ship a fake pretrained model. Train it only after
collecting and labelling real repository snapshots. Install with ``pip install -e .[ml]``.
"""
from __future__ import annotations

from pathlib import Path

FEATURE_COLUMNS = [
    "days_since_last_commit",
    "bus_factor",
    "issue_closure_rate_pct",
    "pr_merge_rate_pct",
    "commits_90d",
    "contributors_sampled",
    "has_ci",
    "has_tests",
]


def train_from_csv(csv_path: str, output_path: str = "models/repo_risk.joblib") -> dict:
    try:
        import joblib
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise RuntimeError("Install ML dependencies with: pip install -e .[ml]") from exc

    frame = pd.read_csv(csv_path)
    missing = [column for column in FEATURE_COLUMNS + ["label"] if column not in frame.columns]
    if missing:
        raise ValueError(f"Training CSV is missing columns: {', '.join(missing)}")
    if frame["label"].nunique() < 2:
        raise ValueError("Training data must contain at least two label classes.")

    x = frame[FEATURE_COLUMNS].fillna(0)
    y = frame["label"]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLUMNS}, target)
    return {"model_path": str(target), "test_rows": len(x_test), "report": report}


def feature_row(stats: dict) -> dict:
    return {
        "days_since_last_commit": stats.get("activity", {}).get("days_since_last_commit") or 0,
        "bus_factor": stats.get("contributors", {}).get("bus_factor") or 0,
        "issue_closure_rate_pct": stats.get("issues", {}).get("closure_rate_pct") or 0,
        "pr_merge_rate_pct": stats.get("pull_requests", {}).get("merge_rate_pct") or 0,
        "commits_90d": stats.get("activity", {}).get("commits_90d") or 0,
        "contributors_sampled": stats.get("contributors", {}).get("sampled_total") or 0,
        "has_ci": int(bool(stats.get("signals", {}).get("has_ci"))),
        "has_tests": int(bool(stats.get("signals", {}).get("has_tests"))),
    }
