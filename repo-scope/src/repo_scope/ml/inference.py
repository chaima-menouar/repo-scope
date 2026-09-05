"""Optional inference for the experimental RepoScope risk model."""
from __future__ import annotations

import json
from pathlib import Path

from repo_scope.config import PROJECT_ROOT
from repo_scope.ml.training import EXPECTED_LABELS, feature_row

LEGACY_MODEL_PATH = PROJECT_ROOT / "models" / "repo_risk.joblib"
SCALED_MODEL_PATH = PROJECT_ROOT / "models" / "repo_risk_100k.joblib"
SCALED_METRICS_PATH = PROJECT_ROOT / "models" / "repo_risk_100k_metrics.json"
MIN_SCALED_CLASS_SUPPORT = 20


def scaled_model_is_eligible(
    model_path: Path = SCALED_MODEL_PATH,
    metrics_path: Path = SCALED_METRICS_PATH,
) -> bool:
    if not model_path.exists() or not metrics_path.exists():
        return False
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        counts = {str(label): int(count) for label, count in metrics.get("class_counts", {}).items()}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    if set(counts) != EXPECTED_LABELS:
        return False
    return min(counts.values()) >= MIN_SCALED_CLASS_SUPPORT


def default_model_path() -> Path:
    """Use the scaled artifact only after all three risk classes have meaningful support."""
    if scaled_model_is_eligible():
        return SCALED_MODEL_PATH
    return LEGACY_MODEL_PATH


def predict_risk(stats: dict, model_path: str | Path | None = None) -> dict:
    path = Path(model_path) if model_path is not None else default_model_path()
    if not path.exists():
        return {
            "available": False,
            "status": "model_not_available",
            "note": "The experimental ML artifact has not been generated for this deployment.",
        }

    try:
        import joblib
        import pandas as pd
    except ImportError:
        return {
            "available": False,
            "status": "ml_dependencies_not_installed",
            "note": "Install RepoScope with the optional ML dependencies to enable model inference.",
        }

    try:
        artifact = joblib.load(path)
        model = artifact["model"]
        features = artifact["features"]
        row = feature_row(stats)
        frame = pd.DataFrame([{name: row.get(name, 0) for name in features}])
        probabilities = model.predict_proba(frame)[0]
        classes = [str(value) for value in model.classes_]
        by_class = {
            label: round(float(probability), 4)
            for label, probability in zip(classes, probabilities, strict=True)
        }
        predicted = str(model.predict(frame)[0])
        metadata = artifact.get("training_metadata", {})
        return {
            "available": True,
            "status": metadata.get("model_status", "experimental_weak_supervision"),
            "predicted_label": predicted,
            "probabilities": by_class,
            "training_metadata": metadata,
            "model_artifact": path.name,
            "note": (
                "Experimental baseline trained from conservative weak labels based on independent GitHub "
                "maintenance evidence. It is not a calibrated production risk score."
            ),
        }
    except (KeyError, ValueError, TypeError, OSError) as exc:
        return {
            "available": False,
            "status": "model_load_failed",
            "note": f"Experimental model could not be loaded ({type(exc).__name__}).",
        }
