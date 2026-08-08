import { useCallback, useState } from 'react'
import { ExternalLinkIcon } from 'lucide-react'

import AppHeader from './components/AppHeader'
import DebriefPanel from './components/DebriefPanel'
import LandingHero from './components/LandingHero'
import ReportLoadingSkeleton from './components/ReportLoadingSkeleton'
import ReportProgressLog from './components/ReportProgressLog'
import ReportSummary from './components/ReportSummary'
import YoYTable from './components/YoYTable'
import { fetchReportStream } from './lib/api'
import { secEdgarUrl } from './lib/sec'
import type { ProgressStep, Report } from './lib/types'

type LoadState = 'idle' | 'loading' | 'error' | 'success'

function appendProgressStep(steps: ProgressStep[], message: string): ProgressStep[] {
  return [
    ...steps.map((step) => ({ ...step, status: 'done' as const })),
    { id: crypto.randomUUID(), message, status: 'active' },
  ]
}

export default function App() {
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([])

  const loadReport = useCallback(
    async (ticker: string, options?: { refresh?: boolean }) => {
      setLoadState('loading')
      setError(null)
      setProgressSteps([])

      try {
        const data = await fetchReportStream(ticker, options, (message) => {
          setProgressSteps((prev) => appendProgressStep(prev, message))
        })
        setProgressSteps((prev) => prev.map((step) => ({ ...step, status: 'done' })))
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
  const showProgress = isLoading || (loadState === 'error' && progressSteps.length > 0)

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
            {showProgress && (
              <div className="mb-6">
                <ReportProgressLog steps={progressSteps} />
              </div>
            )}

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
