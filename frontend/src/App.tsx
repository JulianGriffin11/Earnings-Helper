import { useCallback, useState } from 'react'

import {
  fetchHistory,
  fetchReport,
  secEdgarUrl,
  type HistoryItem,
  type ReportResponse,
} from './api/client'
import DebriefPanel from './components/DebriefPanel'
import ReportHistory from './components/ReportHistory'
import SearchBar from './components/SearchBar'
import YoYTable from './components/YoYTable'
import './App.css'

type LoadState = 'idle' | 'loading' | 'error' | 'success'

export default function App() {
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])

  const loadReport = useCallback(
    async (ticker: string, options?: { refresh?: boolean; filingDate?: string }) => {
      setLoadState('loading')
      setError(null)

      try {
        const data = await fetchReport(ticker, options)
        setReport(data)

        try {
          const historyData = await fetchHistory(data.ticker)
          setHistory(historyData.items)
        } catch {
          setHistory([])
        }

        setLoadState('success')
      } catch (err) {
        setReport(null)
        setHistory([])
        setError(err instanceof Error ? err.message : 'Failed to load report')
        setLoadState('error')
      }
    },
    [],
  )

  function handleSelect(ticker: string) {
    loadReport(ticker)
  }

  function handleRefresh() {
    if (!report) return
    loadReport(report.ticker, { refresh: true })
  }

  function handleHistorySelect(filingDate: string) {
    if (!report) return
    loadReport(report.ticker, { filingDate })
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Earnings Helper</h1>
        <p className="tagline">YoY analysis and earnings debrief from SEC filings</p>
        <SearchBar onSelect={handleSelect} disabled={loadState === 'loading'} />
      </header>

      {loadState === 'loading' && (
        <div className="status-banner loading">Loading report...</div>
      )}

      {loadState === 'error' && error && (
        <div className="status-banner error">{error}</div>
      )}

      {loadState === 'success' && report && (
        <main className="app-main">
          <div className="report-meta">
            <div>
              <h2>
                {report.ticker} — {report.company}
              </h2>
              <p className="muted">
                Filing date: {report.filing_date}
                {report.cached && ' · cached'}
                {report.debrief_cached && ' · debrief cached'}
              </p>
            </div>
            <button type="button" className="refresh-btn" onClick={handleRefresh}>
              Refresh
            </button>
          </div>

          <div className="content-grid">
            <div className="main-column">
              <YoYTable title="Quarterly YoY" section={report.quarterly} />
              <YoYTable title="Annual YoY" section={report.annual} />
              <DebriefPanel debrief={report.debrief} />
            </div>
            <ReportHistory
              items={history}
              activeFilingDate={report.filing_date}
              onSelect={handleHistorySelect}
            />
          </div>

          <footer className="app-footer">
            <a href={secEdgarUrl(report.cik)} target="_blank" rel="noreferrer">
              View SEC filings
            </a>
          </footer>
        </main>
      )}

      {loadState === 'idle' && (
        <p className="empty-state">Search for a company to get started.</p>
      )}
    </div>
  )
}
