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
FIELDNAMES = ["repo", *FEATURE_COLUMNS, *EVIDENCE_COLUMNS, "label"]


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
) -> tuple[int, list[tuple[str, str]], int]:
    rows_by_repo = load_existing(output) if resume else {}
    existing_count = len(rows_by_repo)
    pending = [repo for repo in repositories if repo not in rows_by_repo]
    if limit is not None:
        pending = pending[: max(0, limit)]

    failures: list[tuple[str, str]] = []
    completed_since_checkpoint = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(_collect_one, repo): repo for repo in pending}
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
    parser.add_argument("--workers", type=int, default=4, help="Concurrent repository workers (default: 4).")
    parser.add_argument("--resume", action="store_true", help="Keep existing rows and collect only missing repositories.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of new repositories to collect this run.")
    parser.add_argument("--checkpoint-every", type=int, default=25, help="Persist partial progress after this many successful repositories.")
    args = parser.parse_args()

    repositories = load_repositories(Path(args.repos))
    collected, failures, previous = collect(
        repositories,
        Path(args.output),
        workers=args.workers,
        resume=args.resume,
        limit=args.limit,
        checkpoint_every=args.checkpoint_every,
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
