"""Cloud and delivery-readiness signals derived from repository structure."""
from __future__ import annotations


WEIGHTS = {
    "has_ci": 25,
    "has_tests": 15,
    "has_docker": 20,
    "has_iac": 20,
    "has_lockfile": 10,
    "has_deploy_config": 10,
}

LABELS = {
    "has_ci": "CI/CD workflow",
    "has_tests": "automated tests",
    "has_docker": "container definition",
    "has_iac": "infrastructure as code",
    "has_lockfile": "dependency lockfile",
    "has_deploy_config": "deployment configuration",
}


def cloud_readiness(signals: dict) -> dict:
    checks = []
    score = 0
    for key, weight in WEIGHTS.items():
        present = bool(signals.get(key))
        if present:
            score += weight
        checks.append({
            "key": key,
            "label": LABELS[key],
            "present": present,
            "weight": weight,
        })

    if score >= 80:
        posture = "production-ready"
    elif score >= 55:
        posture = "cloud-capable"
    elif score >= 30:
        posture = "partial"
    else:
        posture = "early"

    missing = [item["label"] for item in checks if not item["present"]]
    return {
        "score": score,
        "posture": posture,
        "checks": checks,
        "missing": missing,
        "note": "This score measures repository delivery signals, not the quality or security of a live cloud deployment.",
    }
