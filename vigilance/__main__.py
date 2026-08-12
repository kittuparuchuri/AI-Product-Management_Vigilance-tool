"""Command-line entry point.

Run it with:  python -m vigilance <owner>/<repo>
Example:      python -m vigilance psf/requests
"""

import sys

import requests

from .github_client import fetch_repo
from .score import score_repo


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv

    if not argv or "/" not in argv[0]:
        print("Usage: python -m vigilance <owner>/<repo>")
        print("Example: python -m vigilance psf/requests")
        return 1

    owner, name = argv[0].split("/", 1)

    try:
        repo = fetch_repo(owner, name)
    except requests.HTTPError as error:
        status = error.response.status_code
        if status == 404:
            print(f"Repo not found: {owner}/{name}. Check the spelling.")
        elif status == 403:
            print("GitHub rate limit hit. Wait a bit and try again.")
        else:
            print(f"GitHub returned an error ({status}).")
        return 1
    except requests.RequestException:
        print("Could not reach GitHub. Check your internet connection.")
        return 1

    result = score_repo(repo)
    print(f"Vigilance score for {owner}/{name}: {result['total']}/115")
    for component, points in result["breakdown"].items():
        print(f"  {component:16} {points}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
