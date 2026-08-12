"""End-to-end tests: the scorer must reach the truth the simulator knows."""

from vigilance.simulate import simulate_drift
from vigilance.scoring import score_reviews, flag_declining_reviewers


def _score_everything():
    scored = []
    for reviews, pr_meta in simulate_drift():
        scored += score_reviews(reviews, pr_meta)
    return scored


def test_drifter_alice_is_flagged():
    flagged = {d.reviewer for d in flag_declining_reviewers(_score_everything())}
    assert "alice" in flagged


def test_steady_bob_is_not_flagged():
    flagged = {d.reviewer for d in flag_declining_reviewers(_score_everything())}
    assert "bob" not in flagged
