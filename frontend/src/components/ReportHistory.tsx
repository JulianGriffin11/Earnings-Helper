import { formatDate } from '../lib/format'
import type { HistoryItem } from '../lib/types'

interface ReportHistoryProps {
  items: HistoryItem[]
  activeFilingDate?: string
  onSelect: (filingDate: string) => void
}

export default function ReportHistory({
  items,
  activeFilingDate,
  onSelect,
}: ReportHistoryProps) {
  if (items.length === 0) {
    return (
      <aside className="overflow-hidden rounded-xl border border-border bg-bg shadow-[var(--shadow-card)]">
        <div className="border-b border-border bg-surface px-4 py-3">
          <h2 className="m-0 text-lg text-text-heading">History</h2>
        </div>
        <p className="p-4 text-sm text-text">No past reports yet.</p>
      </aside>
    )
  }

  return (
    <aside className="overflow-hidden rounded-xl border border-border bg-bg shadow-[var(--shadow-card)]">
      <div className="border-b border-border bg-surface px-4 py-3">
        <h2 className="m-0 text-lg text-text-heading">History</h2>
      </div>
      <ul className="m-0 list-none p-2">
        {items.map((item) => {
          const isActive = item.filing_date === activeFilingDate
          return (
            <li key={item.report_id} className="mt-1 first:mt-0">
              <button
                type="button"
                className={`flex w-full cursor-pointer flex-col items-start gap-0.5 rounded-lg border px-3 py-2.5 text-left font-[inherit] hover:border-accent-border hover:bg-accent-bg ${
                  isActive
                    ? 'border-accent bg-accent-bg text-text-heading'
                    : 'border-transparent bg-transparent text-text-heading'
                }`}
                onClick={() => onSelect(item.filing_date)}
              >
                <span className="font-semibold text-accent">
                  Filed {item.filing_date}
                </span>
                {item.period_end && (
                  <span className="text-xs text-text">Period {item.period_end}</span>
                )}
                <span className="text-xs text-text">
                  {formatDate(item.created_at)}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
