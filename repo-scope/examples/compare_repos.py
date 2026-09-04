"""Example: compare two repos side by side (once analysis/compare.py is implemented)."""
from repo_scope import RepoProfile
from repo_scope.analysis.compare import compare_repos

a = RepoProfile("facebook/react")
b = RepoProfile("vuejs/core")
diff = compare_repos(a.stats, b.stats)
print(diff)
