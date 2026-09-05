"""Explainable summaries plus optional LLM-powered engineering insights."""
from __future__ import annotations

import json

from repo_scope.config import OPENAI_API_KEY, OPENAI_MODEL


def build_smart_summary(data: dict) -> str:
    stats = data.get("stats", data)
    health = stats.get("health", {})
    activity = stats.get("activity", {})
    contributors = stats.get("contributors", {})
    issues = stats.get("issues", {})
    signals = stats.get("signals", {})

    parts = [f"Repository health is {health.get('label', 'unrated').lower()} at {health.get('score', 0)}/100."]
    days = activity.get("days_since_last_commit")
    if days is not None:
        parts.append(f"The latest sampled commit is {days} day{'s' if days != 1 else ''} old.")
    factor = contributors.get("bus_factor", 0)
    if factor:
        ownership = "concentrated ownership" if factor <= 2 else "broader contribution resilience"
        parts.append(f"The sampled bus factor is {factor}, indicating {ownership}.")
    closure = issues.get("closure_rate_pct")
    if closure is not None:
        parts.append(f"Sampled issue closure rate is {closure:.0f}%.")
    cloud = stats.get("cloud_readiness", {})
    if cloud:
        parts.append(f"Cloud/DevOps readiness is {cloud.get('score', 0)}/100 ({cloud.get('posture', 'unrated')}).")
    missing = [
        name
        for name, present in (("CI", signals.get("has_ci")), ("tests", signals.get("has_tests")))
        if not present
    ]
    if missing:
        parts.append("Engineering hygiene could improve around " + " and ".join(missing) + ".")
    return " ".join(parts)


def build_structured_diagnosis(data: dict) -> dict:
    stats = data.get("stats", data)
    health = stats.get("health", {})
    activity = stats.get("activity", {})
    contributors = stats.get("contributors", {})
    issues = stats.get("issues", {})
    pulls = stats.get("pull_requests", {})
    signals = stats.get("signals", {})
    cloud = stats.get("cloud_readiness", {})

    risks: list[dict] = []
    strengths: list[str] = []
    actions: list[str] = []

    days = activity.get("days_since_last_commit")
    if days is not None and days > 30:
        severity = "high" if days > 90 else "medium"
        risks.append({
            "title": "Repository activity is stale",
            "severity": severity,
            "evidence": f"Latest sampled commit is {days} days old.",
            "recommendation": "Review maintenance ownership and define a regular release or maintenance cadence.",
        })
        actions.append("Restore an explicit maintenance cadence and ownership plan.")
    elif days is not None:
        strengths.append(f"Recent development activity: latest sampled commit is {days} days old.")

    bus_factor = contributors.get("bus_factor") or 0
    if bus_factor and bus_factor <= 2:
        risks.append({
            "title": "Contributor concentration",
            "severity": "high" if bus_factor == 1 else "medium",
            "evidence": f"Sampled bus factor is {bus_factor}.",
            "recommendation": "Spread review, release, and subsystem ownership across more maintainers.",
        })
        actions.append("Reduce single-maintainer dependency through shared code ownership and reviews.")
    elif bus_factor > 2:
        strengths.append(f"Contributor resilience is healthier with a sampled bus factor of {bus_factor}.")

    closure = issues.get("closure_rate_pct")
    if closure is not None and closure < 50:
        risks.append({
            "title": "Issue backlog pressure",
            "severity": "medium",
            "evidence": f"Sampled issue closure rate is {closure:.0f}%.",
            "recommendation": "Triage stale issues, define ownership, and track closure targets by milestone.",
        })
        actions.append("Run an issue triage pass and assign backlog ownership.")
    elif closure is not None and closure >= 70:
        strengths.append(f"Issue hygiene is strong with a sampled closure rate of {closure:.0f}%.")

    merge_rate = pulls.get("merge_rate_pct")
    if merge_rate is not None and merge_rate >= 70:
        strengths.append(f"Pull-request throughput is healthy at a sampled {merge_rate:.0f}% merge rate.")

    for key, label, action in (
        ("has_ci", "Continuous integration is missing", "Add CI checks for tests and build validation."),
        ("has_tests", "Automated tests were not detected", "Add automated tests for critical repository paths."),
    ):
        if not signals.get(key):
            risks.append({
                "title": label,
                "severity": "medium",
                "evidence": f"RepoScope did not detect the corresponding repository signal ({key}).",
                "recommendation": action,
            })
            actions.append(action)
        else:
            strengths.append(f"{label.replace(' is missing', '').replace(' were not detected', '')} detected.")

    cloud_score = cloud.get("score")
    if cloud_score is not None and cloud_score < 55:
        missing_cloud = cloud.get("missing", [])[:3]
        evidence = f"Cloud/DevOps readiness is {cloud_score}/100 ({cloud.get('posture', 'early')})."
        if missing_cloud:
            evidence += " Missing signals include " + ", ".join(missing_cloud) + "."
        action = "Add the highest-value missing delivery controls before production deployment."
        risks.append({
            "title": "Cloud delivery readiness is incomplete",
            "severity": "medium",
            "evidence": evidence,
            "recommendation": action,
        })
        actions.append(action)
    elif cloud_score is not None and cloud_score >= 80:
        strengths.append(f"Cloud/DevOps repository readiness is strong at {cloud_score}/100.")

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    risks.sort(key=lambda item: severity_rank.get(item["severity"], 3))
    risks = risks[:3]

    score = int(health.get("score") or 0)
    if score >= 80:
        risk_level = "low"
    elif score >= 60:
        risk_level = "moderate"
    else:
        risk_level = "high"

    return {
        "executive_summary": build_smart_summary(data),
        "risk_level": risk_level,
        "top_risks": risks,
        "strengths": strengths[:4],
        "next_actions": list(dict.fromkeys(actions))[:4],
        "evidence_coverage": "sampled GitHub metadata, engineering-practice signals, and Cloud/DevOps readiness",
    }


def generate_ai_insight(data: dict) -> dict:
    """Use OpenAI when configured; otherwise return a deterministic explainable diagnosis."""
    diagnosis = build_structured_diagnosis(data)
    fallback = diagnosis["executive_summary"]
    if not OPENAI_API_KEY:
        return {
            "mode": "explainable-fallback",
            "model": None,
            "text": fallback,
            "diagnosis": diagnosis,
            "note": "Set OPENAI_API_KEY to enable the LLM analyst. The dashboard remains fully functional without it.",
        }

    try:
        from openai import OpenAI

        stats = data.get("stats", data)
        compact = {
            "repo": stats.get("repo"),
            "health": stats.get("health"),
            "activity": stats.get("activity"),
            "contributors": {
                "sampled_total": stats.get("contributors", {}).get("sampled_total"),
                "bus_factor": stats.get("contributors", {}).get("bus_factor"),
                "top": stats.get("contributors", {}).get("top", [])[:5],
            },
            "issues": stats.get("issues"),
            "pull_requests": stats.get("pull_requests"),
            "signals": stats.get("signals"),
            "cloud_readiness": stats.get("cloud_readiness"),
            "experimental_ml": stats.get("ml_risk"),
            "alerts": data.get("alerts", []),
        }
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=(
                "You are RepoScope's engineering analyst. Analyze the aggregate GitHub repository metrics below. "
                "Write 3 concise paragraphs: health diagnosis, main risk, and next engineering action. "
                "Treat experimental ML output as supporting evidence only. Do not invent metrics or claim access to "
                "source code. Mention that metrics are sampled where relevant.\n\n"
                + json.dumps(compact, ensure_ascii=False)
            ),
        )
        return {
            "mode": "openai",
            "model": OPENAI_MODEL,
            "text": response.output_text,
            "diagnosis": diagnosis,
            "note": None,
        }
    except Exception as exc:  # noqa: BLE001 - external provider failures must preserve fallback behavior
        return {
            "mode": "explainable-fallback",
            "model": None,
            "text": fallback,
            "diagnosis": diagnosis,
            "note": f"LLM analysis was unavailable, so RepoScope used its local explainable summary ({type(exc).__name__}).",
        }
