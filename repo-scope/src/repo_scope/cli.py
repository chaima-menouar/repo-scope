"""Command-line interface for RepoScope."""
from __future__ import annotations

import argparse
import json
import sys

from repo_scope.fetch.github_api import GitHubAPIError
from repo_scope.profile import RepoProfile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repo-scope", description="Analyze GitHub repository health.")
    parser.add_argument("repo", help="Repository slug in owner/repo form")
    parser.add_argument("--html", help="Write a standalone HTML report")
    parser.add_argument("--json", dest="json_path", help="Write a JSON report")
    parser.add_argument("--no-cache", action="store_true", help="Bypass local API cache")
    parser.add_argument("--stdout", action="store_true", help="Print the analysis JSON to stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = RepoProfile(args.repo, use_cache=not args.no_cache)
    except (ValueError, GitHubAPIError) as exc:
        print(f"RepoScope error: {exc}", file=sys.stderr)
        return 2

    if not args.html and not args.json_path and not args.stdout:
        args.html = f"{profile.owner}-{profile.repo}-report.html"

    if args.html:
        profile.to_html(args.html)
        print(f"HTML report: {args.html}")
    if args.json_path:
        profile.to_json(args.json_path)
        print(f"JSON report: {args.json_path}")
    if args.stdout:
        print(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
