from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from repo_scope.analysis.health import bus_factor
from repo_scope.analysis.stats import compute_stats
from repo_scope.fetch import github_api
from repo_scope.ml.training import FEATURE_COLUMNS, feature_row

EVIDENCE_COLUMNS = ["snapshot_at_utc", "archived", "latest_release_age_days", "latest_release_at"]
CONTEXT_COLUMNS = ["language", "stars", "forks", "open_issues", "size_kb", "catalog_pushed_at"]
FIELDNAMES = ["repo", *FEATURE_COLUMNS, *EVIDENCE_COLUMNS, *CONTEXT_COLUMNS, "label"]


def load_repositories(path: Path) -> list[str]:
    repositories: list[str] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line in seen:
            continue
        seen.add(line)
        repositories.append(line)
    return repositories


def load_existing(path: Path) -> dict[str, dict]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["repo"]: row for row in csv.DictReader(handle) if row.get("repo")}


def load_catalog(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None or not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["repo"]: row for row in csv.DictReader(handle) if row.get("repo")}


def _catalog_repo_info(repo: str, row: dict[str, str]) -> dict:
    owner, name = repo.split("/", 1)
    return {
        "full_name": repo,
        "name": name,
        "owner": {"login": owner},
        "archived": (row.get("archived") or "").strip().lower() in {"1", "true", "yes"},
        "created_at": row.get("created_at") or "",
        "updated_at": row.get("updated_at") or "",
        "pushed_at": row.get("pushed_at") or "",
        "default_branch": row.get("default_branch") or "main",
        "stargazers_count": int(float(row.get("stars") or 0)),
        "forks_count": int(float(row.get("forks") or 0)),
        "size": int(float(row.get("size_kb") or 0)),
        "license": None if not row.get("license") else {"spdx_id": row.get("license")},
        "topics": [value for value in (row.get("topics") or "").split("|") if value],
    }


def _release_evidence(owner: str, repo: str) -> tuple[int | None, str]:
    release = github_api.get_latest_release(owner, repo)
    if not release:
        return None, ""
    released_at = release.get("published_at") or release.get("created_at") or ""
    if not released_at:
        return None, ""
    try:
        released = datetime.fromisoformat(released_at.replace("Z", "+00:00"))
        age_days = max(0, (datetime.now(timezone.utc) - released.astimezone(timezone.utc)).days)
        return age_days, released_at
    except (TypeError, ValueError):
        return None, released_at


def _context(catalog_row: dict[str, str] | None) -> dict[str, object]:
    row = catalog_row or {}
    return {
        "language": row.get("language") or "",
        "stars": row.get("stars") or "",
        "forks": row.get("forks") or "",
        "open_issues": row.get("open_issues") or "",
        "size_kb": row.get("size_kb") or "",
        "catalog_pushed_at": row.get("pushed_at") or "",
    }


def _collect_one(repo: str, catalog_row: dict[str, str] | None = None) -> dict:
    owner, name = repo.split("/", 1)
    repo_info = _catalog_repo_info(repo, catalog_row) if catalog_row else github_api.get_repo_info(owner, name)
    default_branch = repo_info.get("default_branch") or "main"

    commits = github_api.get_commits(owner, name)
    contributors = github_api.get_contributors(owner, name)
    issues = github_api.get_issues(owner, name)
    pulls = github_api.get_pull_requests(owner, name)
    paths = github_api.get_repository_paths(owner, name, default_branch)

    stats = compute_stats(
        repo_info,
        commits,
        contributors,
        {},
        issues=issues,
        pulls=pulls,
        paths=paths,
    )
    stats["contributors"]["bus_factor"] = bus_factor(contributors)

    release_age, released_at = _release_evidence(owner, name)
    return {
        "repo": repo,
        **feature_row(stats),
        "snapshot_at_utc": datetime.now(timezone.utc).isoformat(),
        "archived": int(bool(repo_info.get("archived"))),
        "latest_release_age_days": "" if release_age is None else release_age,
        "latest_release_at": released_at,
        **_context(catalog_row),
        "label": "",
    }


def _write_rows(output: Path, repositories: list[str], rows_by_repo: dict[str, dict]) -> int:
    rows = [rows_by_repo[repo] for repo in repositories if repo in rows_by_repo]
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(output)
    return len(rows)


def collect(
    repositories: list[str],
    output: Path,
    *,
    workers: int = 4,
    resume: bool = False,
    limit: int | None = None,
    checkpoint_every: int = 25,
    catalog_rows: dict[str, dict[str, str]] | None = None,
) -> tuple[int, list[tuple[str, str]], int]:
    rows_by_repo = load_existing(output) if resume else {}
    existing_count = len(rows_by_repo)
    pending = [repo for repo in repositories if repo not in rows_by_repo]
    if limit is not None:
        pending = pending[: max(0, limit)]

    catalog_rows = catalog_rows or {}
    failures: list[tuple[str, str]] = []
    completed_since_checkpoint = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(_collect_one, repo, catalog_rows.get(repo)): repo
            for repo in pending
        }
        for future in as_completed(futures):
            repo = futures[future]
            try:
                rows_by_repo[repo] = future.result()
                completed_since_checkpoint += 1
                print(f"collected {repo}", flush=True)
                if checkpoint_every > 0 and completed_since_checkpoint >= checkpoint_every:
                    saved = _write_rows(output, repositories, rows_by_repo)
                    completed_since_checkpoint = 0
                    print(f"checkpoint saved: {saved} rows", flush=True)
            except Exception as exc:
                failures.append((repo, str(exc)))
                print(f"failed {repo}: {exc}", flush=True)

    total = _write_rows(output, repositories, rows_by_repo)
    return total, failures, existing_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect RepoScope ML feature snapshots from public repositories.")
    parser.add_argument("--repos", default="data/seed_repositories.txt")
    parser.add_argument("--output", default="data/repo_risk_unlabelled.csv")
    parser.add_argument("--catalog", default=None, help="Optional repository catalog used to avoid redundant metadata API calls.")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent repository workers (default: 4).")
    parser.add_argument("--resume", action="store_true", help="Keep existing rows and collect only missing repositories.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of new repositories to collect this run.")
    parser.add_argument("--checkpoint-every", type=int, default=25, help="Persist partial progress after this many successful repositories.")
    args = parser.parse_args()

    repositories = load_repositories(Path(args.repos))
    catalog_rows = load_catalog(Path(args.catalog)) if args.catalog else {}
    collected, failures, previous = collect(
        repositories,
        Path(args.output),
        workers=args.workers,
        resume=args.resume,
        limit=args.limit,
        checkpoint_every=args.checkpoint_every,
        catalog_rows=catalog_rows,
    )

    print(f"dataset now contains {collected} rows ({previous} existed before this run)")
    if failures:
        print(f"{len(failures)} repositories failed in this batch")
        for repo, reason in failures:
            print(f"- {repo}: {reason}")

    if not collected:
        raise SystemExit("No repository snapshots were collected.")


if __name__ == "__main__":
    main()
