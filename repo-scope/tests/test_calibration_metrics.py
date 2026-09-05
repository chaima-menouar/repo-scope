from __future__ import annotations

import numpy as np

from repo_scope.ml.training import _calibration_payload


def test_calibration_payload_reports_out_of_fold_diagnostics():
    labels = ["healthy", "risky", "watch"]
    y_true = ["healthy", "risky", "watch", "healthy"]
    probabilities = np.array(
        [
            [0.80, 0.10, 0.10],
            [0.10, 0.80, 0.10],
            [0.10, 0.10, 0.80],
            [0.60, 0.20, 0.20],
        ]
    )
    report = _calibration_payload(y_true, probabilities, labels)
    assert report["status"] == "analysis_only_uncalibrated"
    assert report["log_loss"] > 0
    assert report["multiclass_brier_score"] > 0
    assert 0 <= report["expected_calibration_error_10_bin"] <= 1
    assert 0 <= report["mean_confidence"] <= 1
    assert report["bins"]
