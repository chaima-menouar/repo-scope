"""Example: profile a public repo end-to-end (once implemented)."""
from repo_scope import RepoProfile

profile = RepoProfile("facebook/react")
profile.to_html("react_report.html")
profile.to_json("react_report.json")
