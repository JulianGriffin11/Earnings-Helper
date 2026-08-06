import { useCallback, useState } from 'react'

import DebriefPanel from './components/DebriefPanel'
import ReportHeader from './components/ReportHeader'
import ReportHistory from './components/ReportHistory'
import SearchBar from './components/SearchBar'
import StatusBanner from './components/StatusBanner'
import YoYTable from './components/YoYTable'
import { fetchHistory, fetchReport } from './lib/api'
import { secEdgarUrl } from './lib/sec'
import type { HistoryItem, Report } from './lib/types'

type LoadState = 'idle' | 'loading' | 'error' | 'success'

export default function App() {
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)
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

  const isLoading = loadState === 'loading'
  const hasReport = loadState === 'success' && report

  return (
    <div className="px-6 py-10 pb-16">
      <header className="mx-auto mb-10 flex max-w-2xl flex-col items-center text-center">
        <h1 className="mb-2 text-accent">Earnings Helper</h1>
        <p className="mb-6 text-text">
          Earnings debrief validated from SEC filings
        </p>
        <div className="w-full">
          <SearchBar onSelect={handleSelect} disabled={isLoading} />
        </div>
      </header>

      <div className="mx-auto max-w-5xl">
        {isLoading && (
          <StatusBanner variant="loading" message="Loading report..." />
        )}

        {loadState === 'error' && error && (
          <StatusBanner variant="error" message={error} />
        )}

        {hasReport && (
          <main>
            <ReportHeader
              report={report}
              onRefresh={handleRefresh}
              refreshDisabled={isLoading}
            />

            <div className="grid items-start gap-6 max-[900px]:grid-cols-1 grid-cols-[1fr_240px]">
              <div className="flex flex-col gap-6">
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

            <footer className="mt-8 border-t border-border pt-4">
              <a
                className="font-medium text-accent hover:text-accent-hover hover:underline"
                href={secEdgarUrl(report.cik)}
                target="_blank"
                rel="noreferrer"
              >
                View SEC filings
              </a>
            </footer>
          </main>
        )}

        {loadState === 'idle' && (
          <p className="text-center text-text">
            Search for a company to get started.
          </p>
        )}
      </div>
    </div>
  )
}
