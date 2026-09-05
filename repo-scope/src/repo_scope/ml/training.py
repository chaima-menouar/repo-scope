"""Supervised training pipeline for RepoScope's experimental repository-risk model."""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

FEATURE_SCHEMA_VERSION = "reposcope-risk-features-v1"
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
EXPECTED_LABELS = {"healthy", "watch", "risky"}
LABEL_ORDER = ["healthy", "watch", "risky"]


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
    labels = set(frame["label"].astype(str).str.strip())
    if labels != EXPECTED_LABELS:
        missing_labels = sorted(EXPECTED_LABELS - labels)
        unexpected = sorted(labels - EXPECTED_LABELS)
        details = []
        if missing_labels:
            details.append(f"missing classes: {', '.join(missing_labels)}")
        if unexpected:
            details.append(f"unexpected classes: {', '.join(unexpected)}")
        raise ValueError(
            "RepoScope risk training requires exactly healthy, watch and risky labels (" + "; ".join(details) + ")."
        )
    if frame["repo"].nunique() < 4:
        raise ValueError("Training data must contain at least four distinct repositories.")


def _model():
    try:
        from sklearn.ensemble import RandomForestClassifier
    except ImportError as exc:
        raise RuntimeError("Install ML dependencies with: pip install -e .[ml]") from exc

    return RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def _evaluation_payload(y_true, predictions) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )

    return {
        "labels": LABEL_ORDER,
        "accuracy": round(float(accuracy_score(y_true, predictions)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, predictions)), 6),
        "macro_f1": round(
            float(f1_score(y_true, predictions, labels=LABEL_ORDER, average="macro", zero_division=0)),
            6,
        ),
        "confusion_matrix": confusion_matrix(y_true, predictions, labels=LABEL_ORDER).tolist(),
        "report": classification_report(
            y_true,
            predictions,
            labels=LABEL_ORDER,
            output_dict=True,
            zero_division=0,
        ),
    }


def _temporal_holdout(frame, x, y, groups) -> dict:
    """Evaluate on the newest repository snapshots when timestamps are available.

    Repository identity is kept entirely on one side of the split. The split is
    intentionally chronological rather than stratified, because the purpose is
    to expose time-shift risk rather than manufacture balanced test data.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Install ML dependencies with: pip install -e .[ml]") from exc

    if "snapshot_at_utc" not in frame.columns:
        return {"available": False, "reason": "snapshot_at_utc column is not present"}

    timestamps = pd.to_datetime(frame["snapshot_at_utc"], errors="coerce", utc=True)
    valid = timestamps.notna()
    valid_repositories = groups[valid].nunique()
    if valid_repositories < 8:
        return {
            "available": False,
            "reason": "fewer than eight repositories have valid snapshot timestamps",
            "repositories_with_timestamps": int(valid_repositories),
        }

    repo_times = (
        pd.DataFrame({"repo": groups[valid], "snapshot": timestamps[valid]})
        .groupby("repo", as_index=False)["snapshot"]
        .max()
        .sort_values(["snapshot", "repo"], kind="stable")
    )
    test_repository_count = max(1, math.ceil(len(repo_times) * 0.25))
    test_repository_count = min(test_repository_count, len(repo_times) - 3)
    train_repos = set(repo_times.iloc[:-test_repository_count]["repo"].tolist())
    test_repos = set(repo_times.iloc[-test_repository_count:]["repo"].tolist())

    if train_repos & test_repos:
        raise RuntimeError("Repository leakage detected in temporal holdout split.")

    train_mask = groups.isin(train_repos) & valid
    test_mask = groups.isin(test_repos) & valid
    if not train_mask.any() or not test_mask.any():
        return {"available": False, "reason": "temporal split produced an empty train or test partition"}

    temporal_y_train = y[train_mask]
    temporal_y_test = y[test_mask]
    if set(temporal_y_train) != EXPECTED_LABELS:
        return {
            "available": False,
            "reason": "older temporal training partition does not contain all three risk classes",
            "train_class_counts": {
                str(label): int(count)
                for label, count in temporal_y_train.value_counts().sort_index().items()
            },
        }

    temporal_model = _model()
    temporal_model.fit(x[train_mask], temporal_y_train)
    predictions = temporal_model.predict(x[test_mask])
    payload = _evaluation_payload(temporal_y_test, predictions)
    cutoff = repo_times.iloc[-test_repository_count]["snapshot"]
    test_class_counts = {
        str(label): int(count)
        for label, count in temporal_y_test.value_counts().sort_index().items()
    }
    payload.update(
        {
            "available": True,
            "strategy": "newest_25pct_repositories_by_snapshot_time",
            "cutoff_utc": cutoff.isoformat(),
            "train_repositories": len(train_repos),
            "test_repositories": len(test_repos),
            "train_rows": int(train_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "test_class_counts": test_class_counts,
            "missing_test_classes": sorted(EXPECTED_LABELS - set(temporal_y_test)),
        }
    )
    return payload


def train_from_csv(csv_path: str, output_path: str = "models/repo_risk.joblib") -> dict:
    try:
        import joblib
        import pandas as pd
        import sklearn
        from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix, f1_score
        from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold, cross_val_predict
    except ImportError as exc:
        raise RuntimeError("Install ML dependencies with: pip install -e .[ml]") from exc

    source = Path(csv_path)
    dataset_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    trained_at_utc = datetime.now(timezone.utc).isoformat()

    frame = pd.read_csv(source)
    _validate_training_frame(frame)

    x = frame[FEATURE_COLUMNS].fillna(0)
    y = frame["label"].astype(str).str.strip()
    groups = frame["repo"].astype(str).str.strip()
    class_counts = {str(label): int(count) for label, count in y.value_counts().sort_index().items()}

    min_class_count = min(class_counts.values())
    cv_folds = min(5, min_class_count)
    if cv_folds < 2:
        raise ValueError("Each class needs at least two repositories for grouped cross-validation.")

    cv = StratifiedGroupKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    cv_predictions = cross_val_predict(_model(), x, y, groups=groups, cv=cv, n_jobs=-1)
    cv_report = classification_report(y, cv_predictions, labels=LABEL_ORDER, output_dict=True, zero_division=0)
    cv_accuracy = float(accuracy_score(y, cv_predictions))
    cv_balanced_accuracy = float(balanced_accuracy_score(y, cv_predictions))
    cv_macro_f1 = float(f1_score(y, cv_predictions, labels=LABEL_ORDER, average="macro", zero_division=0))
    cv_confusion_matrix = confusion_matrix(y, cv_predictions, labels=LABEL_ORDER).tolist()

    warning_reasons = []
    if len(frame) < 100:
        warning_reasons.append("fewer than 100 labelled repository snapshots")
    if min_class_count < 20:
        warning_reasons.append("at least one class has fewer than 20 repositories")
    if cv_accuracy >= 0.99:
        warning_reasons.append("cross-validation accuracy is unusually high for a small weakly-labelled dataset")
    if cv_balanced_accuracy < 0.60:
        warning_reasons.append("balanced accuracy is below 0.60, indicating weak minority-class performance")
    evaluation_warning = None
    if warning_reasons:
        evaluation_warning = (
            "Small weakly-labelled dataset; metrics may be optimistic and must not be treated as production "
            "performance. Signals: " + "; ".join(warning_reasons) + "."
        )

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(x, y, groups=groups))
    x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    train_repos = sorted(groups.iloc[train_idx].unique().tolist())
    test_repos = sorted(groups.iloc[test_idx].unique().tolist())

    if set(train_repos) & set(test_repos):
        raise RuntimeError("Repository leakage detected between train and test splits.")
    if set(y_train) != EXPECTED_LABELS:
        raise ValueError(
            "The repository-level split did not preserve all three risk classes in training. "
            "Add more labelled repositories per class."
        )

    holdout_model = _model()
    holdout_model.fit(x_train, y_train)
    heldout_predictions = holdout_model.predict(x_test)
    heldout = _evaluation_payload(y_test, heldout_predictions)
    temporal_holdout = _temporal_holdout(frame, x, y, groups)

    # Evaluation uses isolated splits. The saved inference artifact is then
    # refit on every labelled row so validated data is not unnecessarily lost.
    final_model = _model()
    final_model.fit(x, y)
    feature_importance = {
        feature: round(float(importance), 6)
        for feature, importance in sorted(
            zip(FEATURE_COLUMNS, final_model.feature_importances_, strict=True),
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
        "model": final_model,
        "features": FEATURE_COLUMNS,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "classes": [str(value) for value in final_model.classes_],
        "training_metadata": {
            "trained_at_utc": trained_at_utc,
            "source_csv": str(source),
            "dataset_sha256": dataset_sha256,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "scikit_learn_version": sklearn.__version__,
            "model_type": type(final_model).__name__,
            "artifact_fit_strategy": "refit_on_all_rows_after_isolated_evaluation",
            "rows": len(frame),
            "repositories": int(groups.nunique()),
            "train_repositories": len(train_repos),
            "test_repositories": len(test_repos),
            "split_strategy": "group_shuffle_by_repository",
            "cross_validation_strategy": "stratified_group_k_fold",
            "cross_validation_folds": cv_folds,
            "temporal_holdout_available": bool(temporal_holdout.get("available")),
            "random_state": 42,
            "class_counts": class_counts,
            "label_sources": label_sources,
            "model_status": "experimental_weak_supervision" if label_sources else "supervised",
            "evaluation_warning": evaluation_warning,
        },
    }
    joblib.dump(artifact, target)

    return {
        "model_path": str(target),
        "trained_at_utc": trained_at_utc,
        "source_csv": str(source),
        "dataset_sha256": dataset_sha256,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "scikit_learn_version": sklearn.__version__,
        "model_type": type(final_model).__name__,
        "artifact_fit_strategy": "refit_on_all_rows_after_isolated_evaluation",
        "rows": len(frame),
        "repositories": int(groups.nunique()),
        "train_rows": len(train_idx),
        "test_rows": len(test_idx),
        "train_repositories": len(train_repos),
        "test_repositories": len(test_repos),
        "classes": artifact["classes"],
        "class_counts": class_counts,
        "label_sources": label_sources,
        "feature_importance": feature_importance,
        "cross_validation": {
            "strategy": "stratified_group_k_fold",
            "folds": cv_folds,
            "labels": LABEL_ORDER,
            "accuracy": round(cv_accuracy, 6),
            "balanced_accuracy": round(cv_balanced_accuracy, 6),
            "macro_f1": round(cv_macro_f1, 6),
            "confusion_matrix": cv_confusion_matrix,
            "report": cv_report,
        },
        "heldout": heldout,
        "temporal_holdout": temporal_holdout,
        "heldout_report": heldout["report"],
        "evaluation_warning": evaluation_warning,
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
