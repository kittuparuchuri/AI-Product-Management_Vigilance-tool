"""
Reviewer Vigilance Tracker
===========================

Problem this addresses (in plain terms):
When an AI reviews a pull request first and gives it a green light,
human reviewers start trusting that signal more than they should.
Over weeks and months, they read less carefully, leave fewer comments,
and approve faster -- not because the code got better, but because
they've stopped really checking. This is "automation complacency,"
well documented in aviation and radiology, now showing up in AI-assisted
code review.

What this tool does:
Pulls real pull request + review history from a public GitHub repo,
identifies which reviews were AI-bot reviews vs human reviews, and
computes a per-reviewer "vigilance score" over time:

  - Comment density: comments left per 100 lines changed
  - Rubber-stamp rate: % of approvals with 0 comments, submitted
    quickly after an AI bot already reviewed the same PR
  - Review latency: how long they spend before approving, relative
    to PR size
  - Trend: is their vigilance score declining over time?

This is a heuristic, not a certified psychological instrument -- it's
a practical proxy built from data every team already has in GitHub.
"""

import requests
import time
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

GITHUB_API = "https://api.github.com"

# Known AI/bot reviewer login patterns (extend as needed)
AI_BOT_LOGINS = {
    "coderabbitai", "coderabbitai[bot]", "github-actions[bot]",
    "copilot", "copilot-pull-request-reviewer[bot]",
    "sourcery-ai[bot]", "codiumai-pr-agent[bot]", "deepsource-autofix[bot]",
    "sonarcloud[bot]", "codecov[bot]", "greptile-apps[bot]", "cursor[bot]",
    "graphite-app[bot]", "korbit-ai[bot]", "bugbot[bot]",
}


def is_ai_bot(login: str) -> bool:
    login_lower = login.lower()
    if login_lower in AI_BOT_LOGINS:
        return True
    # catch-all heuristics for bot naming conventions
    return login_lower.endswith("[bot]") and any(
        kw in login_lower for kw in ["ai", "review", "bot", "copilot", "code"]
    )


@dataclass
class ReviewEvent:
    pr_number: int
    reviewer: str
    is_bot: bool
    state: str            # APPROVED, COMMENTED, CHANGES_REQUESTED
    submitted_at: datetime
    body_length: int
    comment_count: int    # inline comments by this reviewer on this PR


@dataclass
class PRMeta:
    number: int
    additions: int
    deletions: int
    changed_files: int
    created_at: datetime


class GitHubReviewFetcher:
    """Pulls PR + review data from the public GitHub REST API.
    Works unauthenticated (rate-limited to 60 req/hour) or with a
    token for higher limits -- pass token=... if you have one."""

    def __init__(self, owner: str, repo: str, token: str = None):
        self.owner = owner
        self.repo = repo
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.session.headers.update(headers)

    def _get(self, path: str, params: dict = None):
        url = f"{GITHUB_API}{path}"
        resp = self.session.get(url, params=params or {})
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = resp.headers.get("X-RateLimit-Reset")
            raise RuntimeError(
                f"GitHub API rate limit hit. Resets at epoch {reset}. "
                f"Pass a token= to GitHubReviewFetcher for a higher limit."
            )
        resp.raise_for_status()
        return resp.json()

    def fetch_recent_closed_prs(self, max_prs: int = 20) -> list:
        prs = self._get(
            f"/repos/{self.owner}/{self.repo}/pulls",
            params={"state": "closed", "per_page": max_prs, "sort": "updated", "direction": "desc"},
        )
        return prs

    def fetch_pr_meta(self, pr_number: int) -> PRMeta:
        data = self._get(f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}")
        return PRMeta(
            number=pr_number,
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changed_files=data.get("changed_files", 0),
            created_at=_parse_ts(data["created_at"]),
        )

    def fetch_pr_reviews(self, pr_number: int) -> list:
        reviews = self._get(f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/reviews")
        review_comments = self._get(f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/comments")

        comment_counts = defaultdict(int)
        for c in review_comments:
            comment_counts[c["user"]["login"]] += 1

        events = []
        for r in reviews:
            if r.get("state") is None or r.get("submitted_at") is None:
                continue
            login = r["user"]["login"]
            events.append(ReviewEvent(
                pr_number=pr_number,
                reviewer=login,
                is_bot=is_ai_bot(login),
                state=r["state"],
                submitted_at=_parse_ts(r["submitted_at"]),
                body_length=len(r.get("body") or ""),
                comment_count=comment_counts.get(login, 0),
            ))
        return events


def _parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
