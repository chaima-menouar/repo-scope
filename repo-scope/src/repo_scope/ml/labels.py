"""Conservative weak-label policy for the experimental ML baseline."""
from __future__ import annotations

HEALTHY_RELEASE_MAX_DAYS = 150
WATCH_RELEASE_MIN_DAYS = 180


def assign_weak_label(row: dict[str, object]) -> tuple[str, str, str] | None:
    """Assign a label only when independent maintenance evidence is available."""
    archived = str(row.get("archived", "")).strip() == "1"
    release_age_raw = str(row.get("latest_release_age_days", "")).strip()

    if archived:
        return "risky", "github_archived_flag", "GitHub marks this repository as archived."

    if not release_age_raw:
        return None

    try:
        release_age = int(float(release_age_raw))
    except ValueError:
        return None

    if release_age <= HEALTHY_RELEASE_MAX_DAYS:
        return (
            "healthy",
            "recent_release_evidence",
            f"Latest GitHub release is {release_age} days old.",
        )
    if release_age >= WATCH_RELEASE_MIN_DAYS:
        return (
            "watch",
            "stale_release_evidence",
            f"Latest GitHub release is {release_age} days old; repository is not archived.",
        )

    return None
