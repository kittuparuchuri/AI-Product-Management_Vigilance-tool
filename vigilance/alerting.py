"""Send a gentle alert when a reviewer's trend is flagged.

Configured entirely with environment variables, so no secret lives in code:
  SLACK_WEBHOOK_URL  -- if set, the alert is posted to Slack.
If nothing is configured, alerts print to the console (a safe dry run).
"""

import os

import requests


def build_message(reviewer, first, latest, drop):
    return (
        "Heads up: " + reviewer + "'s review vigilance dipped from "
        + str(round(first)) + " to " + str(round(latest))
        + " (down " + str(round(drop)) + " points). Might be worth a look"
        + " -- no blame, just a nudge to check in."
    )


def _post_slack(text, webhook_url):
    requests.post(webhook_url, json={"text": text}, timeout=10)


def send_alerts(flagged):
    """flagged: {reviewer: DecliningReviewer}. Sends or dry-run-prints each."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    sent = []
    for reviewer in sorted(flagged):
        decliner = flagged[reviewer]
        text = build_message(
            reviewer,
            decliner.first_score,
            decliner.latest_score,
            decliner.drop,
        )
        sent.append(text)
        if webhook:
            try:
                _post_slack(text, webhook)
                print("Alert sent to Slack for " + reviewer + ".")
            except requests.RequestException:
                print("Could not reach Slack for " + reviewer + "; message was:")
                print("  " + text)
        else:
            print("[dry run] " + text)
    return sent
