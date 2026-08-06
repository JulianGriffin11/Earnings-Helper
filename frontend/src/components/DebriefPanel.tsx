import type { ReactNode } from 'react'

import type { EarningsDebrief, MetricHighlight } from '../lib/types'

interface DebriefPanelProps {
  debrief: EarningsDebrief | null | undefined
}

const assessmentLabels: Record<EarningsDebrief['overall_assessment'], string> = {
  strong: 'Strong',
  mixed: 'Mixed',
  weak: 'Weak',
}

const headerBadgeClasses: Record<EarningsDebrief['overall_assessment'], string> = {
  strong: 'bg-white/20 text-white',
  mixed: 'bg-white/20 text-white',
  weak: 'bg-white/20 text-white',
}

function trendLabel(trend: MetricHighlight['trend']): string {
  if (trend === 'up') return '↑ Up'
  if (trend === 'down') return '↓ Down'
  return '→ Flat'
}

function trendColor(trend: MetricHighlight['trend']): string {
  if (trend === 'up') return 'text-positive'
  if (trend === 'down') return 'text-negative'
  return 'text-text'
}

function AnalysisCard({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <h3 className="mb-2 text-xs font-semibold tracking-wide text-accent uppercase">
        {title}
      </h3>
      {children}
    </div>
  )
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="m-0 list-none space-y-2 p-0">
      {items.map((item) => (
        <li key={item} className="flex gap-2.5 text-sm leading-relaxed text-text">
          <span
            className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent"
            aria-hidden
          />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export default function DebriefPanel({ debrief }: DebriefPanelProps) {
  if (!debrief) {
    return (
      <section className="overflow-hidden rounded-xl border border-border bg-bg shadow-[var(--shadow-card)]">
        <div className="bg-accent px-5 py-3">
          <h2 className="m-0 text-lg text-white">Earnings Debrief</h2>
        </div>
        <p className="p-5 text-sm text-text">No debrief available for this report.</p>
      </section>
    )
  }

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-bg shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-center justify-between gap-3 bg-accent px-5 py-4">
        <h2 className="m-0 text-lg text-white">Earnings Debrief</h2>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold tracking-wide uppercase ${headerBadgeClasses[debrief.overall_assessment]}`}
        >
          {assessmentLabels[debrief.overall_assessment]}
        </span>
      </div>

      <p className="border-b border-border bg-accent-bg px-5 py-4 text-base leading-snug font-medium text-text-heading">
        {debrief.headline}
      </p>

      <div className="space-y-4 p-5">
        <div className="grid gap-4 md:grid-cols-2">
          <AnalysisCard title="Revenue">
            <p className="mb-1 text-sm font-semibold text-text-heading">
              {debrief.revenue_analysis.metric}
            </p>
            <p className={`mb-2 text-xs font-medium ${trendColor(debrief.revenue_analysis.trend)}`}>
              {trendLabel(debrief.revenue_analysis.trend)}
            </p>
            <p className="text-sm leading-relaxed text-text">
              {debrief.revenue_analysis.summary}
            </p>
          </AnalysisCard>

          <AnalysisCard title="Margins">
            <p className="text-sm leading-relaxed text-text">
              {debrief.margin_analysis}
            </p>
          </AnalysisCard>
        </div>

        {debrief.expense_analysis.length > 0 && (
          <div>
            <h3 className="mb-3 text-xs font-semibold tracking-wide text-accent uppercase">
              Expenses
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {debrief.expense_analysis.map((item) => (
                <div
                  key={item.metric}
                  className="rounded-lg border border-border bg-surface px-4 py-3"
                >
                  <p className="mb-1 text-sm font-semibold text-text-heading">
                    {item.metric}
                  </p>
                  <p className={`mb-1.5 text-xs font-medium ${trendColor(item.trend)}`}>
                    {trendLabel(item.trend)}
                  </p>
                  <p className="text-sm leading-relaxed text-text">{item.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid gap-6 border-t border-border pt-5 md:grid-cols-2">
          <div>
            <h3 className="mb-3 text-xs font-semibold tracking-wide text-accent uppercase">
              Key Takeaways
            </h3>
            <BulletList items={debrief.key_takeaways} />
          </div>
          <div>
            <h3 className="mb-3 text-xs font-semibold tracking-wide text-accent uppercase">
              Items to Watch
            </h3>
            <BulletList items={debrief.items_to_watch} />
          </div>
        </div>
      </div>
    </section>
  )
}
