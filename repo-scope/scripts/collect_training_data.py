from __future__ import annotations

import argparse
import csv
from pathlib import Path

from repo_scope.ml.training import FEATURE_COLUMNS, feature_row
from repo_scope.profile import RepoProfile


def load_repositories(path: Path) -> list[str]:
    repositories: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        repositories.append(line)
    return repositories


def collect(repositories: list[str], output: Path) -> tuple[int, list[tuple[str, str]]]:
    rows: list[dict] = []
    failures: list[tuple[str, str]] = []

    for repo in repositories:
        try:
            profile = RepoProfile(repo)
            row = {"repo": repo, **feature_row(profile.stats), "label": ""}
            rows.append(row)
            print(f"collected {repo}")
        except Exception as exc:  # keep a long batch useful even if one repository fails
            failures.append((repo, str(exc)))
            print(f"failed {repo}: {exc}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo", *FEATURE_COLUMNS, "label"])
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
