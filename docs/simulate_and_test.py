"""
Simulates a realistic PR review history to verify the scoring engine
works correctly before pointing it at live GitHub data.

Scenario modeled:
  - Reviewer "alice": starts careful (real comments, waits, doesn't
    rubber-stamp), gradually becomes complacent over 40 PRs -- fewer
    comments, faster approvals right after the AI bot's review.
  - Reviewer "bob": stays consistently careful throughout -- a control
    group to prove the tool doesn't just flag everyone.
"""

import random
from datetime import datetime, timedelta
from vigilance_tracker import ReviewEvent, PRMeta
from vigilance_scoring import score_reviews, compute_vigilance_scores, flag_declining_reviewers

random.seed(42)

def simulate():
    review_events = []
    pr_meta_by_number = {}
    base_time = datetime(2026, 1, 1)

    pr_number = 1
    for week in range(40):  # 40 weeks of PRs
        created = base_time + timedelta(weeks=week)
        additions = random.randint(50, 400)
        deletions = random.randint(10, 150)
        pr_meta_by_number[pr_number] = PRMeta(
            number=pr_number, additions=additions, deletions=deletions,
            changed_files=random.randint(1, 8), created_at=created,
        )

        # AI bot reviews first, same day
        bot_time = created + timedelta(hours=1)
        review_events.append(ReviewEvent(
            pr_number=pr_number, reviewer="coderabbitai[bot]", is_bot=True,
            state="COMMENTED", submitted_at=bot_time, body_length=300, comment_count=3,
        ))

        # ALICE: complacency increases with week number (drift model)
        complacency_factor = min(week / 35.0, 1.0)  # 0 -> 1 over the dataset
        alice_delay_minutes = max(2, 60 * (1 - complacency_factor) + random.gauss(0, 5))
        alice_comments = max(0, round(random.gauss(4 * (1 - complacency_factor), 1)))
        alice_time = bot_time + timedelta(minutes=alice_delay_minutes)
        review_events.append(ReviewEvent(
            pr_number=pr_number, reviewer="alice", is_bot=False,
            state="APPROVED", submitted_at=alice_time,
            body_length=50 if alice_comments else 0, comment_count=alice_comments,
        ))

        # BOB: stays consistently careful (control)
        bob_delay_minutes = max(20, 90 + random.gauss(0, 15))
        bob_comments = max(1, round(random.gauss(4, 1)))
        bob_time = bot_time + timedelta(minutes=bob_delay_minutes)
        review_events.append(ReviewEvent(
            pr_number=pr_number, reviewer="bob", is_bot=False,
            state="APPROVED", submitted_at=bob_time,
            body_length=80, comment_count=bob_comments,
        ))

        pr_number += 1

    return review_events, pr_meta_by_number


if __name__ == "__main__":
    events, meta = simulate()
    scored = score_reviews(events, meta)
    vigilance = compute_vigilance_scores(scored, window_size=5)

    for reviewer in ["alice", "bob"]:
        print(f"\n=== {reviewer} ===")
        print(f"{'Window End':<20} {'RubberStamp%':<14} {'CommentDensity':<16} {'VigilanceScore'}")
        for w in vigilance[reviewer]:
            print(f"{w['window_end'].strftime('%Y-%m-%d'):<20} "
                  f"{w['rubber_stamp_rate']*100:<14.0f} "
                  f"{w['avg_comment_density']:<16.2f} "
                  f"{w['vigilance_score']}")

    print("\n=== Flagged reviewers (score dropped >= 20 points) ===")
    flags = flag_declining_reviewers(vigilance, drop_threshold=20.0)
    for f in flags:
        print(f"{f['reviewer']}: {f['first_score']} -> {f['latest_score']} "
              f"(dropped {f['drop']} pts over {f['windows_tracked']} windows)")
