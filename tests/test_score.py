"""Tests for the scoring logic. These run offline - no internet needed."""

from datetime import datetime, timezone

from vigilance.score import score_repo, freshness_points

# A fixed "current time" so tests always give the same answer.
NOW = datetime(2024, 1, 5, tzinfo=timezone.utc)


def make_repo(**overrides):
    """Start from a healthy repo, then override fields for each test."""
    repo = {
        "pushed_at": "2024-01-04T00:00:00Z",
        "archived": False,
        "license": {"key": "mit"},
        "description": "A test repo",
        "has_issues": True,
    }
    repo.update(overrides)
    return repo


def test_perfect_repo_scores_100():
    result = score_repo(make_repo(), now=NOW)
    assert result["total"] == 100


def test_archived_repo_loses_20_points():
    result = score_repo(make_repo(archived=True), now=NOW)
    assert result["breakdown"]["not_archived"] == 0
    assert result["total"] == 80


def test_stale_repo_has_zero_freshness():
    result = score_repo(make_repo(pushed_at="2020-01-01T00:00:00Z"), now=NOW)
    assert result["breakdown"]["freshness"] == 0


def test_missing_license_and_description():
    result = score_repo(make_repo(license=None, description=None), now=NOW)
    assert result["breakdown"]["has_license"] == 0
    assert result["breakdown"]["has_description"] == 0
    assert result["total"] == 75


def test_freshness_buckets():
    assert freshness_points("2024-01-04T00:00:00Z", NOW) == 40   # 1 day ago
    assert freshness_points("2023-12-20T00:00:00Z", NOW) == 30   # 16 days ago
    assert freshness_points("2023-11-01T00:00:00Z", NOW) == 20   # ~65 days ago
    assert freshness_points("2023-03-01T00:00:00Z", NOW) == 10   # ~10 months
    assert freshness_points("2022-01-01T00:00:00Z", NOW) == 0    # 2 years

def test_popular_repo_gets_bonus():
    from vigilance.score import popularity_points
    assert popularity_points(5000) == 15
    assert popularity_points(250) == 8
    assert popularity_points(10) == 0


def test_stars_add_to_total():
    result = score_repo(make_repo(stargazers_count=9000), now=NOW)
    assert result["breakdown"]["popularity"] == 15
    assert result["total"] == 115