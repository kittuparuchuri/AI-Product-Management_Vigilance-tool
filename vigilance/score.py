"""Turn raw GitHub repo data into a 0-100 'vigilance' score.

The score rewards repositories that look actively cared for:
recent activity, not archived, has a license, has a description,
and has its issue tracker turned on.
"""

from datetime import datetime, timezone


def _parse_github_time(timestamp):
    """GitHub sends times like '2024-05-01T12:34:56Z'. Convert to a datetime."""
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )


def popularity_points(stars):
    """Up to 15 bonus points based on how many stars the repo has."""
    if stars >= 1000:
        return 15
    if stars >= 100:
        return 8
    return 0

def freshness_points(pushed_at, now):
    """Up to 40 points, based on how recently the repo was pushed to."""
    last_push = _parse_github_time(pushed_at)
    days_since = (now - last_push).days
    if days_since <= 7:
        return 40
    if days_since <= 30:
        return 30
    if days_since <= 90:
        return 20
    if days_since <= 365:
        return 10
    return 0


def score_repo(repo, now=None):
    """Score one repo dict (as returned by the GitHub API).

    Returns a dict: {"total": int, "breakdown": {component: points}}.
    Pass `now` in tests to make the result deterministic.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    breakdown = {
        "freshness": freshness_points(repo["pushed_at"], now),
        "not_archived": 0 if repo.get("archived") else 20,
        "has_license": 15 if repo.get("license") else 0,
        "has_description": 10 if repo.get("description") else 0,
        "issues_enabled": 15 if repo.get("has_issues") else 0,
        "popularity": popularity_points(repo.get("stargazers_count", 0)),
    }
    return {"total": sum(breakdown.values()), "breakdown": breakdown}
