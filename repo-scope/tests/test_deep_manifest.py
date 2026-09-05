from __future__ import annotations

import csv

from scripts.build_deep_manifest import build_manifest


def test_manifest_preserves_active_archived_and_language_diversity(tmp_path):
    catalog = tmp_path / "catalog.csv"
    output = tmp_path / "manifest.txt"
    rows = []
    languages = ["Python", "Go", "TypeScript", "Java"]
    for index in range(40):
        rows.append(
            {
                "repo": f"active/repo-{index:02d}",
                "language": languages[index % len(languages)],
                "stars": [5, 30, 120, 700, 2000, 9000][index % 6],
                "archived": 0,
            }
        )
    for index in range(20):
        rows.append(
            {
                "repo": f"archived/repo-{index:02d}",
                "language": languages[index % len(languages)],
                "stars": [5, 30, 120, 700, 2000, 9000][index % 6],
                "archived": 1,
            }
        )

    with catalog.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repo", "language", "stars", "archived"])
        writer.writeheader()
        writer.writerows(rows)

    result = build_manifest(catalog, output, target=20, archived_fraction=0.20)
    selected = output.read_text(encoding="utf-8").splitlines()

    assert result["manifest_rows"] == 20
    assert len(selected) == len(set(selected)) == 20
    assert sum(repo.startswith("archived/") for repo in selected) == 4
    assert sum(repo.startswith("active/") for repo in selected) == 16

    by_repo = {row["repo"]: row for row in rows}
    selected_languages = {by_repo[repo]["language"] for repo in selected}
    assert selected_languages == set(languages)
