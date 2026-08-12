"""Read real PR + review history from GitHub and turn it into ReviewEvents."""

import hashlib
import json
import os
from datetime import datetime

import requests

from .models import ReviewEvent, PRMeta

GITHUB_API = "https://api.github.com"
CACHE_DIR = ".vigilance_cache"

AI_BOT_LOGINS = {
    "coderabbitai[bot]",
    "github-actions[bot]",
    "sonarcloud[bot]",
    "dependabot[bot]",
    "codecov[bot]",
    "sourcery-ai[bot]",
    "deepsource-autofix[bot]",
    "sonarqubecloud[bot]",
}


def _headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _cache_path(url, params):
    key = url + "?" + json.dumps(params or {}, sort_keys=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, digest + ".json")


def _get(url, params=None):
    path = _cache_path(url, params)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            pass

    response = requests.get(url, headers=_headers(), params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
    except OSError:
        pass
    return data


def _is_bot(user):
    if not user:
        return False
    if user.get("type") == "Bot":
        return True
    return user.get("login") in AI_BOT_LOGINS


def _parse_time(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")


def fetch_review_data(owner, repo, max_prs=40):
    base = GITHUB_API + "/repos/" + owner + "/" + repo
    pulls = _get(
        base + "/pulls",
        params={
            "state": "all",
            "per_page": min(max_prs, 100),
            "sort": "created",
            "direction": "desc",
        },
    )

    data = []
    for pull in pulls[:max_prs]:
        number = pull["number"]

        detail = _get(base + "/pulls/" + str(number))
        pr_meta = PRMeta(
            additions=detail.get("additions", 0),
            deletions=detail.get("deletions", 0),
            changed_files=detail.get("changed_files", 0),
        )

        comments = _get(base + "/pulls/" + str(number) + "/comments",
                        params={"per_page": 100})
        inline_by_review = {}
        for comment in comments:
            review_id = comment.get("pull_request_review_id")
            if review_id is not None:
                inline_by_review[review_id] = inline_by_review.get(review_id, 0) + 1

        reviews_json = _get(base + "/pulls/" + str(number) + "/reviews",
                            params={"per_page": 100})
        reviews = []
        for review in reviews_json:
            submitted = review.get("submitted_at")
            if not submitted:
                continue
            user = review.get("user") or {}
            reviews.append(
                ReviewEvent(
                    reviewer=user.get("login", "unknown"),
                    is_bot=_is_bot(user),
                    state=review.get("state", ""),
                    submitted_at=_parse_time(submitted),
                    inline_comments=inline_by_review.get(review.get("id"), 0),
                )
            )
        if reviews:
            data.append((reviews, pr_meta))
    return data
