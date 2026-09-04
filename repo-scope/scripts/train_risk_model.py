from __future__ import annotations

import argparse
import json

from repo_scope.ml.training import train_from_csv

parser = argparse.ArgumentParser(description="Train RepoScope repository-risk classifier from labelled snapshots.")
parser.add_argument("csv")
parser.add_argument("--output", default="models/repo_risk.joblib")
args = parser.parse_args()
print(json.dumps(train_from_csv(args.csv, args.output), indent=2))
