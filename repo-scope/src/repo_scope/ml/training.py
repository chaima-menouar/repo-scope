"""Supervised training pipeline for RepoScope's experimental repository-risk model."""
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


def _validate_training_frame(frame) -> None:
    required = FEATURE_COLUMNS + ["repo", "label"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Training CSV is missing columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Training data is empty.")
    if frame["label"].isna().any() or frame["label"].astype(str).str.strip().eq("").any():
        raise ValueError("Every training row must have a non-empty evidence-backed or human-reviewed label.")
    if frame["repo"].isna().any() or frame["repo"].astype(str).str.strip().eq("").any():
        raise ValueError("Every training row must identify its repository in the 'repo' column.")
    if frame["label"].nunique() < 2:
        raise ValueError("Training data must contain at least two label classes.")
    if frame["repo"].nunique() < 4:
        raise ValueError("Training data must contain at least four distinct repositories.")


def train_from_csv(csv_path: str, output_path: str = "models/repo_risk.joblib") -> dict:
    try:
        import joblib
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report
        from sklearn.model_selection import GroupShuffleSplit
    except ImportError as exc:
        raise RuntimeError("Install ML dependencies with: pip install -e .[ml]") from exc

    frame = pd.read_csv(csv_path)
    _validate_training_frame(frame)

    x = frame[FEATURE_COLUMNS].fillna(0)
    y = frame["label"].astype(str).str.strip()
    groups = frame["repo"].astype(str).str.strip()

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(x, y, groups=groups))
    x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    train_repos = sorted(groups.iloc[train_idx].unique().tolist())
    test_repos = sorted(groups.iloc[test_idx].unique().tolist())

    if set(train_repos) & set(test_repos):
        raise RuntimeError("Repository leakage detected between train and test splits.")
    if y_train.nunique() < 2:
        raise ValueError(
            "The repository-level split left the training set with fewer than two classes. "
            "Add more labelled repositories per class."
        )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    feature_importance = {
        feature: round(float(importance), 6)
        for feature, importance in sorted(
            zip(FEATURE_COLUMNS, model.feature_importances_, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
    }
    label_sources = []
    if "label_source" in frame.columns:
        label_sources = sorted(frame["label_source"].dropna().astype(str).unique().tolist())

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": model,
        "features": FEATURE_COLUMNS,
        "classes": [str(value) for value in model.classes_],
        "training_metadata": {
            "rows": len(frame),
            "repositories": int(groups.nunique()),
            "train_repositories": len(train_repos),
            "test_repositories": len(test_repos),
            "split_strategy": "group_shuffle_by_repository",
            "random_state": 42,
            "label_sources": label_sources,
            "model_status": "experimental_weak_supervision" if label_sources else "supervised",
        },
    }
    joblib.dump(artifact, target)

    return {
        "model_path": str(target),
        "rows": len(frame),
        "repositories": int(groups.nunique()),
        "train_rows": len(train_idx),
        "test_rows": len(test_idx),
        "train_repositories": len(train_repos),
        "test_repositories": len(test_repos),
        "classes": artifact["classes"],
        "label_sources": label_sources,
        "feature_importance": feature_importance,
        "report": report,
    }


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
