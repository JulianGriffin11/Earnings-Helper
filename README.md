# Earnings Helper

Automates year-over-year (YoY) revenue and expense analysis for public companies. Enter a ticker or company name, fetch structured financial data from the SEC, compute deterministic YoY metrics, generate an LLM earnings debrief, and cache results in Postgres.

---

## What It Does

1. You enter a company (e.g. `AMZN` or `Amazon`)
2. The backend resolves the ticker to a SEC CIK and fetches XBRL financial data
3. Python computes quarterly and annual YoY changes for standard income-statement line items
4. An LLM agent reads the computed data and produces a structured earnings debrief (narrative only — no math)
5. Results are saved to Postgres so repeat lookups are fast and past reports are browsable
6. The frontend shows YoY tables, the debrief, and report history

---

## Architecture

```mermaid
flowchart LR
    User["User enters AMZN"]
    Frontend["React UI"]
    API["FastAPI"]
    SEC["SEC XBRL API"]
    Calc["YoY calculator"]
    DB["Postgres"]
    LLM["LLM debrief agent"]
    Report["Full report + debrief"]

    User --> Frontend --> API
    API --> SEC --> Calc
    Calc --> DB
    Calc --> LLM
    LLM --> DB
    DB --> Report --> Frontend
```

### Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Data source | [SEC data.sec.gov XBRL API](https://data.sec.gov/) | Free, no API key, structured JSON |
| YoY math | Deterministic Python | Auditable, testable, no hallucinated numbers |
| LLM | Debrief/narrative layer only | Hands-on LLM experience; interprets pre-computed data, never does arithmetic |
| LLM output | Pydantic structured output | Consistent debrief format; easy to render and store |
| Database | Postgres via Supabase | Cache LLM debriefs + report history without over-engineering |
| Backend | Python + FastAPI | Async-friendly; Pydantic shared across API, LLM, and DB |
| Frontend | React (Vite) + Tailwind CSS | Search bar, YoY tables, debrief panel, report history; strict TypeScript, native fetch |

---

## Prerequisites

Before building, install:

- **Python 3.11+**
- **Node.js 18+** and **pnpm** (for the React frontend)
- **Supabase account** (for Postgres — Phase 3)
- **OpenAI API key** (or Anthropic — for the LLM debrief layer)

You'll also need a contact email for the SEC `User-Agent` header (required by SEC policy).

---

## Step-by-Step Build Guide

Work through these phases in order. Each phase builds on the last.

---

### Phase 1 — SEC Data Layer

**Goal:** Fetch structured financial data for a company from the SEC.

#### 1.1 Set up the backend project

```bash
mkdir -p backend/app/{routes,services,models,db} backend/config backend/playground
cd backend
# Create pyproject.toml with: fastapi, uvicorn, httpx, pydantic, pyyaml, pytest
```

Create `.env.example`:

```env
SEC_USER_AGENT=EarningsHelper your-email@example.com
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
OPENAI_API_KEY=sk-...
```

#### 1.2 Build the SEC HTTP client

File: `backend/app/services/ingest.py`

- Use `httpx` for async HTTP requests
- Set `User-Agent` header from env on every request
- Add simple in-memory cache (TTL ~24h) for SEC responses
- Respect rate limit (~10 requests/second)

Key SEC endpoints:

```
# Ticker → CIK lookup
GET https://www.sec.gov/files/company_tickers.json

# Single financial concept for a company
GET https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{Concept}.json

# All facts (for tag discovery / fallbacks)
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json

# Recent filings metadata
GET https://data.sec.gov/submissions/CIK{cik}.json
```

CIK must be **zero-padded to 10 digits** (e.g. Amazon = `0001018724`).

#### 1.3 Build ticker lookup

File: `backend/app/services/resolver.py`

- Load `company_tickers.json` and build a lookup map
- Support search by ticker (`AMZN`) or partial company name (`Amazon`)
- Return: `{ ticker, name, cik }`

#### 1.4 Build XBRL parser (start with one metric)

File: `backend/app/services/extractor.py`

- Fetch a single concept (start with `Revenues`) for a CIK
- Filter results to the correct form type (`10-Q` or `10-K`)
- Normalize facts: prefer duration entries, use `end` date for period matching
- On duplicate values for the same period, keep the one with the latest `filed` date

#### 1.5 Smoke test with Amazon

```bash
cd backend
uv run python playground/test_ingest.py
```

**Phase 1 checklist:**
- [x] SEC client with User-Agent and caching
- [x] Ticker/name → CIK resolution
- [x] Fetch one XBRL concept for one company
- [x] Playground smoke test against live SEC

---

### Phase 2 — YoY Engine

**Goal:** Compute quarterly and annual YoY changes for configured income-statement metrics.

#### 2.1 Create metrics config

File: `backend/config/metrics.yaml`  
Loader: `backend/app/core/load_metrics.py`

| Display Label | Primary XBRL Tag | Fallback Tags |
|---|---|---|
| Revenue | `Revenues` | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet` |
| Operating Expenses | `OperatingExpenses` | `CostsAndExpenses`, `OtherCostAndExpenseOperating` |
| Gross Profit | `GrossProfit` | derived: Revenue − COGS if missing |
| Net Income | `NetIncomeLoss` | `NetIncomeLossAvailableToCommonStockholdersBasic` |

#### 2.2 Build the YoY calculator

File: `backend/app/services/yoy_calculator.py`

**Quarterly YoY (10-Q):**
- Anchor period dates from Revenue (latest `10-Q` `end` vs same `end` one year prior)
- Loop metrics from `metrics.yaml`; try primary tag then fallbacks at those dates
- Compute for each metric:
  - `dollar_change = current - prior`
  - `pct_change = (current / prior - 1) * 100` (omit pct when `prior == 0`)

**Annual YoY (10-K):**
- Same logic using latest `10-K` period ends

**Normalization rules (critical — prevents bad numbers):**
1. Match periods by `end` date, not just `fy`
2. Prefer duration facts (`start` + `end` present) over instant facts (handled in `extractor.py`)
3. On duplicates, keep the latest `filed` date (handles restatements)
4. Try primary XBRL tag first, then fallbacks — never mix tags across periods
5. Validate: value exists, units are USD, form type matches

Example output:

```json
{
  "company": "AMAZON COM INC",
  "cik": "0001018724",
  "ticker": "AMZN",
  "generated_at": "2026-08-04T19:30:00",
  "quarterly": {
    "period_end": "2026-06-30",
    "prior_period_end": "2025-06-30",
    "metrics": [
      {
        "label": "Revenue",
        "tag": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "current": 382125000000,
        "prior": 323369000000,
        "dollar_change": 58756000000,
        "pct_change": 18.2
      }
    ]
  },
  "annual": { "..." : "..." }
}
```

#### 2.3 Validate the calculator

```bash
cd backend
uv run python playground/test_yoy.py
```

Writes one JSON file per run to `backend/artifacts/{TICKER}_{date}.json` for manual spot-checks against SEC filings.

**Phase 2 checklist:**
- [x] `metrics.yaml` with line items + fallback tags
- [x] `load_metrics.py` loader
- [x] `yoy_calculator.py` (generic metric loop)
- [x] Quarterly YoY matching by `end` date
- [x] Annual YoY matching
- [x] Playground smoke test (`playground/test_yoy.py`)
- [x] Artifact JSON per run for spot-checks (`artifacts/`)
- [ ] Edge cases: missing tags, zero prior, restatements (deferred)

---

### Phase 3 — Postgres

**Goal:** Persist reports and debriefs; cache results to avoid repeat SEC + LLM calls.

#### 3.1 Supabase Postgres

Create a [Supabase](https://supabase.com) project and add to `backend/.env`:

```env
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

Use the **connection pooler** URL (port 6543) for the app and playground scripts. For Alembic migrations, use the **direct** connection string (port 5432) if `alembic upgrade head` fails through the pooler.

```bash
cd backend
alembic upgrade head
```

#### 3.2 Database schema (3 tables)

```mermaid
erDiagram
    Company ||--o{ Report : has
    Report ||--|| Debrief : has

    Company {
        int id PK
        string ticker
        string name
        string cik
    }

    Report {
        int id PK
        int company_id FK
        string period_type
        date period_end
        date prior_period_end
        jsonb yoy_data
        string filing_date
        datetime created_at
    }

    Debrief {
        int id PK
        int report_id FK
        jsonb debrief_json
        string model_used
        datetime created_at
    }
```

**What we store:** companies, computed YoY reports, LLM debriefs.

**What we do NOT store:** raw SEC responses, user accounts, analyst estimates.

**Cache invalidation:** when SEC submissions show a newer filing, generate a new report. Old reports stay in history.

#### 3.3 SQLAlchemy models + Alembic

Files:
- `backend/app/db/database.py` — engine, session factory
- `backend/app/db/models.py` — `Company`, `Report`, `Debrief` ORM models
- `backend/alembic/` — initial migration

```bash
cd backend
alembic upgrade head
```

#### 3.4 Report service (save/load/cache)

File: `backend/app/services/report_service.py`

Orchestration logic:
1. Check Postgres for existing report matching ticker + latest filing date
2. If fresh cache hit → return cached report (+ debrief in Phase 4)
3. If miss → fetch SEC → compute YoY → save report → (Phase 4) generate debrief → save debrief

Validate cache behavior:

```bash
cd backend
uv run python playground/test_report_service.py
```

First run prints `cached: false`; second run prints `cached: true`.

**Phase 3 checklist:**
- [x] Supabase Postgres connected (`DATABASE_URL` in `.env`)
- [x] SQLAlchemy models for Company, Report, Debrief
- [x] Alembic migration applied
- [x] Report service with cache hit/miss logic
- [x] Playground smoke test (`playground/test_report_service.py`)

---

### Phase 4 — LLM Debrief Agent

**Goal:** Generate a structured earnings narrative from the computed YoY data.

**Golden rule: the LLM never does math.** It only interprets numbers already computed by Python.

#### 4.1 Define the structured output schema

File: `backend/app/models/debrief.py`

```python
from pydantic import BaseModel
from typing import Literal

class MetricHighlight(BaseModel):
    metric: str                    # e.g. "Revenue"
    trend: Literal["up", "down", "flat"]
    summary: str                   # 1-2 sentences using ONLY provided numbers

class EarningsDebrief(BaseModel):
    headline: str                  # One-line summary of the quarter
    overall_assessment: Literal["strong", "mixed", "weak"]
    revenue_analysis: MetricHighlight
    margin_analysis: str           # Gross/operating margin direction
    expense_analysis: list[MetricHighlight]  # R&D, SG&A, OpEx trends
    key_takeaways: list[str]       # 3-5 bullets
    items_to_watch: list[str]      # 1-3 things to monitor next quarter
```

#### 4.2 Build the debrief agent

File: `backend/app/services/debrief_agent.py`

**System prompt:**
- "You are an earnings analyst. Interpret the provided YoY data."
- "Do not invent numbers. Every figure you cite must appear in the input JSON."
- "Focus on what changed and why it might matter operationally."

**User message:** the serialized YoY report JSON from Phase 2.

**Provider:** OpenAI (`gpt-4o-mini`) with sync structured output via the official `openai` SDK (Pydantic parsing — no `instructor`).

#### 4.3 Wire into report service

Update `report_service.py`:

```
SEC fetch → YoY calc → save Report → LLM debrief → save Debrief → return
```

Debrief is stored on the **quarterly** `Report` row. Cache hit returns saved debrief; YoY cached without debrief backfills on read.

#### 4.4 Validate with playground

```bash
cd backend
# Direct: OpenAI only, uses artifacts/AMZN_*.json
uv run python playground/test_debrief.py

# Full pipeline: SEC + Postgres + OpenAI (Run 1 generates, Run 2 caches)
uv run python playground/test_debrief.py --integration
```

Requires `OPENAI_API_KEY` in `.env`.

**Phase 4 checklist:**
- [x] Pydantic `EarningsDebrief` schema
- [x] Prompt template (system + user message)
- [x] OpenAI integration with structured output (sync)
- [x] Wired into report service pipeline
- [x] Playground smoke test (`playground/test_debrief.py`)

---

### Phase 5 — API + Frontend

**Goal:** Expose endpoints and build the UI.

#### 5.1 FastAPI routes

Files: [`backend/app/routes/search.py`](backend/app/routes/search.py), [`backend/app/routes/reports.py`](backend/app/routes/reports.py), [`backend/app/routes/deps.py`](backend/app/routes/deps.py)

| Endpoint | Purpose |
|---|---|
| `GET /api/search?q=amazon` | Autocomplete tickers/names |
| `GET /api/report?ticker=AMZN` | YoY report + debrief (uses cache if fresh) |
| `GET /api/report?ticker=AMZN&refresh=true` | Force re-fetch + new debrief |
| `GET /api/report?ticker=AMZN&filing_date=2026-07-31` | Load a historical snapshot from Postgres |
| `GET /api/history?ticker=AMZN` | Past reports for this company |

Response includes YoY sections (`quarterly`, `annual`) and `debrief` in one payload.

```bash
cd backend
uv run uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

#### 5.2 React frontend

**Stack:** Vite SPA, React 19, strict TypeScript, Tailwind CSS, native `fetch` (no Axios). Package manager is **pnpm** only.

**Key files:**
- [`frontend/src/lib/env.ts`](frontend/src/lib/env.ts) — validates `VITE_API_BASE_URL` at startup (single env boundary)
- [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) — typed HTTP client
- [`frontend/src/lib/types/`](frontend/src/lib/types/) — shared API/application types
- Components under [`frontend/src/components/`](frontend/src/components/)

| Component | Purpose |
|---|---|
| `SearchBar.tsx` | Ticker/company search with autocomplete |
| `YoYTable.tsx` | Quarterly + annual tables (Metric, Current, Prior, $ Change, % Change) |
| `DebriefPanel.tsx` | Headline, assessment badge, analysis cards, takeaways, watch items |
| `ReportHistory.tsx` | Past analyses for the same ticker |
| `ReportHeader.tsx` | Company meta + refresh |
| `StatusBanner.tsx` | Loading and error banners |

In dev, leave `VITE_API_BASE_URL` empty — Vite proxies `/api` → `http://localhost:8000`.

```bash
# from repo root
pnpm install --frozen-lockfile
cd frontend
pnpm run dev
# UI at http://localhost:5173
```

**Production:** set `VITE_API_BASE_URL` to your deployed FastAPI origin (no trailing slash). See [`frontend/.env.example`](frontend/.env.example) and [`frontend/.env.production`](frontend/.env.production).

#### 5.3 First end-to-end test

Run **both** servers (two terminals):

```bash
# Terminal 1 — backend
cd backend
uv run uvicorn app.main:app --reload

# Terminal 2 — frontend (from repo root)
pnpm install --frozen-lockfile
cd frontend
pnpm run dev
```

Then open http://localhost:5173, search **AMZN**, and confirm:
1. Quarterly + annual YoY tables render
2. Earnings debrief panel appears below
3. History sidebar lists past runs (after a second lookup or refresh)
4. **Refresh** forces a new SEC fetch + debrief

First run may take ~10–30s (SEC + OpenAI). Repeat lookup should be much faster (cache hit).

**Phase 5 checklist:**
- [x] API endpoints working (`/api/search`, `/api/report`, `/api/history`)
- [x] React search bar + YoY tables
- [x] Debrief panel with structured output
- [x] Report history sidebar
- [x] Loading and error states

---

### Phase 6 — Polish + Verify

**Goal:** Make it reliable and spot-check against real filings.

#### 6.1 End-to-end test

- Enter `AMZN` → YoY tables + debrief in under ~10 seconds (first run), ~1 second (cached)
- Spot-check YoY numbers against the latest Amazon 10-Q/10-K
- Repeat for AAPL, MSFT, GOOGL, NVDA

#### 6.2 Verify debrief quality

- Debrief cites only numbers from the YoY report — no hallucinated figures
- Takeaways are relevant and specific to the company's actual performance

#### 6.3 Run the test suite

```bash
cd backend && pytest -v
```

**Phase 6 checklist:**
- [ ] 5+ large-cap tickers work without manual tag fixes
- [ ] Cached reports return instantly
- [ ] All tests pass
- [ ] Manual spot-check against SEC filings

---

## Project Structure (Target)

```
Earnings_Helper/
├── pnpm-workspace.yaml
├── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── settings.py
│   │   │   └── load_metrics.py
│   │   ├── routes/
│   │   │   ├── deps.py
│   │   │   ├── reports.py
│   │   │   └── search.py
│   │   ├── services/
│   │   │   ├── ingest.py
│   │   │   ├── resolver.py
│   │   │   ├── extractor.py
│   │   │   ├── yoy_calculator.py
│   │   │   ├── debrief_agent.py
│   │   │   └── report_service.py
│   │   ├── models/
│   │   │   ├── report.py
│   │   │   └── debrief.py
│   │   └── db/
│   │       ├── database.py
│   │       └── models.py
│   ├── alembic/
│   ├── config/
│   │   └── metrics.yaml
│   ├── playground/
│   │   ├── test_ingest.py
│   │   ├── test_yoy.py
│   │   ├── test_report_service.py
│   │   └── test_debrief.py
│   ├── artifacts/          # gitignored; one JSON per YoY run for spot-checks
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── YoYTable.tsx
│   │   │   ├── DebriefPanel.tsx
│   │   │   ├── ReportHistory.tsx
│   │   │   ├── ReportHeader.tsx
│   │   │   └── StatusBanner.tsx
│   │   └── lib/
│   │       ├── env.ts
│   │       ├── api.ts
│   │       ├── format.ts
│   │       ├── sec.ts
│   │       └── types/
│   ├── .env.example
│   ├── .env.production     # template for production builds
│   └── package.json
└── README.md
```

---

## Running Locally (Once Built)

```bash
# 1. Apply database schema (Supabase DATABASE_URL in backend/.env)
cd backend
cp .env.example .env   # fill in SEC_USER_AGENT and DATABASE_URL
uv sync
alembic upgrade head

# 2. Start backend API
uv run uvicorn app.main:app --reload

# 3. Start frontend (separate terminal, from repo root)
pnpm install --frozen-lockfile
cd frontend
cp .env.example .env   # optional for dev; empty VITE_API_BASE_URL uses the Vite proxy
pnpm run dev
```
Open http://localhost:5173, search for a ticker, and view the YoY report + debrief.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `SEC_USER_AGENT` | Contact string for SEC API (required by SEC policy) |
| `DATABASE_URL` | Postgres connection string |
| `OPENAI_API_KEY` | OpenAI API key for LLM debrief |
| `OPENAI_MODEL` | OpenAI model (optional, defaults to `gpt-4o-mini`) |

### Frontend (`frontend/.env` or host env)

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Public FastAPI origin for production builds (e.g. `https://api.yourdomain.com`). Leave empty in dev to use the Vite `/api` proxy. Never put secrets here — only `VITE_*` vars are exposed to the browser. |

---

## Tech Dependencies

**Backend:** `fastapi`, `uvicorn`, `httpx`, `pydantic`, `pyyaml`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `openai`, `pytest`, `pytest-asyncio`

**Frontend:** `react`, `vite`, `typescript`, `tailwindcss`, `@tailwindcss/vite` — managed with **pnpm** (exact-pinned direct deps; commit `pnpm-lock.yaml`)

**Infra:** Supabase (Postgres)

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM invents numbers | Structured output + prompt rule: cite only input JSON |
| LLM latency (2–5s) | Progressive loading UI; cache debriefs in Postgres |
| LLM cost | Cache by filing date; only re-call on `refresh=true` |
| Companies use different XBRL tags | Fallback tag list in `metrics.yaml` |
| SEC rate limiting | In-memory cache; respect 10 req/s |
| Fiscal calendars differ | Match on `end` date, not calendar assumptions |

---

## Success Criteria

- [ ] Enter `AMZN` → YoY tables + structured LLM debrief in under ~10s (first run), ~1s (cached)
- [ ] YoY numbers match latest 10-Q/10-K (manual spot-check)
- [ ] Debrief cites only numbers from the YoY report
- [ ] Past reports visible in history for same ticker
- [ ] Works for 5+ large-cap tickers without manual tag fixes

---

## Extending It (v2 Ideas)

- **Custom metrics** — add line items to `metrics.yaml` without code changes
- **Segment breakdowns** — AWS revenue, North America revenue (harder; tags vary by company)
- **Earnings press releases** — parse 8-K HTML with LLM for data not yet in XBRL
- **Analyst estimates** — compare actual vs consensus (requires additional data source)
- **Swap LLM provider** — Anthropic, local models, etc.
- **Export** — PDF or CSV download of report + debrief

