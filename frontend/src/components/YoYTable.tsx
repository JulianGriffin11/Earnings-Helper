import type { YoYSection } from '../api/client'

interface YoYTableProps {
  title: string
  section: YoYSection
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPct(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export default function YoYTable({ title, section }: YoYTableProps) {
  if (!section.period_end) {
    return (
      <section className="yoy-table">
        <h2>{title}</h2>
        <p className="muted">No data available</p>
      </section>
    )
  }

  return (
    <section className="yoy-table">
      <h2>{title}</h2>
      <p className="period-label">
        {section.period_end} vs {section.prior_period_end}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>Current</th>
              <th>Prior</th>
              <th>$ Change</th>
              <th>% Change</th>
            </tr>
          </thead>
          <tbody>
            {section.metrics.map((metric) => (
              <tr key={metric.label}>
                <td>{metric.label}</td>
                <td>{formatCurrency(metric.current)}</td>
                <td>{formatCurrency(metric.prior)}</td>
                <td>{formatCurrency(metric.dollar_change)}</td>
                <td
                  className={
                    metric.pct_change == null
                      ? ''
                      : metric.pct_change >= 0
                        ? 'positive'
                        : 'negative'
                  }
                >
                  {formatPct(metric.pct_change)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
