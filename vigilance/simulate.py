"""Fake but realistic review data, where we already know the answer.

simulate_drift() models two reviewers over 40 weeks:
  - alice: starts careful, gradually rubber-stamps faster with fewer comments
  - bob:   stays careful the whole time (the control)
"""

from datetime import datetime, timedelta

from .models import ReviewEvent, PRMeta

BOT = "ai-review-bot"
START = datetime(2024, 1, 1)


def _pr(reviewer, week, comments, delay_minutes, changed=200):
    """One PR: a bot reviews first, then the human delay_minutes later."""
    base = START + timedelta(weeks=week)
    bot = ReviewEvent(BOT, True, "COMMENTED", base, 5)
    human = ReviewEvent(
        reviewer,
        False,
        "APPROVED",
        base + timedelta(minutes=delay_minutes),
        comments,
    )
    return [bot, human], PRMeta(additions=changed, deletions=0, changed_files=4)


def simulate_drift(weeks=40):
    """Return a chronological list of (reviews, pr_meta) tuples, one per PR."""
    data = []
    for week in range(weeks):
        progress = week / (weeks - 1)

        alice_comments = 1 if (1.4 * (1 - progress)) >= 0.5 else 0
        if alice_comments == 0 and week % 5 == 0:
            alice_comments = 1
        alice_delay = 60 if progress < 0.5 else 8
        data.append(_pr("alice", week, alice_comments, alice_delay))

        bob_comments = 2 if week % 2 == 0 else 1
        data.append(_pr("bob", week, bob_comments, 90))

    return data
