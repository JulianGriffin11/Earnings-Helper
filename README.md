# Earnings Helper

Year-over-year income-statement analysis for public companies. Search a ticker, pull SEC XBRL data, compute the changes in Python, and show a short debrief of what moved.

## Why I Built This 💡

I wanted a faster way to read an earnings report. Instead of hunting through a filing for which lines changed, I wanted the year-over-year numbers calculated first, then a short explanation of what those changes mean.

## How It Works

```text
        Ticker search
              ↓
        SEC XBRL facts
              ↓
       Python YoY math
              ↓
          PostgreSQL
              ↓
         LLM debrief
              ↓
       Report in the UI
```

Enter a ticker. The app resolves the company, pulls structured facts from the SEC, and computes quarterly and annual year-over-year changes in Python. Postgres caches the report for the latest filing. The model writes a debrief from those numbers. One Render web service serves the React UI and the API together.

## Tech Stack 🛠️

| Technology | Purpose |
| --- | --- |
| React / Vite | Search page and report UI |
| FastAPI | API, and the built UI in production |
| Python | SEC fetch, YoY calculation, and orchestration |
| PostgreSQL | Cached reports and debriefs |
| SQLAlchemy / Alembic | Data access and migrations |
| OpenAI API | Earnings debrief |
| Render | One web service for the UI and API |

## AI Pipeline 🤖

Python and SQL handle fetching, period selection, storage, and the arithmetic. The LLM is used only to interpret numbers the code already computed.

1. Compute the quarterly and annual year-over-year rows
2. Write a debrief that explains what moved

Model output is returned as structured JSON so the application can store it and render the debrief in code. The model does not calculate percentages.

## Database 🗄️

PostgreSQL stores the company, the quarterly and annual report, and the debrief. A repeat lookup for the latest filing is served from cache when the stored period is still current.

## Run locally

Prerequisites: Python 3.11+, Node.js 18+, pnpm, uv, and a Postgres database.

```bash
cd backend
cp .env.example .env   # SEC_USER_AGENT, DATABASE_URL, OPENAI_API_KEY
uv sync
uv run alembic upgrade head

# from the repo root
./scripts/dev.sh
```

`scripts/dev.sh` starts the API on port 8000 and Vite on port 5173. Leave `VITE_API_BASE_URL` empty so the dev server proxies `/api`.

Open http://localhost:5173 and search for a ticker such as AMZN.

| Variable | Required | Description |
| --- | --- | --- |
| `SEC_USER_AGENT` | yes | Contact string for SEC requests |
| `DATABASE_URL` | yes | Postgres URL. Use the direct connection (port 5432) for migrations |
| `OPENAI_API_KEY` | yes | Debrief generation |
| `OPENAI_MODEL` | no | Defaults to `gpt-4o-mini` |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | no | Observability |

Deploy with the Blueprint in [`render.yaml`](render.yaml). Render runs [`scripts/render-build.sh`](scripts/render-build.sh), applies migrations, then starts the API with [`scripts/start.sh`](scripts/start.sh). FastAPI serves the built UI and `/api` on the same URL. Set `SEC_USER_AGENT`, `DATABASE_URL`, and `OPENAI_API_KEY` on the service. Health check: `GET /health`.

## What I Learned 📚

Building this was less about the model call and more about the pipeline around it. SEC filings do not all use the same tags, and the year-over-year math has to stay in code so the debrief is explaining numbers that can be checked.

Predictable work belongs in Python. Fetching, period selection, arithmetic, and caching stay deterministic. The model is reserved for the written debrief.

## Future Improvements 🚀

- Cover filers that do not publish a single Operating Expenses XBRL tag. Fallbacks live in [`backend/config/metrics.yaml`](backend/config/metrics.yaml), and SG&A is not always the same as total operating expenses.
- Show when a cached report is stale relative to a new filing
- Add clearer empty states when a metric tag is missing

## Project Status ✅

The report pipeline is built: search, SEC facts, year-over-year tables, a cached Postgres report, and an LLM debrief. It is set up to deploy as one Render web service. Future work would extend the metric coverage, not split the app into separate frontend and backend deploys.
