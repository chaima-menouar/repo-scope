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

    parts = [
        f"Repository health is {health.get('label', 'unrated').lower()} at {health.get('score', 0)}/100."
    ]
    days = activity.get("days_since_last_commit")
    if days is not None:
        parts.append(f"The latest sampled commit is {days} day{'s' if days != 1 else ''} old.")
    factor = contributors.get("bus_factor", 0)
    if factor:
        parts.append(f"The sampled bus factor is {factor}, indicating {'concentrated ownership' if factor <= 2 else 'broader contribution resilience'}.")
    closure = issues.get("closure_rate_pct")
    if closure is not None:
        parts.append(f"Sampled issue closure rate is {closure:.0f}%.")
    missing = [name for name, present in (("CI", signals.get("has_ci")), ("tests", signals.get("has_tests"))) if not present]
    if missing:
        parts.append("Engineering hygiene could improve around " + " and ".join(missing) + ".")
    return " ".join(parts)


def generate_ai_insight(data: dict) -> dict:
    """Use OpenAI when configured; otherwise return a deterministic explainable summary."""
    fallback = build_smart_summary(data)
    if not OPENAI_API_KEY:
        return {
            "mode": "explainable-fallback",
            "model": None,
            "text": fallback,
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
            "alerts": data.get("alerts", []),
        }
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=(
                "You are RepoScope's engineering analyst. Analyze the aggregate GitHub repository metrics below. "
                "Write 3 concise paragraphs: health diagnosis, main risk, and next engineering action. "
                "Do not invent metrics or claim access to source code. Mention that metrics are sampled where relevant.\n\n"
                + json.dumps(compact, ensure_ascii=False)
            ),
        )
        return {"mode": "openai", "model": OPENAI_MODEL, "text": response.output_text, "note": None}
    except Exception as exc:  # keep the product usable if the external AI provider fails
        return {
            "mode": "explainable-fallback",
            "model": None,
            "text": fallback,
            "note": f"LLM analysis was unavailable, so RepoScope used its local explainable summary ({type(exc).__name__}).",
        }
