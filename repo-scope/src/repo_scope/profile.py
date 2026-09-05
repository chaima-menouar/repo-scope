"""Public orchestration API for RepoScope."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import re

from repo_scope.analysis.alerts import generate_alerts
from repo_scope.analysis.cloud import cloud_readiness
from repo_scope.analysis.health import bus_factor, compute_health_score, health_label
from repo_scope.analysis.stats import compute_stats
from repo_scope.analysis.timeseries import commits_over_time, issues_opened_vs_closed
from repo_scope.fetch import github_api
from repo_scope.insights import build_smart_summary
from repo_scope.ml.inference import predict_risk


class RepoProfile:
    """Fetch, normalize and analyze a GitHub repository."""

    def __init__(self, repo_slug: str, use_cache: bool = True):
        slug = repo_slug.strip().strip("/")
        parts = slug.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("repo_slug must use the form 'owner/repo'.")
        if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
            raise ValueError("owner and repository names may only contain letters, numbers, dots, underscores and hyphens.")

        self.repo_slug = slug
        self.owner, self.repo = parts
        self.use_cache = use_cache
        self.generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        self.raw = self._fetch()
        self.stats = compute_stats(
            self.raw["repo_info"],
            self.raw["commits"],
            self.raw["contributors"],
            self.raw["languages"],
            issues=self.raw["issues"],
            pulls=self.raw["pull_requests"],
            paths=self.raw["paths"],
        )

        factor = bus_factor(self.raw["contributors"])
        self.stats["contributors"]["bus_factor"] = factor
        self.stats["cloud_readiness"] = cloud_readiness(self.stats["signals"])
        self.stats["ml_risk"] = predict_risk(self.stats)
        provisional_alerts = generate_alerts(self.stats, self.raw["commits"], self.raw["issues"])
        score = compute_health_score(self.stats, provisional_alerts)
        self.stats["health"] = {
            "score": score,
            "label": health_label(score),
            "bus_factor": factor,
        }
        self.alerts = provisional_alerts
        self.timeseries = {
            "commits": commits_over_time(self.raw["commits"]),
            "issues": issues_opened_vs_closed(self.raw["issues"]),
        }
        self.smart_summary = build_smart_summary({"stats": self.stats})

    def _fetch(self) -> dict:
        repo_info = github_api.get_repo_info(self.owner, self.repo, use_cache=self.use_cache)
        default_branch = repo_info.get("default_branch") or "main"
        return {
            "repo_info": repo_info,
            "commits": github_api.get_commits(self.owner, self.repo, use_cache=self.use_cache),
            "contributors": github_api.get_contributors(self.owner, self.repo, use_cache=self.use_cache),
            "issues": github_api.get_issues(self.owner, self.repo, use_cache=self.use_cache),
            "pull_requests": github_api.get_pull_requests(self.owner, self.repo, use_cache=self.use_cache),
            "languages": github_api.get_languages(self.owner, self.repo, use_cache=self.use_cache),
            "paths": github_api.get_repository_paths(
                self.owner,
                self.repo,
                default_branch,
                use_cache=self.use_cache,
            ),
        }

    def to_dict(self, include_raw: bool = False) -> dict:
        payload = {
            "repo_slug": self.repo_slug,
            "generated_at": self.generated_at,
            "stats": self.stats,
            "alerts": [asdict(alert) for alert in self.alerts],
            "timeseries": self.timeseries,
            "smart_summary": self.smart_summary,
        }
        if include_raw:
            payload["raw"] = self.raw
        return payload

    def to_html(self, path: str) -> None:
        from repo_scope.report.renderer import render_html

        render_html(self, path)

    def to_json(self, path: str) -> None:
        from repo_scope.report.renderer import render_json

        render_json(self, path)
