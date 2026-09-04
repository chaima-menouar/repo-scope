"""Descriptive repository statistics used by the rest of RepoScope."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _days_since(value: str | None) -> int | None:
    dt = _parse_dt(value)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    return max(0, (now - dt.astimezone(timezone.utc)).days)


def _commit_date(commit: dict) -> datetime | None:
    inner = commit.get("commit", {})
    return _parse_dt(inner.get("committer", {}).get("date") or inner.get("author", {}).get("date"))


def _count_recent(commits: Iterable[dict], days: int) -> int:
    now = datetime.now(timezone.utc)
    total = 0
    for commit in commits:
        dt = _commit_date(commit)
        if dt and (now - dt.astimezone(timezone.utc)).days <= days:
            total += 1
    return total


def _signals(paths: list[str], repo_info: dict) -> dict:
    lowered = [path.lower() for path in paths]

    def any_path(*needles: str) -> bool:
        return any(any(needle in path for needle in needles) for path in lowered)

    return {
        "has_ci": any_path(".github/workflows/", ".gitlab-ci.yml", "circleci/config.yml", "jenkinsfile"),
        "has_tests": any_path("/tests/", "tests/", "/test/", "test_", ".spec.", ".test."),
        "has_license": bool(repo_info.get("license")) or any_path("license", "copying"),
        "has_contributing": any_path("contributing.md", "contributing.rst"),
        "has_readme": any(path in {"readme.md", "readme.rst", "readme"} for path in lowered),
        "has_security_policy": any_path("security.md", ".github/security"),
    }


def compute_stats(
    repo_info: dict,
    commits: list[dict],
    contributors: list[dict],
    languages: dict,
    issues: list[dict] | None = None,
    pulls: list[dict] | None = None,
    paths: list[str] | None = None,
) -> dict:
    issues = issues or []
    pulls = pulls or []
    paths = paths or []

    created = _parse_dt(repo_info.get("created_at"))
    now = datetime.now(timezone.utc)
    repo_age_days = (now - created.astimezone(timezone.utc)).days if created else None

    total_language_bytes = sum(max(0, int(v or 0)) for v in languages.values())
    top_languages = [
        {
            "name": name,
            "bytes": int(value),
            "percent": round((value / total_language_bytes * 100), 1) if total_language_bytes else 0.0,
        }
        for name, value in sorted(languages.items(), key=lambda item: item[1], reverse=True)
    ]

    sorted_contributors = sorted(contributors, key=lambda c: int(c.get("contributions", 0)), reverse=True)
    total_contributions = sum(int(c.get("contributions", 0)) for c in sorted_contributors)
    top_contributors = [
        {
            "login": c.get("login") or c.get("name") or "anonymous",
            "avatar_url": c.get("avatar_url"),
            "html_url": c.get("html_url"),
            "contributions": int(c.get("contributions", 0)),
            "share_pct": round((int(c.get("contributions", 0)) / total_contributions * 100), 1)
            if total_contributions
            else 0.0,
        }
        for c in sorted_contributors[:8]
    ]

    issue_open = sum(1 for item in issues if item.get("state") == "open")
    issue_closed = sum(1 for item in issues if item.get("state") == "closed")
    issue_total = issue_open + issue_closed
    stale_open = sum(
        1
        for item in issues
        if item.get("state") == "open" and (_days_since(item.get("created_at")) or 0) >= 90
    )

    pr_open = sum(1 for item in pulls if item.get("state") == "open")
    pr_closed = sum(1 for item in pulls if item.get("state") == "closed")
    pr_merged = sum(1 for item in pulls if item.get("merged_at"))
    pr_total = pr_open + pr_closed

    last_commit_date = None
    dates = [date for date in (_commit_date(c) for c in commits) if date]
    if dates:
        last_commit_date = max(dates).isoformat().replace("+00:00", "Z")
    elif repo_info.get("pushed_at"):
        last_commit_date = repo_info.get("pushed_at")

    return {
        "repo": {
            "full_name": repo_info.get("full_name"),
            "name": repo_info.get("name"),
            "owner": repo_info.get("owner", {}).get("login"),
            "description": repo_info.get("description"),
            "html_url": repo_info.get("html_url"),
            "homepage": repo_info.get("homepage"),
            "default_branch": repo_info.get("default_branch"),
            "visibility": repo_info.get("visibility", "public"),
            "archived": bool(repo_info.get("archived")),
            "fork": bool(repo_info.get("fork")),
            "created_at": repo_info.get("created_at"),
            "updated_at": repo_info.get("updated_at"),
            "repo_age_days": repo_age_days,
            "stars": int(repo_info.get("stargazers_count", 0)),
            "forks": int(repo_info.get("forks_count", 0)),
            "watchers": int(repo_info.get("subscribers_count", repo_info.get("watchers_count", 0))),
            "size_kb": int(repo_info.get("size", 0)),
            "topics": repo_info.get("topics", []),
        },
        "activity": {
            "sampled_commits": len(commits),
            "commits_30d": _count_recent(commits, 30),
            "commits_90d": _count_recent(commits, 90),
            "last_commit_at": last_commit_date,
            "days_since_last_commit": _days_since(last_commit_date),
        },
        "contributors": {
            "sampled_total": len(contributors),
            "total_contributions_in_sample": total_contributions,
            "top": top_contributors,
        },
        "issues": {
            "sampled_total": issue_total,
            "open": issue_open,
            "closed": issue_closed,
            "closure_rate_pct": round(issue_closed / issue_total * 100, 1) if issue_total else None,
            "stale_open_90d": stale_open,
        },
        "pull_requests": {
            "sampled_total": pr_total,
            "open": pr_open,
            "closed": pr_closed,
            "merged": pr_merged,
            "merge_rate_pct": round(pr_merged / pr_closed * 100, 1) if pr_closed else None,
        },
        "languages": top_languages,
        "signals": _signals(paths, repo_info),
        "sampling": {
            "note": "Activity, contributor, issue and PR metrics are computed from the recent GitHub API sample configured for this deployment.",
            "commit_items": len(commits),
            "contributor_items": len(contributors),
            "issue_items": len(issues),
            "pull_request_items": len(pulls),
        },
    }
