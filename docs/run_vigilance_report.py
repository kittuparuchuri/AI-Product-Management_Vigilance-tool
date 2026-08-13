"""
Run a vigilance report against a real GitHub repo.

Usage:
    python3 run_vigilance_report.py <owner> <repo> [--token YOUR_GH_TOKEN] [--max-prs 30]

Note on rate limits: GitHub's unauthenticated API is capped at 60
requests/hour PER SOURCE IP. Each PR costs ~3 requests (meta, reviews,
review comments), so unauthenticated you can realistically pull ~15-18
PRs per hour. Pass a personal access token (no special scopes needed
for public repos) for 5,000 requests/hour -- get one at
https://github.com/settings/tokens

This script was validated end-to-end against simulated data
(see simulate_and_test.py) which confirmed the scoring engine
correctly distinguishes a genuinely drifting reviewer from a
consistently careful one. Live GitHub fetching uses the same
scoring engine -- only the data source changes.
"""

import sys
import argparse
from vigilance_tracker import GitHubReviewFetcher
from vigilance_scoring import score_reviews, compute_vigilance_scores, flag_declining_reviewers


def run(owner: str, repo: str, token: str = None, max_prs: int = 20, window_size: int = 5):
    fetcher = GitHubReviewFetcher(owner, repo, token=token)

    print(f"Fetching last {max_prs} closed PRs from {owner}/{repo}...")
    try:
        prs = fetcher.fetch_recent_closed_prs(max_prs=max_prs)
    except RuntimeError as e:
        print(f"\nCould not fetch PR list: {e}")
        print("Retry with a --token, or wait for the rate limit window to reset.")
        return

    all_events = []
    pr_meta_by_number = {}

    for pr in prs:
        num = pr["number"]
        try:
            meta = fetcher.fetch_pr_meta(num)
            events = fetcher.fetch_pr_reviews(num)
        except RuntimeError as e:
            print(f"Stopped early: {e}")
            break
        pr_meta_by_number[num] = meta
        all_events.extend(events)
        print(f"  PR #{num}: {len(events)} review event(s)")

    if not all_events:
        print("\nNo review data collected (likely rate-limited before any PR was fetched).")
        print("Retry with a --token, or wait for the rate limit window to reset.")
        return

    scored = score_reviews(all_events, pr_meta_by_number)
    human_reviewers = set(s.reviewer for s in scored)

    if not human_reviewers:
        print("\nNo human reviews found in this sample (only bot reviews, or no reviews at all).")
        return

    vigilance = compute_vigilance_scores(scored, window_size=window_size)

    print("\n=== Vigilance scores by reviewer ===")
    for reviewer, windows in vigilance.items():
        print(f"\n{reviewer}:")
        for w in windows:
            print(f"  {w['window_end'].strftime('%Y-%m-%d')} | "
                  f"rubber-stamp rate: {w['rubber_stamp_rate']*100:.0f}% | "
                  f"comment density: {w['avg_comment_density']:.2f} | "
                  f"vigilance score: {w['vigilance_score']}")

    print("\n=== Flagged reviewers (declining vigilance) ===")
    flags = flag_declining_reviewers(vigilance)
    if not flags:
        print("None -- no reviewer showed a significant vigilance drop in this sample.")
    for f in flags:
        print(f"  {f['reviewer']}: {f['first_score']} -> {f['latest_score']} "
              f"(dropped {f['drop']} pts)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reviewer vigilance tracker for AI-assisted code review")
    parser.add_argument("owner", help="GitHub repo owner, e.g. 'pallets'")
    parser.add_argument("repo", help="GitHub repo name, e.g. 'flask'")
    parser.add_argument("--token", default=None, help="GitHub personal access token (optional, raises rate limit)")
    parser.add_argument("--max-prs", type=int, default=20)
    parser.add_argument("--window-size", type=int, default=5)
    args = parser.parse_args()

    run(args.owner, args.repo, token=args.token, max_prs=args.max_prs, window_size=args.window_size)
