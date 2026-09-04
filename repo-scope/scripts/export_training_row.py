from __future__ import annotations

import argparse
import csv
from pathlib import Path

from repo_scope.ml.training import FEATURE_COLUMNS, feature_row
from repo_scope.profile import RepoProfile

parser = argparse.ArgumentParser(description="Append an analyzed repository snapshot to a training CSV.")
parser.add_argument("repo")
parser.add_argument("--csv", default="data/repo_risk_training.csv")
parser.add_argument("--label", default="", help="Optional human label, e.g. healthy/watch/risky")
args = parser.parse_args()

profile = RepoProfile(args.repo)
row = feature_row(profile.stats)
row["repo"] = args.repo
row["label"] = args.label
path = Path(args.csv)
path.parent.mkdir(parents=True, exist_ok=True)
exists = path.exists()
with path.open("a", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["repo", *FEATURE_COLUMNS, "label"])
    if not exists:
        writer.writeheader()
    writer.writerow(row)
print(path)
