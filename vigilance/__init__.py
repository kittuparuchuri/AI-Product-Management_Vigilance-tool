"""Vigilance: score how actively a GitHub repository is maintained."""

from .score import score_repo
from .github_client import fetch_repo

__all__ = ["score_repo", "fetch_repo"]
