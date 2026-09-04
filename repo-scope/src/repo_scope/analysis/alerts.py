"""Rule-based repository health alerts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass
class Alert:
    level: Literal["info", "warning", "critical"]
    message: str
    code: str = "general"

    def to_dict(self) -> dict:
        return asdict(self)


def generate_alerts(stats: dict, commits: list[dict] | None = None, issues: list[dict] | None = None) -> list[Alert]:
    del commits, issues  # metrics are already normalized inside stats
    alerts: list[Alert] = []
    factor = int(stats.get("contributors", {}).get("bus_factor", 0))
    contributor_count = int(stats.get("contributors", {}).get("sampled_total", 0))
    days = stats.get("activity", {}).get("days_since_last_commit")
    issue_rate = stats.get("issues", {}).get("closure_rate_pct")
    stale = int(stats.get("issues", {}).get("stale_open_90d", 0))
    signals = stats.get("signals", {})

    if stats.get("repo", {}).get("archived"):
        alerts.append(Alert("critical", "This repository is archived and should be treated as inactive.", "archived"))
    elif days is not None and days > 365:
        alerts.append(Alert("critical", f"No sampled commit activity for {days} days.", "inactive"))
    elif days is not None and days > 90:
        alerts.append(Alert("warning", f"Repository activity is stale: last sampled commit was {days} days ago.", "stale_activity"))

    if factor == 1 and contributor_count > 1:
        alerts.append(Alert("critical", "Contributor concentration is high: one person accounts for at least half of sampled contributions.", "bus_factor"))
    elif factor == 2 and contributor_count >= 4:
        alerts.append(Alert("warning", "Contributor resilience is limited: two people account for at least half of sampled contributions.", "bus_factor"))

    if issue_rate is not None and stats.get("issues", {}).get("sampled_total", 0) >= 10:
        if issue_rate < 30:
            alerts.append(Alert("critical", f"Issue closure rate is low at {issue_rate:.0f}% in the sampled window.", "issue_hygiene"))
        elif issue_rate < 55:
            alerts.append(Alert("warning", f"Issue closure rate is only {issue_rate:.0f}% in the sampled window.", "issue_hygiene"))

    if stale >= 20:
        alerts.append(Alert("warning", f"{stale} sampled open issues are at least 90 days old.", "stale_issues"))

    if not signals.get("has_ci"):
        alerts.append(Alert("warning", "No CI workflow was detected in the repository tree sample.", "ci"))
    if not signals.get("has_tests"):
        alerts.append(Alert("warning", "No obvious automated test files were detected.", "tests"))
    if not signals.get("has_license"):
        alerts.append(Alert("info", "No license was detected.", "license"))
    if not signals.get("has_contributing"):
        alerts.append(Alert("info", "No CONTRIBUTING guide was detected.", "contributing"))

    if not alerts:
        alerts.append(Alert("info", "No major health risks were detected in the sampled repository data.", "healthy"))
    return alerts
