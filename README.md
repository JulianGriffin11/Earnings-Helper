# Earnings Helper

This is a income statement analysis for public companies. Search a ticker, pull their SEC data, compute the changes in Python, and show a short debrief of what moved.

## Why I Built This 💡

A local company wanted a faster to read an earnings report. Instead of hunting through a filing for which lines changed, he wanted the year-over-year numbers calculated first, then a short explanation of what those changes mean.

## How It Works

```text
        Search Ticker
              ↓
          SEC Facts
              ↓
     Python Calculations
              ↓
          PostgreSQL
              ↓
         LLM debrief
              ↓
        Visual Report
```

Enter a ticker. The app, pulls structured facts from the SEC, and computes quarterly and annual year-over-year changes in Python. Postgres caches the report for the latest filing. The model writes a debrief from those numbers. One Render deployment using React UI and the API together.

## Tech Stack 🛠️


| Technology   | Purpose                                       |
| ------------ | --------------------------------------------- |
| React / Vite | Search page and report UI                     |
| Python       | SEC fetch, YoY calculation, and orchestration |
| PostgreSQL   | Cached reports and debriefs                   |
| OpenAI API   | Earnings debrief                              |
| Render       | Deployment and UI                             |




## AI Pipeline 🤖

Python and SQL handle fetching, period selection, storage, and the arithmetic. The LLM is used only to interpret numbers the code already computed.

1. Compute the quarterly and annual year-over-year rows
2. Write a debrief that explains what moved

Model output is returned as structured JSON so the application can store it and render the debrief in code. The model does not calculate percentages.

## Database 🗄️

PostgreSQL stores the company, the quarterly and annual report, and the debrief. A repeat lookup for the latest filing is served from cache when the stored period is still current.

## Analyst export 📊

A report download builds an Excel workbook from two views. The views flatten the JSON on `reports` and `debriefs` into columns. Alembic creates them in the same database as the app (`alembic upgrade head` from `backend/`, using the direct Postgres URL on port 5432).

`analyst_yoy` has one row per company, period, and metric:

| Column | Meaning |
| --- | --- |
| ticker, company | Company identity |
| period_type | `quarterly` or `annual` |
| period_end, prior_period_end, filing_date | Period pair and filing |
| metric | Revenue, Operating Expenses, Gross Profit, or Net Income |
| current_amount, prior_amount, dollar_change | Dollar amounts from the filing |
| pct_change | Percentage points. `9.63` means 9.63% |
| metric_order | Line-item order inside the filing |

`analyst_debrief` has one row per quarterly debrief: ticker, company, filing_date, headline, overall_assessment, margin_analysis, takeaways, items_to_watch. Takeaways and items to watch are newline-separated text.

**Excel.** On a report, Download Excel requests `GET /api/reports/{ticker}/export.xlsx`. The workbook is built in memory from those views for that ticker. The YoY and Debrief sheets are Excel tables when they have rows. Dollar columns use a number format. Percent change keeps the same percentage-point value as `pct_change`.

**Power BI.** In Power BI Desktop, get data from PostgreSQL and import `analyst_yoy` and `analyst_debrief`. Use the direct database host on port 5432 with SSL, and a read-only login. Relate the tables on ticker and filing_date. Suggested visuals: ticker and period_type slicers, a bar of pct_change by metric, a card for overall_assessment, and a table of the amount columns.

A demo that cannot reach the database can use Get Data on the downloaded workbook. That file is a snapshot of one ticker. A later earnings pull updates the views, and Power BI picks up the new rows on its own refresh. This app does not call Power BI when a filing is saved.

## What I Learned 📚

Building this was less about the model call and more about the pipeline around it. SEC filings do not all use the same tags, and the year-over-year math has to stay in code so the debrief is explaining numbers that can be checked.

Predictable work belongs in Python. Fetching, period selection, arithmetic, and caching stay deterministic. The model is reserved for the written debrief.

## Future Improvements 🚀

- Expanding of the line items tag (i.e. COGS, SG&A, etc)
- Show when a cached report is stale relative to a new filing
- Add clearer empty states when a metric tag is missing
- Power BI service refresh stays on a schedule in Power BI. See Analyst export for the views and the workbook fallback.



## Project Status ✅

The report pipeline is built: search, SEC facts, year-over-year tables, a cached Postgres report, an LLM debrief, and an Excel download of the analyst views. It is set up to deploy as one Render web service. 
