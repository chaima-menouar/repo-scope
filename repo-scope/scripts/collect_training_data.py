from __future__ import annotations

import argparse
import csv
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


def collect(repositories: list[str], output: Path) -> tuple[int, list[tuple[str, str]]]:
    rows: list[dict] = []
    failures: list[tuple[str, str]] = []

    for repo in repositories:
        try:
            profile = RepoProfile(repo)
            release_age, released_at = _release_evidence(profile.owner, profile.repo)
            row = {
                "repo": repo,
                **feature_row(profile.stats),
                "archived": int(bool(profile.raw["repo_info"].get("archived"))),
                "latest_release_age_days": "" if release_age is None else release_age,
                "latest_release_at": released_at,
                "label": "",
            }
            rows.append(row)
            print(f"collected {repo}")
        except Exception as exc:  # keep a long batch useful even if one repository fails
            failures.append((repo, str(exc)))
            print(f"failed {repo}: {exc}")

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
    args = parser.parse_args()

    repos_path = Path(args.repos)
    output_path = Path(args.output)
    repositories = load_repositories(repos_path)
    collected, failures = collect(repositories, output_path)

    print(f"wrote {collected} rows to {output_path}")
    if failures:
        print(f"{len(failures)} repositories failed")
        for repo, reason in failures:
            print(f"- {repo}: {reason}")

    if not collected:
        raise SystemExit("No repository snapshots were collected.")


if __name__ == "__main__":
    main()
