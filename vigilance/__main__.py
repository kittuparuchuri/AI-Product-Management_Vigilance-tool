"""Command-line interface.

  python -m vigilance report --source simulate      run the pipeline on fake data
  python -m vigilance <owner>/<repo> [...]           score GitHub repos (older tool)
"""

import sys

import requests

from .github_client import fetch_repo
from .score import score_repo


def run_report(args):
    source = "simulate"
    if "--source" in args:
        i = args.index("--source")
        if i + 1 < len(args):
            source = args[i + 1]

    if source != "simulate":
        print("Unknown source " + repr(source) + ". Only simulate is available.")
        return 1

    from .simulate import simulate_drift
    from .scoring import (
        score_reviews,
        compute_vigilance_scores,
        flag_declining_reviewers,
    )

    data = simulate_drift()
    scored = []
    for reviews, pr_meta in data:
        scored += score_reviews(reviews, pr_meta)

    windows = compute_vigilance_scores(scored)
    flagged = {d.reviewer: d for d in flag_declining_reviewers(scored)}

    print("Vigilance report  (source: simulate)")
    print("=" * 52)
    for reviewer in sorted(windows):
        scores = [round(s) for s in windows[reviewer]]
        first, latest = scores[0], scores[-1]
        if reviewer in flagged:
            status = "FLAGGED (dropped " + str(round(flagged[reviewer].drop)) + ")"
        else:
            status = "ok"
        print("{:8} {:34} {:>3} -> {:<3}  {}".format(reviewer, str(scores), first, latest, status))

    print()
    names = ", ".join(sorted(flagged)) if flagged else "(none)"
    print("Flagged reviewers: " + names)
    return 0


def score_one(target):
    owner, name = target.split("/", 1)
    try:
        repo = fetch_repo(owner, name)
    except requests.HTTPError as error:
        status = error.response.status_code
        if status == 404:
            print("Repo not found: " + target + ". Check the spelling.")
        elif status == 403:
            print("GitHub rate limit hit. Wait a bit and try again.")
        else:
            print("GitHub returned an error (" + str(status) + ") for " + target + ".")
        return None
    except requests.RequestException:
        print("Could not reach GitHub for " + target + ".")
        return None
    return target, score_repo(repo)


def print_breakdown(target, result):
    print("Vigilance score for " + target + ": " + str(result["total"]) + "/115")
    for component, points in result["breakdown"].items():
        print("  {:16} {}".format(component, points))


def print_ranked_table(scored):
    scored.sort(key=lambda pair: pair[1]["total"], reverse=True)
    print("{:<5}{:<9}Repository".format("Rank", "Score"))
    for rank, (target, result) in enumerate(scored, start=1):
        print("{:<5}{:<9}{}".format(rank, str(result["total"]) + "/115", target))


def run_repo_scoring(argv):
    scored = []
    for target in argv:
        if "/" not in target:
            print("Skipping " + repr(target) + ": use the <owner>/<repo> format.")
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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv

    if argv and argv[0] == "report":
        return run_report(argv[1:])

    if not argv:
        print("Usage:")
        print("  python -m vigilance report --source simulate")
        print("  python -m vigilance <owner>/<repo> [<owner>/<repo> ...]")
        return 1

    return run_repo_scoring(argv)


if __name__ == "__main__":
    raise SystemExit(main())
