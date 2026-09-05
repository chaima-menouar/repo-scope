from repo_scope.ml.inference import predict_risk
from repo_scope.ml.labels import assign_weak_label


def test_weak_labels_require_independent_evidence():
    assert assign_weak_label({"archived": "1", "latest_release_age_days": ""})[0] == "risky"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "30"})[0] == "healthy"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": "400"})[0] == "watch"
    assert assign_weak_label({"archived": "0", "latest_release_age_days": ""}) is None


def test_ml_inference_fails_closed_without_artifact(tmp_path):
    result = predict_risk({}, tmp_path / "missing.joblib")
    assert result["available"] is False
    assert result["status"] == "model_not_available"
