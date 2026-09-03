# AnomaLog

A log anomaly detector that uses Claude AI to classify every line of a log file as **Normal**, **Suspicious**, or **Critical**, and then generates an incident summary for your security team.

## Stack

| Layer      | Technology                     |
|------------|-------------------------------|
| Backend    | Python 3.12 + FastAPI          |
| AI         | Anthropic Claude (claude-sonnet-4-6) |
| Database   | PostgreSQL 16                  |
| Templates  | Jinja2 + Tailwind CSS (CDN)    |
| Container  | Docker + Docker Compose        |

## Quick start

```bash
# 1. Clone and enter the project
cd anomalog

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Build and run
docker compose up --build

# 4. Open in browser
open http://localhost:8001
```

## How it works

1. **Upload** — drop a `.log`, `.txt`, or `.csv` file (up to 500 lines analyzed).
2. **Classify** — Claude reads each line in batches of 20 and labels it `normal`, `suspicious`, or `critical` with a one-sentence reason.
3. **Report** — Claude generates a 2-3 paragraph incident summary covering severity, what the logs suggest, and recommended actions.
4. **Review** — browse every classified line in a color-coded table and share the incident report with your team.
