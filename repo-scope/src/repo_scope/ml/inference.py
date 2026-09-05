"""Optional inference for the experimental RepoScope risk model."""
from __future__ import annotations

import json
from pathlib import Path

from repo_scope.config import PROJECT_ROOT
from repo_scope.ml.training import EXPECTED_LABELS, FEATURE_COLUMNS, FEATURE_SCHEMA_VERSION, feature_row

LEGACY_MODEL_PATH = PROJECT_ROOT / "models" / "repo_risk.joblib"
SCALED_MODEL_PATH = PROJECT_ROOT / "models" / "repo_risk_100k.joblib"
SCALED_METRICS_PATH = PROJECT_ROOT / "models" / "repo_risk_100k_metrics.json"
SCALED_READINESS_PATH = PROJECT_ROOT / "models" / "repo_risk_100k_readiness.json"
SCALED_PROMOTION_PATH = PROJECT_ROOT / "models" / "repo_risk_100k_promotion.json"
MIN_SCALED_CLASS_SUPPORT = 20


def _read_json(path: Path) -> dict:
    try:
        if not path.exists() or not path.stat().st_size:
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def scaled_model_is_eligible(
    model_path: Path = SCALED_MODEL_PATH,
    metrics_path: Path = SCALED_METRICS_PATH,
    readiness_path: Path = SCALED_READINESS_PATH,
    promotion_path: Path = SCALED_PROMOTION_PATH,
) -> bool:
    """Require data support, automated readiness and explicit human promotion approval."""
    if not model_path.exists():
        return False

    metrics = _read_json(metrics_path)
    counts = {str(label): int(count) for label, count in metrics.get("class_counts", {}).items()}
    if set(counts) != EXPECTED_LABELS or min(counts.values(), default=0) < MIN_SCALED_CLASS_SUPPORT:
        return False

    readiness = _read_json(readiness_path)
    if readiness.get("eligible") is not True or readiness.get("promotion_status") != "eligible_for_manual_review":
        return False

    promotion = _read_json(promotion_path)
    return promotion.get("approved") is True


def default_model_path() -> Path:
    """Use the scaled artifact only after automated validation and explicit manual promotion."""
    if scaled_model_is_eligible(
        SCALED_MODEL_PATH,
        SCALED_METRICS_PATH,
        SCALED_READINESS_PATH,
        SCALED_PROMOTION_PATH,
    ):
        return SCALED_MODEL_PATH
    return LEGACY_MODEL_PATH


def _artifact_schema_is_compatible(artifact: dict) -> bool:
    """Accept v1 artifacts and the pre-versioned legacy artifact only when its feature list matches v1 exactly."""
    features = artifact.get("features")
    if features != FEATURE_COLUMNS:
        return False
    schema_version = artifact.get("feature_schema_version")
    return schema_version in (None, FEATURE_SCHEMA_VERSION)


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
        if not isinstance(artifact, dict) or not _artifact_schema_is_compatible(artifact):
            return {
                "available": False,
                "status": "model_schema_incompatible",
                "note": "The model artifact uses an unsupported RepoScope feature schema and was not loaded.",
            }
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
            "feature_schema_version": artifact.get("feature_schema_version", FEATURE_SCHEMA_VERSION),
            "note": (
                "Experimental model output. Probability values are diagnostic and must not be interpreted "
                "as calibrated production confidence unless the promoted artifact documentation explicitly says so."
            ),
        }
    except (KeyError, ValueError, TypeError, OSError) as exc:
        return {
            "available": False,
            "status": "model_load_failed",
            "note": f"Experimental model could not be loaded ({type(exc).__name__}).",
        }
