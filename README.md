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
| Database | Postgres via Docker | Cache LLM debriefs + report history without over-engineering |
| Backend | Python + FastAPI | Async-friendly; Pydantic shared across API, LLM, and DB |
| Frontend | React (Vite) | Search bar, YoY tables, debrief panel, report history |

---

## Prerequisites

Before building, install:

- **Python 3.11+**
- **Node.js 18+** (for the React frontend)
- **Docker Desktop** (for Postgres)
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
mkdir -p backend/app/{routes,services,models,db} backend/config backend/tests/fixtures
cd backend
# Create pyproject.toml with: fastapi, uvicorn, httpx, pydantic, pyyaml, pytest
```

Create `.env.example`:

```env
SEC_USER_AGENT=EarningsHelper your-email@example.com
DATABASE_URL=postgresql://earnings:earnings@localhost:5432/earnings_helper
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

#### 1.5 Test with Amazon

```bash
# Prove it works: fetch AMZN revenue history
pytest backend/tests/test_sec_client.py -v
```

Save a frozen copy of the SEC JSON response in `backend/tests/fixtures/amzn_revenues.json` so tests don't hit the live API.

**Phase 1 checklist:**
- [x] SEC client with User-Agent and caching
- [x] Ticker/name → CIK resolution
- [x] Fetch one XBRL concept for one company
- [ ] Unit test with frozen fixture

---

### Phase 2 — YoY Engine

**Goal:** Compute quarterly and annual YoY changes for all standard line items.

#### 2.1 Create metrics config

File: `backend/config/metrics.yaml`

| Display Label | Primary XBRL Tag | Fallback Tags |
|---|---|---|
| Revenue | `Revenues` | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet` |
| Cost of Revenue | `CostOfRevenue` | `CostOfGoodsAndServicesSold` |
| Gross Profit | `GrossProfit` | derived: Revenue − COGS if missing |
| R&D | `ResearchAndDevelopmentExpense` | — |
| SG&A | `SellingGeneralAndAdministrativeExpense` | — |
| Total OpEx | `OperatingExpenses` | — |
| Operating Income | `OperatingIncomeLoss` | — |
| Net Income | `NetIncomeLoss` | `NetIncomeLossAvailableToCommonStockholdersBasic` |

#### 2.2 Build the YoY calculator

File: `backend/app/services/yoy_calculator.py`

**Quarterly YoY (10-Q):**
- Find the most recently filed quarter (e.g. `fp=Q3`, `end=2025-09-30`)
- Find the same fiscal quarter one year prior (`end=2024-09-30`)
- Compute for each metric:
  - `delta = current - prior`
  - `pct_change = (current / prior - 1) * 100` (handle `prior == 0` safely)

**Annual YoY (10-K):**
- Same logic using `form=10-K` and `fp=FY`

**Normalization rules (critical — prevents bad numbers):**
1. Match periods by `end` date, not just `fy`
2. Prefer duration facts (`start` + `end` present) over instant facts
3. On duplicates, keep the latest `filed` date (handles restatements)
4. Try primary XBRL tag first, then fallbacks — never mix tags across periods
5. Validate: value exists, units are USD, form type matches

Example output:

```json
{
  "company": "Amazon.com Inc.",
  "cik": "0001018724",
  "ticker": "AMZN",
  "as_of_filing": "2025-10-31",
  "quarterly": {
    "period_end": "2025-09-30",
    "prior_period_end": "2024-09-30",
    "metrics": [
      {
        "label": "Revenue",
        "current": 180000000000,
        "prior": 158000000000,
        "delta": 22000000000,
        "pct_change": 13.9
      }
    ]
  },
  "annual": { "..." : "..." }
}
```

#### 2.3 Test the calculator

```bash
pytest backend/tests/test_yoy_calculator.py -v
```

Test with fixtures for AMZN and AAPL. Spot-check output against the actual 10-Q/10-K.

**Phase 2 checklist:**
- [ ] `metrics.yaml` with 8 line items + fallback tags
- [ ] Quarterly YoY matching by `end` date
- [ ] Annual YoY matching
- [ ] Edge cases: missing tags, zero prior, restatements
- [ ] Unit tests with frozen fixtures

---

### Phase 3 — Postgres

**Goal:** Persist reports and debriefs; cache results to avoid repeat SEC + LLM calls.

#### 3.1 Docker Compose for Postgres

File: `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: earnings
      POSTGRES_PASSWORD: earnings
      POSTGRES_DB: earnings_helper
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```bash
docker compose up -d
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
alembic init alembic
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

#### 3.4 Report service (save/load/cache)

File: `backend/app/services/report_service.py`

Orchestration logic:
1. Check Postgres for existing report matching ticker + latest filing date
2. If fresh cache hit → return cached report + debrief
3. If miss → fetch SEC → compute YoY → save report → (Phase 4) generate debrief → save debrief

**Phase 3 checklist:**
- [ ] Docker Compose Postgres running
- [ ] SQLAlchemy models for Company, Report, Debrief
- [ ] Alembic migration applied
- [ ] Report service with cache hit/miss logic

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

**Provider:** OpenAI (`gpt-4o-mini`) with structured output / JSON mode, or Anthropic with tool use. Use the `instructor` library or native Pydantic parsing.

#### 4.3 Wire into report service

Update `report_service.py`:

```
SEC fetch → YoY calc → save Report → LLM debrief → save Debrief → return
```

#### 4.4 Test with mocked LLM

```bash
pytest backend/tests/test_debrief_agent.py -v
```

Mock the LLM response in tests — don't call the live API in CI.

**Phase 4 checklist:**
- [ ] Pydantic `EarningsDebrief` schema
- [ ] Prompt template (system + user message)
- [ ] OpenAI/Anthropic integration with structured output
- [ ] Wired into report service pipeline
- [ ] Unit tests with mocked LLM responses

---

### Phase 5 — API + Frontend

**Goal:** Expose endpoints and build the UI.

#### 5.1 FastAPI routes

Files: `backend/app/routes/search.py`, `backend/app/routes/reports.py`

| Endpoint | Purpose |
|---|---|
| `GET /api/search?q=amazon` | Autocomplete tickers/names |
| `GET /api/report?ticker=AMZN` | YoY report + debrief (uses cache if fresh) |
| `GET /api/report?ticker=AMZN&refresh=true` | Force re-fetch + new debrief |
| `GET /api/history?ticker=AMZN` | Past reports for this company |
| `GET /api/health` | Health check |

Response includes both `yoy_data` and `debrief` in one payload.

```bash
cd backend
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

#### 5.2 React frontend

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

Components:
- `SearchBar.tsx` — ticker or company name input
- `YoYTable.tsx` — quarterly + annual tables (Metric, Current, Prior, $ Change, % Change)
- `DebriefPanel.tsx` — headline, assessment badge, takeaways, watch items
- `ReportHistory.tsx` — past analyses for the same ticker

UI flow:
1. User searches → loading: "Fetching SEC data..."
2. YoY tables render → loading: "Generating debrief..."
3. Debrief panel renders
4. Footer: SEC filing link + "Generated at" timestamp

```bash
cd frontend
npm run dev
# UI at http://localhost:5173
```

**Phase 5 checklist:**
- [ ] All API endpoints working
- [ ] React search bar + YoY tables
- [ ] Debrief panel with structured output
- [ ] Report history sidebar/dropdown
- [ ] Loading and error states

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
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
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
│   ├── tests/
│   │   └── fixtures/
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── YoYTable.tsx
│   │   │   ├── DebriefPanel.tsx
│   │   │   └── ReportHistory.tsx
│   │   └── api/client.ts
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Running Locally (Once Built)

```bash
# 1. Start Postgres
docker compose up -d

# 2. Set up backend
cd backend
cp .env.example .env   # fill in your keys
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# 3. Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```
Open http://localhost:5173, search for a ticker, and view the YoY report + debrief.

---

## Environment Variables

| Variable | Description |
|---|---|
| `SEC_USER_AGENT` | Contact string for SEC API (required by SEC policy) |
| `DATABASE_URL` | Postgres connection string |
| `OPENAI_API_KEY` | OpenAI API key for LLM debrief |

---

## Tech Dependencies

**Backend:** `fastapi`, `uvicorn`, `httpx`, `pydantic`, `pyyaml`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `openai`, `pytest`, `pytest-asyncio`

**Frontend:** `react`, `vite`, `typescript`

**Infra:** Docker Compose (Postgres)

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

