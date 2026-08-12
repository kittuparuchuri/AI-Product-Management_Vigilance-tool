"""The friction role: help prevent complacency in the first place.

On high-risk PRs (big diffs, many files, or sensitive paths like auth/payment),
withhold the AI's verdict until the human commits their own -- then reveal both
and reconcile. CAUGHT (a human flags what the AI approved) is what we protect.
"""

from dataclasses import dataclass, field
from typing import List

SENSITIVE_HINTS = (
    "auth", "login", "password", "token", "secret",
    "payment", "billing", "checkout", "security", "crypto",
)


@dataclass
class FrictionConfig:
    big_diff_lines: int = 300
    many_files: int = 10


@dataclass
class PullRequest:
    number: int
    additions: int
    deletions: int
    changed_files: int
    paths: List[str] = field(default_factory=list)
    ai_verdict: str = "APPROVED"
    human_verdict: str = "APPROVED"


def risk_reasons(pr, config=None):
    if config is None:
        config = FrictionConfig()
    reasons = []
    if pr.additions + pr.deletions >= config.big_diff_lines:
        reasons.append("big diff")
    if pr.changed_files >= config.many_files:
        reasons.append("many files")
    if any(any(hint in path.lower() for hint in SENSITIVE_HINTS) for path in pr.paths):
        reasons.append("sensitive path")
    return reasons


def is_high_risk(pr, config=None):
    return len(risk_reasons(pr, config)) > 0


def decide(pr, config=None):
    return "WITHHOLD" if is_high_risk(pr, config) else "show"


def reconcile(ai_verdict, human_verdict):
    approved = "APPROVED"
    if ai_verdict == approved and human_verdict != approved:
        return "CAUGHT"
    if ai_verdict != approved and human_verdict == approved:
        return "OVERRIDE"
    return "AGREED"


def _demo_pulls():
    return [
        PullRequest(101, additions=20, deletions=2, changed_files=1,
                    paths=["docs/readme.md"],
                    ai_verdict="APPROVED", human_verdict="APPROVED"),
        PullRequest(102, additions=320, deletions=40, changed_files=6,
                    paths=["src/payments/checkout.py"],
                    ai_verdict="APPROVED", human_verdict="CHANGES_REQUESTED"),
        PullRequest(103, additions=15, deletions=3, changed_files=1,
                    paths=["src/auth/login.py"],
                    ai_verdict="CHANGES_REQUESTED", human_verdict="CHANGES_REQUESTED"),
        PullRequest(104, additions=90, deletions=60, changed_files=12,
                    paths=["a.py", "b.py", "c.py"],
                    ai_verdict="APPROVED", human_verdict="APPROVED"),
        PullRequest(105, additions=500, deletions=20, changed_files=4,
                    paths=["src/feature.py"],
                    ai_verdict="CHANGES_REQUESTED", human_verdict="APPROVED"),
    ]


def friction_demo(config=None):
    if config is None:
        config = FrictionConfig()

    print("Friction role demo")
    print("=" * 60)
    for pr in _demo_pulls():
        reasons = risk_reasons(pr, config)
        if reasons:
            outcome = reconcile(pr.ai_verdict, pr.human_verdict)
            print("PR #" + str(pr.number) + "  WITHHOLD  (" + ", ".join(reasons) + ")")
            print("    AI: " + pr.ai_verdict + " | human: " + pr.human_verdict
                  + "  ->  " + outcome)
        else:
            print("PR #" + str(pr.number) + "  show      (low risk)")
            print("    AI: " + pr.ai_verdict + " (shown immediately)")
    return 0
