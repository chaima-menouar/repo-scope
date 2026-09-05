import json

import joblib

from repo_scope.ml import inference
from repo_scope.ml.inference import predict_risk
from repo_scope.ml.labels import assign_weak_label
from repo_scope.ml.training import FEATURE_COLUMNS, FEATURE_SCHEMA_VERSION


def test_weak_labels_require_independent_evidence():
    assert assign_weak_label({"archived": "1", "latest_release_age_days": ""})[0] == "risky"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "30"})[0] == "healthy"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "150"})[0] == "healthy"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "151"}) is None
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "179"}) is None
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "180"})[0] == "watch"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "400"})[0] == "watch"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": ""}) is None


def test_ml_inference_fails_closed_without_artifact(tmp_path):
    result = predict_risk({}, tmp_path / "missing.joblib")
    assert result["available"] is False
    assert result["status"] == "model_not_available"


def test_ml_inference_rejects_unknown_feature_schema(tmp_path):
    artifact_path = tmp_path / "bad-schema.joblib"
    joblib.dump(
        {
            "model": object(),
            "features": FEATURE_COLUMNS,
            "feature_schema_version": "reposcope-risk-features-v999",
        },
        artifact_path,
    )
    result = predict_risk({}, artifact_path)
    assert result["available"] is False
    assert result["status"] == "model_schema_incompatible"


def test_ml_inference_rejects_feature_list_mismatch_even_without_version(tmp_path):
    artifact_path = tmp_path / "bad-features.joblib"
    joblib.dump(
        {
            "model": object(),
            "features": [*FEATURE_COLUMNS[:-1], "unexpected_feature"],
        },
        artifact_path,
    )
    result = predict_risk({}, artifact_path)
    assert result["available"] is False
    assert result["status"] == "model_schema_incompatible"


def test_current_feature_schema_constant_is_versioned():
    assert FEATURE_SCHEMA_VERSION == "reposcope-risk-features-v1"


def test_default_model_prefers_scaled_artifact_with_complete_support(tmp_path, monkeypatch):
    legacy = tmp_path / "repo_risk.joblib"
    scaled = tmp_path / "repo_risk_100k.joblib"
    metrics = tmp_path / "repo_risk_100k_metrics.json"
    legacy.write_bytes(b"legacy")
    scaled.write_bytes(b"scaled")
    metrics.write_text(
        json.dumps({"class_counts": {"healthy": 200, "watch": 40, "risky": 40}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(inference, "LEGACY_MODEL_PATH", legacy)
    monkeypatch.setattr(inference, "SCALED_MODEL_PATH", scaled)
    monkeypatch.setattr(inference, "SCALED_METRICS_PATH", metrics)
    assert inference.scaled_model_is_eligible(scaled, metrics) is True
    assert inference.default_model_path() == scaled


def test_default_model_rejects_incomplete_scaled_artifact(tmp_path, monkeypatch):
    legacy = tmp_path / "repo_risk.joblib"
    scaled = tmp_path / "repo_risk_100k.joblib"
    metrics = tmp_path / "repo_risk_100k_metrics.json"
    legacy.write_bytes(b"legacy")
    scaled.write_bytes(b"scaled")
    metrics.write_text(
        json.dumps({"class_counts": {"healthy": 238, "watch": 2}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(inference, "LEGACY_MODEL_PATH", legacy)
    monkeypatch.setattr(inference, "SCALED_MODEL_PATH", scaled)
    monkeypatch.setattr(inference, "SCALED_METRICS_PATH", metrics)
    assert inference.scaled_model_is_eligible(scaled, metrics) is False
    assert inference.default_model_path() == legacy


def test_default_model_falls_back_when_scaled_artifact_missing(tmp_path, monkeypatch):
    legacy = tmp_path / "repo_risk.joblib"
    scaled = tmp_path / "repo_risk_100k.joblib"
    metrics = tmp_path / "repo_risk_100k_metrics.json"
    legacy.write_bytes(b"legacy")
    monkeypatch.setattr(inference, "LEGACY_MODEL_PATH", legacy)
    monkeypatch.setattr(inference, "SCALED_MODEL_PATH", scaled)
    monkeypatch.setattr(inference, "SCALED_METRICS_PATH", metrics)
    assert inference.default_model_path() == legacy
