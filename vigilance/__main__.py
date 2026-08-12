"""Command-line interface."""

import sys

import requests

from .github_client import fetch_repo
from .score import score_repo


def _parse_flags(args):
    opts = {}
    key = None
    for token in args:
        if token.startswith("--"):
            key = token[2:]
            opts[key] = ""
        elif key is not None:
            opts[key] = token
            key = None
    return opts


def _compute(data):
    from .scoring import (
        score_reviews,
        compute_vigilance_scores,
        flag_declining_reviewers,
    )
    scored = []
    for reviews, pr_meta in data:
        scored += score_reviews(reviews, pr_meta)
    windows = compute_vigilance_scores(scored)
    flagged = {d.reviewer: d for d in flag_declining_reviewers(scored)}
    return windows, flagged


def _print_console(windows, flagged, source):
    print("Vigilance report  (source: " + source + ")")
    print("=" * 60)
    if not windows:
        print("(no human reviews to score)")
        return
    for reviewer in sorted(windows):
        scores = [round(s) for s in windows[reviewer]]
        first, latest = scores[0], scores[-1]
        if reviewer in flagged:
            status = "FLAGGED (dropped " + str(round(flagged[reviewer].drop)) + ")"
        else:
            status = "ok"
        print("{:22} {:30} {:>3} -> {:<3}  {}".format(
            reviewer, str(scores), first, latest, status))
    print()
    names = ", ".join(sorted(flagged)) if flagged else "(none)"
    print("Flagged reviewers: " + names)


def run_report(args):
    opts = _parse_flags(args)
    source = opts.get("source") or "simulate"

    if source == "simulate":
        from .simulate import simulate_drift
        data = simulate_drift()

    elif source == "github":
        owner = opts.get("owner")
        repo = opts.get("repo")
        if not owner or not repo:
            print("For --source github, pass --owner and --repo.")
            return 1
        try:
            max_prs = int(opts.get("max-prs") or 40)
        except ValueError:
            print("--max-prs must be a number.")
            return 1

        from .github_fetcher import fetch_review_data
        try:
            data = fetch_review_data(owner, repo, max_prs)
        except requests.HTTPError as error:
            code = error.response.status_code
            if code == 401:
                print("401 Bad credentials: your GITHUB_TOKEN is wrong or expired. Re-set it (7.2).")
            elif code == 403:
                print("403 rate limit: set a GITHUB_TOKEN so requests are not anonymous.")
            elif code == 404:
                print("Not Found: check the owner/repo spelling, or use a token that can see it.")
            else:
                print("GitHub returned an error (" + str(code) + ").")
            return 1
        except requests.RequestException:
            print("Could not reach GitHub. Check your connection.")
            return 1

        if not data:
            print("No reviews found for " + owner + "/" + repo + " in the last " + str(max_prs) + " PRs.")
            return 1

    else:
        print("Unknown source " + repr(source) + ". Use simulate or github.")
        return 1

    windows, flagged = _compute(data)
    _print_console(windows, flagged, source)

    if "csv" in opts:
        from .outputs import write_csv
        write_csv(windows, flagged, "output/vigilance.csv")
        print("Wrote output/vigilance.csv")

    if "html" in opts:
        from .outputs import write_html
        write_html(windows, flagged, "output/vigilance.html", source)
        print("Wrote output/vigilance.html")

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
        print("  python -m vigilance report --source simulate [--html] [--csv]")
        print("  python -m vigilance report --source github --owner OWNER --repo REPO --max-prs N")
        print("  python -m vigilance <owner>/<repo> [<owner>/<repo> ...]")
        return 1

    return run_repo_scoring(argv)


if __name__ == "__main__":
    raise SystemExit(main())
