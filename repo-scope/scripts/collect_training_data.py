from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from repo_scope.fetch import github_api
from repo_scope.ml.training import FEATURE_COLUMNS, feature_row
from repo_scope.profile import RepoProfile

EVIDENCE_COLUMNS = ["archived", "latest_release_age_days", "latest_release_at"]


def load_repositories(path: Path) -> list[str]:
    repositories: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        repositories.append(line)
    return repositories


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


def _collect_one(repo: str) -> dict:
    profile = RepoProfile(repo)
    release_age, released_at = _release_evidence(profile.owner, profile.repo)
    return {
        "repo": repo,
        **feature_row(profile.stats),
        "archived": int(bool(profile.raw["repo_info"].get("archived"))),
        "latest_release_age_days": "" if release_age is None else release_age,
        "latest_release_at": released_at,
        "label": "",
    }


def collect(
    repositories: list[str],
    output: Path,
    *,
    workers: int = 4,
) -> tuple[int, list[tuple[str, str]]]:
    rows_by_repo: dict[str, dict] = {}
    failures: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(_collect_one, repo): repo for repo in repositories}
        for future in as_completed(futures):
            repo = futures[future]
            try:
                rows_by_repo[repo] = future.result()
                print(f"collected {repo}", flush=True)
            except Exception as exc:  # keep a long batch useful even if one repository fails
                failures.append((repo, str(exc)))
                print(f"failed {repo}: {exc}", flush=True)

    rows = [rows_by_repo[repo] for repo in repositories if repo in rows_by_repo]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo", *FEATURE_COLUMNS, *EVIDENCE_COLUMNS, "label"])
        writer.writeheader()
        writer.writerows(rows)

    return len(rows), failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect RepoScope ML feature snapshots from public repositories.")
    parser.add_argument("--repos", default="data/seed_repositories.txt")
    parser.add_argument("--output", default="data/repo_risk_unlabelled.csv")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent repository workers (default: 4).")
    args = parser.parse_args()

    repos_path = Path(args.repos)
    output_path = Path(args.output)
    repositories = load_repositories(repos_path)
    collected, failures = collect(repositories, output_path, workers=args.workers)

    print(f"wrote {collected} rows to {output_path}")
    if failures:
        print(f"{len(failures)} repositories failed")
        for repo, reason in failures:
            print(f"- {repo}: {reason}")

    if not collected:
        raise SystemExit("No repository snapshots were collected.")


if __name__ == "__main__":
    main()
