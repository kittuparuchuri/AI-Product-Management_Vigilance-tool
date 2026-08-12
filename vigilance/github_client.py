"""Talk to GitHub's public API using the requests library."""

import requests

GITHUB_API = "https://api.github.com"


def fetch_repo(owner, name):
    """Fetch one repository's public data from GitHub.

    Raises requests.HTTPError if the repo is missing or GitHub says no.
    """
    url = f"{GITHUB_API}/repos/{owner}/{name}"
    response = requests.get(
        url,
        headers={"Accept": "application/vnd.github+json"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
