"""Unit tests for the rubber-stamp rule in scoring.py (offline, no network)."""

from datetime import datetime, timedelta

from vigilance.models import ReviewEvent, PRMeta
from vigilance.scoring import score_reviews

T0 = datetime(2024, 1, 1, 12, 0)
PR = PRMeta(additions=200, deletions=0, changed_files=4)


def human(state, minutes_after, comments):
    return ReviewEvent("alice", False, state, T0 + timedelta(minutes=minutes_after), comments)


def bot(minutes_after=0):
    return ReviewEvent("ai-bot", True, "COMMENTED", T0 + timedelta(minutes=minutes_after), 5)


def test_fast_zero_comment_approval_is_rubber_stamp_when_bot_first():
    scored = score_reviews([bot(0), human("APPROVED", 10, 0)], PR)
    assert scored[0].is_rubber_stamp is True


def test_not_a_rubber_stamp_without_a_bot():
    scored = score_reviews([human("APPROVED", 10, 0)], PR)
    assert scored[0].is_rubber_stamp is False


def test_not_a_rubber_stamp_if_slow():
    scored = score_reviews([bot(0), human("APPROVED", 30, 0)], PR)
    assert scored[0].is_rubber_stamp is False


def test_not_a_rubber_stamp_with_comments():
    scored = score_reviews([bot(0), human("APPROVED", 10, 4)], PR)
    assert scored[0].is_rubber_stamp is False
