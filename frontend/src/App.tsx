import { useCallback, useState } from 'react'
import { AlertCircleIcon, ExternalLinkIcon } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import AppHeader from './components/AppHeader'
import DebriefPanel from './components/DebriefPanel'
import KpiGrid from './components/KpiGrid'
import LandingHero from './components/LandingHero'
import ReportLoadingSkeleton from './components/ReportLoadingSkeleton'
import ReportProgressLog from './components/ReportProgressLog'
import ReportSummary from './components/ReportSummary'
import YoYTable from './components/YoYTable'
import { fetchReportStream } from './lib/api'
import { readRecent, rememberRecent, type RecentTicker } from './lib/recent'
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
  const [exactFigures, setExactFigures] = useState(false)
  const [recent, setRecent] = useState<RecentTicker[]>(readRecent)

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
        setRecent(rememberRecent(data.ticker, data.company))
        setLoadState('success')
      } catch (err) {
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
  const hasReport = !isLoading && report
  const showLanding = !report && (loadState === 'idle' || loadState === 'error')
  const progressMode = isLoading ? 'loading' : loadState === 'error' ? 'error' : 'success'
  const showProgress = progressSteps.length > 0 && !showLanding

  return (
    <div className="flex min-h-svh flex-col">
      {showLanding ? (
        <LandingHero
          onSelect={handleSelect}
          disabled={isLoading}
          error={loadState === 'error' ? error : null}
          recent={recent}
          progressSteps={progressSteps}
        />
      ) : (
        <>
          <AppHeader
            onSelect={handleSelect}
            disabled={isLoading}
            activeTicker={report?.ticker ?? null}
            recent={recent}
          />

          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 lg:px-6">
            {loadState === 'error' && error && report && (
              <Alert variant="destructive" className="mb-6">
                <AlertCircleIcon />
                <AlertTitle>Failed to load report</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {showProgress && (
              <div className="mb-6">
                <ReportProgressLog steps={progressSteps} mode={progressMode} />
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

                <KpiGrid
                  section={report.quarterly}
                  exact={exactFigures}
                  onExactChange={setExactFigures}
                />

                <YoYTable
                  title="Quarterly YoY"
                  section={report.quarterly}
                  compact={false}
                />
                <YoYTable
                  title="Annual YoY"
                  section={report.annual}
                  compact={false}
                />
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
