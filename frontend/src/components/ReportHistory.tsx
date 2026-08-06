import type { HistoryItem } from '../api/client'

interface ReportHistoryProps {
  items: HistoryItem[]
  activeFilingDate?: string
  onSelect: (filingDate: string) => void
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function ReportHistory({
  items,
  activeFilingDate,
  onSelect,
}: ReportHistoryProps) {
  if (items.length === 0) {
    return (
      <aside className="report-history">
        <h2>History</h2>
        <p className="muted">No past reports yet.</p>
      </aside>
    )
  }

  return (
    <aside className="report-history">
      <h2>History</h2>
      <ul>
        {items.map((item) => (
          <li key={item.report_id}>
            <button
              type="button"
              className={
                item.filing_date === activeFilingDate ? 'active' : undefined
              }
              onClick={() => onSelect(item.filing_date)}
            >
              <span className="history-filing">Filed {item.filing_date}</span>
              {item.period_end && (
                <span className="history-period">Period {item.period_end}</span>
              )}
              <span className="history-created">{formatDate(item.created_at)}</span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
