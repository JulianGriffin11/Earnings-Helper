import { formatCurrency, formatPct } from '../lib/format'
import type { YoYSection } from '../lib/types'

interface YoYTableProps {
  title: string
  section: YoYSection
}

export default function YoYTable({ title, section }: YoYTableProps) {
  if (!section.period_end) {
    return (
      <section className="rounded-xl border border-border bg-bg p-5 shadow-[var(--shadow-card)]">
        <h2 className="text-lg text-text-heading">{title}</h2>
        <p className="text-sm text-text">No data available</p>
      </section>
    )
  }

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-bg shadow-[var(--shadow-card)]">
      <div className="border-b border-border bg-surface px-5 py-3">
        <h2 className="m-0 text-lg text-text-heading">{title}</h2>
        <p className="mt-1 text-sm text-text">
          {section.period_end} vs {section.prior_period_end}
        </p>
      </div>
      <div className="overflow-x-auto p-1">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-surface">
              <th className="px-4 py-2.5 text-left font-medium text-accent">
                Metric
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-accent">
                Current
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-accent">
                Prior
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-accent">
                $ Change
              </th>
              <th className="px-4 py-2.5 text-right font-medium text-accent">
                % Change
              </th>
            </tr>
          </thead>
          <tbody>
            {section.metrics.map((metric, index) => (
              <tr
                key={metric.label}
                className={index % 2 === 0 ? 'bg-bg' : 'bg-surface/50'}
              >
                <td className="border-t border-border px-4 py-2.5 text-left font-medium text-text-heading">
                  {metric.label}
                </td>
                <td className="border-t border-border px-4 py-2.5 text-right">
                  {formatCurrency(metric.current)}
                </td>
                <td className="border-t border-border px-4 py-2.5 text-right">
                  {formatCurrency(metric.prior)}
                </td>
                <td className="border-t border-border px-4 py-2.5 text-right">
                  {formatCurrency(metric.dollar_change)}
                </td>
                <td
                  className={`border-t border-border px-4 py-2.5 text-right font-medium ${
                    metric.pct_change == null
                      ? ''
                      : metric.pct_change >= 0
                        ? 'text-positive'
                        : 'text-negative'
                  }`}
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
