"""The data contract: the shapes every part of the tool passes around.

Defining these first keeps the rest simple. Whether review data comes from
the real GitHub reader or a fake in-memory simulator, both produce these
same shapes -- so the scoring code can't tell them apart, and you can test
it without ever touching the internet.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReviewEvent:
    """One review left on a pull request."""

    reviewer: str
    is_bot: bool
    state: str
    submitted_at: datetime
    inline_comments: int


@dataclass
class PRMeta:
    """How big a pull request is -- used to judge engagement fairly."""

    additions: int
    deletions: int
    changed_files: int


@dataclass
class ScoredReview:
    """One human review after it has been scored."""

    reviewer: str
    is_rubber_stamp: bool
    comment_density: float
    minutes_after_bot: float
