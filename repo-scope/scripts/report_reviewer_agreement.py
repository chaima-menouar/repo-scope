from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

LABELS = ("healthy", "watch", "risky")


def _load(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("repo") or "").strip()]


def _cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float | None:
    if len(labels_a) != len(labels_b):
        raise ValueError("Reviewer label vectors must have the same length.")
    if not labels_a:
        return None

    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum((counts_a[label] / n) * (counts_b[label] / n) for label in LABELS)
    if expected == 1.0:
        return 1.0 if observed == 1.0 else None
    return (observed - expected) / (1.0 - expected)


def build_report(path: Path) -> dict[str, object]:
    rows = _load(path)
    by_reviewer: dict[str, dict[str, str]] = defaultdict(dict)
    by_repo: dict[str, dict[str, str]] = defaultdict(dict)

    duplicate_decisions: list[str] = []
    invalid_labels: list[str] = []
    for row in rows:
        repo = (row.get("repo") or "").strip()
        reviewer = (row.get("reviewer") or "").strip()
        label = (row.get("human_label") or "").strip()
        if not repo or not reviewer:
            continue
        if label not in LABELS:
            invalid_labels.append(f"{repo}:{reviewer}:{label}")
            continue
        if repo in by_reviewer[reviewer]:
            duplicate_decisions.append(f"{repo}:{reviewer}")
        by_reviewer[reviewer][repo] = label
        by_repo[repo][reviewer] = label

    pairwise: list[dict[str, object]] = []
    for reviewer_a, reviewer_b in combinations(sorted(by_reviewer), 2):
        shared = sorted(set(by_reviewer[reviewer_a]) & set(by_reviewer[reviewer_b]))
        labels_a = [by_reviewer[reviewer_a][repo] for repo in shared]
        labels_b = [by_reviewer[reviewer_b][repo] for repo in shared]
        agreements = sum(a == b for a, b in zip(labels_a, labels_b))
        pairwise.append(
            {
                "reviewer_a": reviewer_a,
                "reviewer_b": reviewer_b,
                "shared_repositories": len(shared),
                "agreement_count": agreements,
                "raw_agreement": round(agreements / len(shared), 6) if shared else None,
                "cohen_kappa": (
                    round(value, 6) if (value := _cohen_kappa(labels_a, labels_b)) is not None else None
                ),
            }
        )

    repos_multi = {repo: decisions for repo, decisions in by_repo.items() if len(decisions) >= 2}
    repos_with_disagreement = {
        repo: decisions for repo, decisions in repos_multi.items() if len(set(decisions.values())) > 1
    }
    reviewer_counts = {reviewer: len(decisions) for reviewer, decisions in sorted(by_reviewer.items())}

    return {
        "decision_rows": len(rows),
        "reviewers": len(by_reviewer),
        "reviewer_decision_counts": reviewer_counts,
        "repositories_reviewed": len(by_repo),
        "repositories_with_multiple_reviewers": len(repos_multi),
        "repositories_with_disagreement": len(repos_with_disagreement),
        "pairwise_reviewer_agreement": pairwise,
        "duplicate_reviewer_repo_decisions": duplicate_decisions,
        "invalid_labels": invalid_labels,
        "status": (
            "ready_for_inter_reviewer_analysis"
            if repos_multi and any(item["shared_repositories"] > 0 for item in pairwise)
            else "insufficient_overlap"
        ),
        "note": (
            "Cohen's kappa is computed only for reviewer pairs with shared repositories. "
            "This report audits human-label reliability and does not promote the model."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report inter-reviewer agreement for RepoScope human validation.")
    parser.add_argument("--decisions", default="data/repo_risk_human_review_decisions.csv")
    parser.add_argument("--output", default="data/repo_risk_human_reviewer_agreement.json")
    args = parser.parse_args()

    report = build_report(Path(args.decisions))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
