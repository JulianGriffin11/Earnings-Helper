import type { ReactNode } from 'react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import type { EarningsDebrief, MetricHighlight } from '@/lib/types'

interface DebriefPanelProps {
  debrief: EarningsDebrief | null | undefined
}

const assessmentLabels: Record<EarningsDebrief['overall_assessment'], string> = {
  strong: 'Strong',
  mixed: 'Mixed',
  weak: 'Weak',
}

const assessmentStyles: Record<EarningsDebrief['overall_assessment'], string> = {
  strong: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  mixed: 'border-border bg-muted text-muted-foreground',
  weak: 'border-red-200 bg-red-50 text-destructive',
}

function trendLabel(trend: MetricHighlight['trend']): string {
  if (trend === 'up') return '↑ Up'
  if (trend === 'down') return '↓ Down'
  return '→ Flat'
}

function trendColor(trend: MetricHighlight['trend']): string {
  if (trend === 'up') return 'text-emerald-600'
  if (trend === 'down') return 'text-destructive'
  return 'text-muted-foreground'
}

function AnalysisCard({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="text-xs font-semibold tracking-wide uppercase">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="m-0 list-none space-y-2 p-0">
      {items.map((item) => (
        <li key={item} className="flex gap-2.5 text-sm leading-relaxed">
          <span
            className="mt-2 size-1.5 shrink-0 rounded-full bg-primary"
            aria-hidden
          />
          <span className="text-muted-foreground">{item}</span>
        </li>
      ))}
    </ul>
  )
}

export default function DebriefPanel({ debrief }: DebriefPanelProps) {
  if (!debrief) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Earnings Debrief</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No debrief available for this report.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <CardTitle>Earnings Debrief</CardTitle>
          <span
            className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold tracking-wide ${assessmentStyles[debrief.overall_assessment]}`}
          >
            {assessmentLabels[debrief.overall_assessment]}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        <div className="grid gap-4 md:grid-cols-2">
          <AnalysisCard title="Revenue">
            <p
              className={`mb-2 text-xs font-medium ${trendColor(debrief.revenue_analysis.trend)}`}
            >
              {trendLabel(debrief.revenue_analysis.trend)}
            </p>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {debrief.revenue_analysis.summary}
            </p>
          </AnalysisCard>

          <AnalysisCard title="Margins">
            <p className="text-sm leading-relaxed text-muted-foreground">
              {debrief.margin_analysis}
            </p>
          </AnalysisCard>
        </div>

        {debrief.expense_analysis.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {debrief.expense_analysis.map((item) => (
                <Card key={item.metric} size="sm">
                  <CardContent className="pt-4">
                    <p className="mb-1 text-sm font-semibold">{item.metric}</p>
                    <p
                      className={`mb-1.5 text-xs font-medium ${trendColor(item.trend)}`}
                    >
                      {trendLabel(item.trend)}
                    </p>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {item.summary}
                    </p>
                  </CardContent>
                </Card>
              ))}
          </div>
        )}

        <Separator />

        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="mb-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Key Takeaways
            </h3>
            <BulletList items={debrief.key_takeaways} />
          </div>
          <div>
            <h3 className="mb-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Items to Watch
            </h3>
            <BulletList items={debrief.items_to_watch} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
