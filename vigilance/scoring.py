"""The scoring engine: turn reviews into a vigilance score.

Pure functions only -- data in, numbers out, no internet. That makes the
whole thing easy to test and impossible for a network glitch to break.
"""

from dataclasses import dataclass

from .models import ScoredReview


@dataclass
class ScoringConfig:
    """Every tunable number lives here, so you change behaviour without
    touching the logic below."""

    rubber_stamp_window_minutes: float = 15.0
    rubber_stamp_weight: float = 60.0
    low_comment_weight: float = 40.0
    target_comment_density: float = 1.0
    window_size: int = 5
    decline_drop: float = 20.0


@dataclass
class DecliningReviewer:
    """The result of flagging: who slipped, and by how much."""

    reviewer: str
    first_score: float
    latest_score: float
    drop: float


def _changed_lines(pr_meta):
    return pr_meta.additions + pr_meta.deletions


def _minutes_between(earlier, later):
    return (later - earlier).total_seconds() / 60.0


def score_reviews(reviews, pr_meta, config=None):
    """Score every human review on one pull request."""
    if config is None:
        config = ScoringConfig()

    changed = max(_changed_lines(pr_meta), 1)
    bot_reviews = [r for r in reviews if r.is_bot]

    scored = []
    for review in reviews:
        if review.is_bot:
            continue

        prior_bots = [b for b in bot_reviews if b.submitted_at <= review.submitted_at]
        if prior_bots:
            latest_bot = max(prior_bots, key=lambda b: b.submitted_at)
            minutes_after_bot = _minutes_between(latest_bot.submitted_at, review.submitted_at)
        else:
            minutes_after_bot = float("inf")

        comment_density = review.inline_comments / changed * 100.0

        is_rubber_stamp = (
            review.state == "APPROVED"
            and review.inline_comments == 0
            and minutes_after_bot <= config.rubber_stamp_window_minutes
        )

        scored.append(
            ScoredReview(
                reviewer=review.reviewer,
                is_rubber_stamp=is_rubber_stamp,
                comment_density=comment_density,
                minutes_after_bot=minutes_after_bot,
            )
        )
    return scored


def _low_comment_penalty(avg_density, config):
    target = config.target_comment_density
    if target <= 0:
        return 0.0
    penalty = (target - avg_density) / target
    return min(1.0, max(0.0, penalty))


def _score_one_window(window, config):
    if not window:
        return 100.0
    rubber_rate = sum(1 for s in window if s.is_rubber_stamp) / len(window)
    avg_density = sum(s.comment_density for s in window) / len(window)
    low_penalty = _low_comment_penalty(avg_density, config)
    score = 100.0 - rubber_rate * config.rubber_stamp_weight - low_penalty * config.low_comment_weight
    return max(0.0, min(100.0, score))


def compute_vigilance_scores(scored_reviews, config=None):
    """Per reviewer, slice reviews into windows and score each. Returns
    {reviewer: [window_score, ...]}. Pass reviews in chronological order."""
    if config is None:
        config = ScoringConfig()

    by_reviewer = {}
    for review in scored_reviews:
        by_reviewer.setdefault(review.reviewer, []).append(review)

    size = max(1, config.window_size)
    scores_by_reviewer = {}
    for reviewer, reviews in by_reviewer.items():
        windows = [reviews[i:i + size] for i in range(0, len(reviews), size)]
        scores_by_reviewer[reviewer] = [_score_one_window(w, config) for w in windows]
    return scores_by_reviewer


def flag_declining_reviewers(scored_reviews, config=None):
    """Flag reviewers whose score fell by >= decline_drop from first window
    to latest. The trend is the signal, not one low score."""
    if config is None:
        config = ScoringConfig()

    scores_by_reviewer = compute_vigilance_scores(scored_reviews, config)
    flagged = []
    for reviewer, scores in scores_by_reviewer.items():
        if len(scores) < 2:
            continue
        first, latest = scores[0], scores[-1]
        drop = first - latest
        if drop >= config.decline_drop:
            flagged.append(DecliningReviewer(reviewer, first, latest, drop))
    return flagged
