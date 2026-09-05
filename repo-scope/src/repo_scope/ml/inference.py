"""Optional inference for the experimental RepoScope risk model."""
from __future__ import annotations

from pathlib import Path

from repo_scope.config import PROJECT_ROOT
from repo_scope.ml.training import feature_row

DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "repo_risk.joblib"


def predict_risk(stats: dict, model_path: str | Path = DEFAULT_MODEL_PATH) -> dict:
    path = Path(model_path)
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
        return {
            "available": True,
            "status": "experimental_weak_supervision",
            "predicted_label": predicted,
            "probabilities": by_class,
            "training_metadata": artifact.get("training_metadata", {}),
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
