# Reviewer Vigilance Tracker

> A team **smoke detector** for code-review quality — not a performance scorecard.

Vigilance measures how carefully pull-request reviews are being done on a GitHub
repository, spots reviewers whose engagement is **drifting downward over time**,
and adds guardrails on high-risk changes. It exists to answer one question: *as
teams lean on AI reviewers, are humans still actually reviewing — or just
rubber-stamping what the bot already approved?*

It is deliberately built to be a **shared safety net**, never a tool for ranking
or evaluating individuals. See [Responsible use](#responsible-use) before rolling
it out.

---

## Table of contents

- [What it does](#what-it-does)
- [How the score works](#how-the-score-works)
- [Quick start](#quick-start)
- [Usage](#usage)
- [Getting a GitHub token](#getting-a-github-token)
- [Outputs](#outputs)
- [Deploying it (GitHub Actions)](#deploying-it-github-actions)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [Running the tests](#running-the-tests)
- [Maintenance](#maintenance)
- [Responsible use](#responsible-use)

---

## What it does

For every human review on a pull request, Vigilance derives three signals:

- **Rubber stamp?** — did a human approve with zero comments, right after an AI
  bot had already reviewed, and within 15 minutes of it?
- **Comment density** — how many inline comments per 100 changed lines.
- **Minutes after the bot** — how quickly the human approved after the AI review.

It then rolls reviews into windows and produces a **0–100 vigilance score** per
reviewer, and **flags** anyone whose score is trending down. Output comes three
ways: a console table, a CSV, and a shareable HTML dashboard with trend lines.

It can also:

- **Alert** (gentle Slack nudge) when a reviewer is flagged.
- Run a **friction role** that, on high-risk PRs, withholds the AI's verdict
  until a human commits their own — then reveals both and reconciles them.

---

## How the score works

**A review is a "rubber stamp" only when all four are true:**

1. a human **APPROVED** the PR,
2. they left **zero** comments,
3. an **AI bot reviewed the same PR first**, and
4. they approved **within 15 minutes** of that bot review.

**The score, per rolling window of reviews (default 5):**

```
vigilance = 100
          - (rubber_stamp_rate    * 60)
          - (low_comment_penalty  * 40)
```

`low_comment_penalty` rises from 0 to 1 as comment density falls below a target.
Every number here lives in one `ScoringConfig` object, so behaviour is tuned
without touching logic.

**Flagging is about the trend, not one bad day.** A reviewer is flagged only when
their score falls **20+ points** from their first window to their latest. One low
score is noise; a sustained decline is signal.

---

## Quick start

Requires **Python 3** and **git**.

```bash
# 1. clone
git clone https://github.com/kittuparuchuri/AI-Product-Management_Vigilance-tool.git
cd AI-Product-Management_Vigilance-tool

# 2. create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. install dependencies
pip install -r requirements.txt

# 4. prove it works on built-in fake data
python -m vigilance report --source simulate
```

You should see reviewer **alice** flagged with a falling score and **bob** steady
and unflagged — the tool catching the pattern it is designed to catch.

---

## Usage

```bash
# Run on built-in simulated data (no token needed)
python -m vigilance report --source simulate

# Also write the CSV and HTML dashboard, and print a (dry-run) alert
python -m vigilance report --source simulate --html --csv --alert

# Run on a real public repo (needs a GitHub token, see below)
python -m vigilance report --source github --owner pallets --repo flask --max-prs 40

# Demonstrate the friction role
python -m vigilance friction-demo
```

Reading the report: each reviewer shows their window scores, first-to-latest
movement, and status (`ok` or `FLAGGED`). Flagging requires at least two windows
(≈10 reviews from one person), so reviewers with few reviews show as `ok`.

---

## Getting a GitHub token

Running against a real repo (`--source github`) needs a token so the GitHub API
doesn't rate-limit you.

1. GitHub → **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate**. For public repos, no special permissions are
   required.
2. Put it in your shell — **never in a file**:

   ```powershell
   # Windows PowerShell
   $env:GITHUB_TOKEN="github_pat_xxxxx"
   ```
   ```bash
   # macOS / Linux
   export GITHUB_TOKEN="github_pat_xxxxx"
   ```

The token lives only in your terminal session. Responses are cached in
`.vigilance_cache/` (git-ignored), so repeat runs are fast and free.

---

## Outputs

| Output | How | Where |
|---|---|---|
| Console table | default | your terminal |
| CSV (for Excel/Sheets) | `--csv` | `output/vigilance.csv` |
| HTML dashboard | `--html` | `output/vigilance.html` |

The dashboard shows a per-reviewer trend line (red for a flagged/declining
reviewer, green for a steady one), a flagged panel, and a full data table. Open
it in any browser.

---

## Deploying it (GitHub Actions)

The bot runs **on GitHub's servers for free** — no server to rent, no machine to
keep on. Two workflows in `.github/workflows/` do the work:

- **`weekly-digest.yml`** — runs on a weekly schedule (and on demand). It
  generates the dashboard, publishes it to GitHub Pages, and posts a digest issue.
- **`pr-nudge.yml`** — runs whenever a review is submitted, posting a gentle
  reminder comment on approvals.

**One-time setup in the repo's Settings:**

1. **Pages** → Source: **GitHub Actions**. *(Public repo required for Pages on a
   free plan.)*
2. **Actions → General → Workflow permissions** → **Read and write** → Save.
3. *(Optional)* **Secrets and variables → Actions** → add `SLACK_WEBHOOK_URL` for
   Slack alerts.

Then: **Actions tab → Reviewer Vigilance - Weekly Digest → Run workflow.** Within
a minute you get a digest issue and (if the repo is public) a live dashboard at
`https://<you>.github.io/<repo>/`.

> Scheduled workflows auto-pause after 60 days with no commits — an occasional
> push keeps the weekly job alive.

---

## Configuration

**Scoring thresholds** — `vigilance/scoring.py`, `ScoringConfig`:

| Setting | Default | Meaning |
|---|---|---|
| `rubber_stamp_window_minutes` | 15 | "approved right after the bot" window |
| `rubber_stamp_weight` | 60 | max points lost to rubber stamping |
| `low_comment_weight` | 40 | max points lost to thin comments |
| `target_comment_density` | 1.0 | comments per 100 changed lines |
| `window_size` | 5 | reviews per rolling window |
| `decline_drop` | 20 | point drop that triggers a flag |

**Identifying AI bots** — `vigilance/github_fetcher.py`, `AI_BOT_LOGINS`. The whole
signal depends on correctly telling the AI reviewer's reviews from humans'. When
your team adopts a new AI review bot, add its exact GitHub login (e.g.
`"coderabbitai[bot]"`) to this set. **Human reviewers are never listed — they are
discovered automatically from the data.**

**Environment variables:**

- `GITHUB_TOKEN` — for local `--source github` runs.
- `SLACK_WEBHOOK_URL` — if set, alerts post to Slack; otherwise they dry-run to
  the console.

---

## Project layout

```
vigilance/
  models.py          data contract: ReviewEvent, PRMeta, ScoredReview
  scoring.py         pure scoring engine + ScoringConfig
  simulate.py        fake 40-week data with a known answer
  github_fetcher.py  real PRs + reviews from the GitHub API
  outputs.py         CSV and HTML dashboard writers
  alerting.py        gentle Slack / console alerts
  friction.py        high-risk detection + withhold/reveal + reconcile
  __main__.py        command-line interface
tests/               automated tests (offline)
.github/workflows/   weekly-digest.yml, pr-nudge.yml
requirements.txt     requests, pytest
pytest.ini           makes `pytest` find the package
```

The scoring engine is **pure** (data in, numbers out, no network), which is why it
is easy to test and impossible for a network glitch to break. The simulator and
the real GitHub fetcher both produce the same shapes, so the tested scorer runs
unchanged on real data.

*Also included:* `score.py` and `github_client.py` are a small earlier tool that
scores how actively a **repository** is maintained (`python -m vigilance
owner/repo`) — kept for reference, separate from the reviewer tracker above.

---

## Running the tests

```bash
pytest -q
```

The tests run offline (no network, no token) and assert the properties that
matter: the drifting reviewer gets flagged, the steady one does not, and a fast
zero-comment approval counts as a rubber stamp only if a bot reviewed first.

---

## Maintenance

- Add every new AI review bot login to `AI_BOT_LOGINS`.
- Re-check `ScoringConfig` thresholds quarterly against how your team really reviews.
- Consider adding a **review-latency** signal (time vs. PR size) as a fourth input.
- Rotate your personal access token periodically (the workflow's built-in token
  rotates itself).

---

## Responsible use

Before trusting the number, run the tool for **4–8 weeks** and check whether low
scores actually line up with more escaped bugs, hotfixes, or reverts on your team.
Until you've seen that link in your own data, treat the score as a
**conversation-starter, not a verdict**.

**Use it as a team smoke detector, never a scorecard.** Do not wire these numbers
into individual performance reviews — that just trains people to game the metric
with padded comments and artificial delays. Use it to improve the *workflow*:
rotate reviewers, add friction on the risky PRs.

And keep the caveat visible: a fast, low-comment approval isn't always
complacency — sometimes the PR really was trivial. The tool flags a **trend**, and
it stays a heuristic.
