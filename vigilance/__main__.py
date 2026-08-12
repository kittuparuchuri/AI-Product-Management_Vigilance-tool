"""CLI: python -m vigilance <owner>/<repo> [<owner>/<repo> ...]

Score one repo (with a full breakdown), or several at once (ranked table).
Examples:
  python -m vigilance psf/requests
  python -m vigilance psf/requests facebook/react octocat/Hello-World
"""

import sys

import requests

from .github_client import fetch_repo
from .score import score_repo


def score_one(target):
    """Fetch and score a single 'owner/repo'. Returns (target, result) or None."""
    owner, name = target.split("/", 1)
    try:
        repo = fetch_repo(owner, name)
    except requests.HTTPError as error:
        status = error.response.status_code
        if status == 404:
            print(f"Repo not found: {target}. Check the spelling.")
        elif status == 403:
            print("GitHub rate limit hit. Wait a bit and try again.")
        else:
            print(f"GitHub returned an error ({status}) for {target}.")
        return None
    except requests.RequestException:
        print(f"Could not reach GitHub for {target}.")
        return None
    return target, score_repo(repo)


def print_breakdown(target, result):
    """Detailed view, used when scoring a single repo."""
    print(f"Vigilance score for {target}: {result['total']}/115")
    for component, points in result["breakdown"].items():
        print(f"  {component:16} {points}")


def print_ranked_table(scored):
    """Ranked summary, used when scoring several repos."""
    scored.sort(key=lambda pair: pair[1]["total"], reverse=True)
    print(f"{'Rank':<5}{'Score':<9}Repository")
    for rank, (target, result) in enumerate(scored, start=1):
        score_text = f"{result['total']}/115"
        print(f"{rank:<5}{score_text:<9}{target}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: python -m vigilance <owner>/<repo> [<owner>/<repo> ...]")
        print("Example: python -m vigilance psf/requests facebook/react")
        return 1

    scored = []
    for target in argv:
        if "/" not in target:
            print(f"Skipping '{target}': use the <owner>/<repo> format.")
            continue
        outcome = score_one(target)
        if outcome is not None:
            scored.append(outcome)

    if not scored:
        return 1

    if len(scored) == 1:
        print_breakdown(*scored[0])
    else:
        print_ranked_table(scored)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())