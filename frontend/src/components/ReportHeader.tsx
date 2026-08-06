import type { Report } from '../lib/types'

interface ReportHeaderProps {
  report: Report
  onRefresh: () => void
  refreshDisabled: boolean
}

export default function ReportHeader({
  report,
  onRefresh,
  refreshDisabled,
}: ReportHeaderProps) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4 rounded-xl border border-border bg-bg px-5 py-4 shadow-[var(--shadow-card)]">
      <div>
        <h2 className="mb-1 text-2xl text-text-heading">
          {report.ticker} — {report.company}
        </h2>
        <p className="text-sm text-text">
          Filing date: {report.filing_date}
          {report.cached && ' · cached'}
          {report.debrief_cached && ' · debrief cached'}
        </p>
      </div>
      <button
        type="button"
        className="cursor-pointer rounded-lg border border-accent bg-bg px-3.5 py-2 font-[inherit] text-accent hover:bg-accent-bg disabled:cursor-not-allowed disabled:opacity-60"
        onClick={onRefresh}
        disabled={refreshDisabled}
      >
        Refresh
      </button>
    </div>
  )
}
