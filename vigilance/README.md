# Vigilance

A small command-line tool that scores how actively a GitHub repository is
maintained. Give it a repo and it fetches the repo's public data from GitHub's
API, then rates it from 0 to 115.

## What it measures

| Signal | Points | Why it matters |
| --- | --- | --- |
| Freshness (recency of last push) | up to 40 | Actively developed repos get pushed to often |
| Not archived | 20 | Archived repos are frozen / read-only |
| Has a license | 15 | A license signals the project is meant to be used |
| Has a description | 10 | Basic project hygiene |
| Issue tracker enabled | 15 | Maintainers who accept issues are engaged |
| Popularity (stars) | up to 15 (bonus) | Widely-used projects tend to be watched closely |

A perfect base score is 100, plus up to 15 bonus points for popularity (max 115).

## Setup

Requires Python 3. From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

On macOS / Linux, activate with `source .venv/bin/activate` instead.

## Usage

Score a single repository (shows the full breakdown):