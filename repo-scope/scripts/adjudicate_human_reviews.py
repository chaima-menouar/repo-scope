from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

ALLOWED_LABELS = {"healthy", "watch", "risky"}
DECISION_COLUMNS = ["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"]
OUTPUT_COLUMNS = ["repo", "human_label", "review_notes", "reviewer", "reviewed_at_utc"]


def load_decisions(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    valid: list[dict[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for row in rows:
        repo = (row.get("repo") or "").strip()
        label = (row.get("human_label") or "").strip()
        reviewer = (row.get("reviewer") or "").strip()
        if not repo:
            continue
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Invalid human label for {repo}: {label!r}")
        if not reviewer:
            raise ValueError(f"Missing reviewer for {repo}")
        pair = (repo, reviewer)
        if pair in seen_pairs:
            raise ValueError(f"Duplicate independent decision for {repo} by reviewer {reviewer}")
        seen_pairs.add(pair)
        valid.append({column: (row.get(column) or "").strip() for column in DECISION_COLUMNS})
    return valid


def adjudicate(decisions: list[dict[str, str]], *, min_reviewers: int = 2) -> tuple[list[dict[str, str]], dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in decisions:
        grouped[row["repo"]].append(row)

    resolved: list[dict[str, str]] = []
    disagreements: list[dict[str, object]] = []
    insufficient: list[str] = []

    for repo in sorted(grouped):
        rows = grouped[repo]
        if len(rows) < min_reviewers:
            insufficient.append(repo)
            continue
        counts = Counter(row["human_label"] for row in rows)
        top_count = max(counts.values())
        winners = sorted(label for label, count in counts.items() if count == top_count)
        if len(winners) != 1:
            disagreements.append(
                {
                    "repo": repo,
                    "labels": dict(sorted(counts.items())),
                    "reviewers": sorted(row["reviewer"] for row in rows),
                    "reason": "no_unique_majority",
                }
            )
            continue

        winner = winners[0]
        winning_rows = [row for row in rows if row["human_label"] == winner]
        if len(winning_rows) <= len(rows) / 2:
            disagreements.append(
                {
                    "repo": repo,
                    "labels": dict(sorted(counts.items())),
                    "reviewers": sorted(row["reviewer"] for row in rows),
                    "reason": "no_strict_majority",
                }
            )
            continue

        notes = " | ".join(f"{row['reviewer']}: {row['review_notes']}" for row in winning_rows)
        reviewers = "+".join(sorted(row["reviewer"] for row in rows))
        reviewed_at = max((row["reviewed_at_utc"] for row in rows if row["reviewed_at_utc"]), default="")
        resolved.append(
            {
                "repo": repo,
                "human_label": winner,
                "review_notes": f"adjudicated majority; {notes}",
                "reviewer": f"adjudicated:{reviewers}",
                "reviewed_at_utc": reviewed_at,
            }
        )

    report = {
        "decision_rows": len(decisions),
        "repositories_with_decisions": len(grouped),
        "adjudicated_repositories": len(resolved),
        "insufficient_reviewer_repositories": len(insufficient),
        "disagreement_repositories": len(disagreements),
        "insufficient_repositories": insufficient,
        "disagreements": disagreements,
        "minimum_reviewers": min_reviewers,
        "note": (
            "Only repositories with a strict majority from at least the configured number of independent reviewers "
            "are written to the durable adjudicated human-label registry. Original reviewer decisions remain preserved."
        ),
    }
    return resolved, report


def write_labels(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Adjudicate independent RepoScope human-review decisions.")
    parser.add_argument("--decisions", default="data/repo_risk_human_review_decisions.csv")
    parser.add_argument("--output", default="data/repo_risk_human_labels.csv")
    parser.add_argument("--min-reviewers", type=int, default=2)
    args = parser.parse_args()

    decisions = load_decisions(Path(args.decisions))
    labels, report = adjudicate(decisions, min_reviewers=max(2, args.min_reviewers))
    write_labels(Path(args.output), labels)
    print(report)


if __name__ == "__main__":
    main()
