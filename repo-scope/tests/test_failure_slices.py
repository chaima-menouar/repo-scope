from __future__ import annotations

import pandas as pd

from repo_scope.ml.training import _failure_slice_diagnostics


def test_failure_slices_use_context_without_changing_feature_contract():
    frame = pd.DataFrame(
        {
            "language": ["Python"] * 5 + ["Go"] * 5,
            "size_kb": [500, 600, 700, 800, 900, 20_000, 21_000, 22_000, 23_000, 24_000],
            "archived": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
            "days_since_last_commit": [10, 20, 30, 40, 50, 500, 500, 500, 500, 500],
        }
    )
    truth = ["healthy"] * 5 + ["risky"] * 5
    predictions = ["healthy", "healthy", "watch", "healthy", "healthy", "risky", "watch", "risky", "risky", "risky"]

    report = _failure_slice_diagnostics(frame, truth, predictions)
    assert report["context_is_not_model_input"] is True
    assert report["source"] == "repository-grouped out-of-fold predictions"
    assert report["dimensions"]["language"][0]["slice"] in {"Python", "Go"}
    python_slice = next(item for item in report["dimensions"]["language"] if item["slice"] == "Python")
    assert python_slice["count"] == 5
    assert python_slice["error_count"] == 1
    assert "repository_size" in report["dimensions"]
    assert "maintenance_style" in report["dimensions"]
