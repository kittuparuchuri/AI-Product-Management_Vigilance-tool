"""
Vigilance scoring engine.

Takes ReviewEvent + PRMeta data (from GitHub, real or simulated) and
computes a per-reviewer vigilance score over time.

Logic, in plain terms:
  A review is "rubber-stamped" if a human approved it with zero
  comments, AND an AI bot had already reviewed the same PR first.
  That's the exact failure mode automation complacency research
  describes: the human defers to the machine's green light instead
  of independently checking.

  Vigilance score (0-100, higher = more engaged):
    100 - (rubber_stamp_rate * 60) - (low_comment_penalty * 40)
  where low_comment_penalty scales with how far below expected
  comment density (given PR size) the reviewer falls.

  We track this in rolling windows (e.g. per N reviews) so a team
  can see the TREND -- a reviewer sliding from 80 -> 40 over three
  months is the actual signal, not a single low score on one PR.
"""

from dataclasses import dataclass
from collections import defaultdict
from datetime import timedelta
import statistics


@dataclass
class ScoredReview:
    pr_number: int
    reviewer: str
    had_bot_review_first: bool
    is_rubber_stamp: bool
    comments_per_100_lines: float
    minutes_after_bot: float or None
    submitted_at: object


def score_reviews(review_events: list, pr_meta_by_number: dict) -> list:
    """
    review_events: list[ReviewEvent], all reviews across all PRs
    pr_meta_by_number: dict[int, PRMeta]
    Returns list[ScoredReview] for HUMAN reviews only (bots excluded
    from being scored -- we're measuring human vigilance).
    """
    by_pr = defaultdict(list)
    for ev in review_events:
        by_pr[ev.pr_number].append(ev)

    scored = []
    for pr_number, events in by_pr.items():
        events_sorted = sorted(events, key=lambda e: e.submitted_at)
        bot_events = [e for e in events_sorted if e.is_bot]
        human_events = [e for e in events_sorted if not e.is_bot]
        first_bot_time = bot_events[0].submitted_at if bot_events else None

        meta = pr_meta_by_number.get(pr_number)
        total_lines = (meta.additions + meta.deletions) if meta else 0

        for h in human_events:
            minutes_after_bot = None
            if first_bot_time and h.submitted_at >= first_bot_time:
                minutes_after_bot = (h.submitted_at - first_bot_time).total_seconds() / 60.0

            comments_per_100 = (
                (h.comment_count / total_lines) * 100 if total_lines > 0 else 0.0
            )

            is_rubber_stamp = (
                h.state == "APPROVED"
                and h.comment_count == 0
                and first_bot_time is not None
                and minutes_after_bot is not None
                and minutes_after_bot < 15  # approved within 15 min of bot review, no input
            )

            scored.append(ScoredReview(
                pr_number=pr_number,
                reviewer=h.reviewer,
                had_bot_review_first=first_bot_time is not None,
                is_rubber_stamp=is_rubber_stamp,
                comments_per_100_lines=round(comments_per_100, 3),
                minutes_after_bot=minutes_after_bot,
                submitted_at=h.submitted_at,
            ))
    return scored


def compute_vigilance_scores(scored_reviews: list, window_size: int = 5) -> dict:
    """
    Groups scored reviews per reviewer, sorted by time, and computes
    a vigilance score for each rolling window of `window_size` reviews.
    Returns {reviewer: [(window_end_date, score), ...]}
    """
    by_reviewer = defaultdict(list)
    for sr in scored_reviews:
        by_reviewer[sr.reviewer].append(sr)

    results = {}
    for reviewer, reviews in by_reviewer.items():
        reviews_sorted = sorted(reviews, key=lambda r: r.submitted_at)
        windows = []
        for i in range(0, len(reviews_sorted), window_size):
            chunk = reviews_sorted[i:i + window_size]
            if not chunk:
                continue
            rubber_stamp_rate = sum(1 for c in chunk if c.is_rubber_stamp) / len(chunk)
            avg_comment_density = statistics.mean(c.comments_per_100_lines for c in chunk)

            # penalty scales down as comment density rises; flattens above density=2.0
            low_comment_penalty = max(0.0, 1 - min(avg_comment_density / 2.0, 1.0))

            score = 100 - (rubber_stamp_rate * 60) - (low_comment_penalty * 40)
            score = round(max(0.0, min(100.0, score)), 1)

            windows.append({
                "window_end": chunk[-1].submitted_at,
                "reviews_in_window": len(chunk),
                "rubber_stamp_rate": round(rubber_stamp_rate, 2),
                "avg_comment_density": round(avg_comment_density, 2),
                "vigilance_score": score,
            })
        results[reviewer] = windows
    return results


def flag_declining_reviewers(vigilance_scores: dict, drop_threshold: float = 20.0) -> list:
    """Flags reviewers whose vigilance score dropped by more than
    `drop_threshold` points from their first window to their most
    recent window -- the actual trend signal, not a single bad score."""
    flags = []
    for reviewer, windows in vigilance_scores.items():
        if len(windows) < 2:
            continue
        first_score = windows[0]["vigilance_score"]
        last_score = windows[-1]["vigilance_score"]
        drop = first_score - last_score
        if drop >= drop_threshold:
            flags.append({
                "reviewer": reviewer,
                "first_score": first_score,
                "latest_score": last_score,
                "drop": round(drop, 1),
                "windows_tracked": len(windows),
            })
    return sorted(flags, key=lambda f: f["drop"], reverse=True)
