import { useCallback, useState } from 'react'
import { ExternalLinkIcon } from 'lucide-react'

import AppHeader from './components/AppHeader'
import DebriefPanel from './components/DebriefPanel'
import LandingHero from './components/LandingHero'
import ReportLoadingSkeleton from './components/ReportLoadingSkeleton'
import ReportSummary from './components/ReportSummary'
import YoYTable from './components/YoYTable'
import { fetchReport } from './lib/api'
import { secEdgarUrl } from './lib/sec'
import type { Report } from './lib/types'

type LoadState = 'idle' | 'loading' | 'error' | 'success'

export default function App() {
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)

  const loadReport = useCallback(
    async (ticker: string, options?: { refresh?: boolean }) => {
      setLoadState('loading')
      setError(null)

      try {
        const data = await fetchReport(ticker, options)
        setReport(data)
        setLoadState('success')
      } catch (err) {
        setReport(null)
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

  const isLoading = loadState === 'loading'
  const hasReport = loadState === 'success' && report
  const showLanding = loadState === 'idle' || (loadState === 'error' && !report)

  return (
    <div className="flex min-h-svh flex-col">
      {showLanding ? (
        <LandingHero
          onSelect={handleSelect}
          disabled={isLoading}
          error={loadState === 'error' ? error : null}
        />
      ) : (
        <>
          <AppHeader
            onSelect={handleSelect}
            disabled={isLoading}
            activeTicker={report?.ticker ?? null}
          />

          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 lg:px-6">
            {isLoading && <ReportLoadingSkeleton />}

            {hasReport && (
              <div className="flex flex-col gap-6">
                <ReportSummary
                  report={report}
                  onRefresh={handleRefresh}
                  refreshDisabled={isLoading}
                />

                <YoYTable title="Quarterly YoY" section={report.quarterly} />
                <YoYTable title="Annual YoY" section={report.annual} />
                <DebriefPanel debrief={report.debrief} />

                <footer className="border-t pt-4">
                  <a
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                    href={secEdgarUrl(report.cik)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View SEC filings
                    <ExternalLinkIcon className="size-3.5" />
                  </a>
                </footer>
              </div>
            )}
          </main>
        </>
      )}
    </div>
  )
}
