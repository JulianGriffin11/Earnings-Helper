import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { formatPct, formatSignedMoney, formatMoney } from '@/lib/format'
import type { MetricRow, YoYSection } from '@/lib/types'

const KPI_LABELS = [
  'Revenue',
  'Gross Profit',
  'Operating Expenses',
  'Net Income',
] as const

const INVERSE_LABELS = new Set<string>(['Operating Expenses'])

const FLAT_BAND = 0.5

interface KpiGridProps {
  section: YoYSection
  exact: boolean
  onExactChange: (exact: boolean) => void
}

type Polarity = 'positive' | 'negative' | 'flat' | 'none'

const polarityStyles: Record<Polarity, string> = {
  positive: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  negative: 'border-red-200 bg-red-50 text-destructive',
  flat: 'border-border bg-muted text-muted-foreground',
  none: 'border-border bg-muted text-muted-foreground',
}

function polarityFor(label: string, pct: number | null | undefined): Polarity {
  if (pct == null) return 'none'
  if (Math.abs(pct) < FLAT_BAND) return 'flat'
  const movedUp = pct > 0
  const favorable = INVERSE_LABELS.has(label) ? !movedUp : movedUp
  return favorable ? 'positive' : 'negative'
}

function metricByLabel(section: YoYSection, label: string): MetricRow | undefined {
  return section.metrics.find((metric) => metric.label === label)
}

export default function KpiGrid({ section, exact, onExactChange }: KpiGridProps) {
  const comparison =
    section.period_end && section.prior_period_end
      ? `${section.period_end} vs ${section.prior_period_end}`
      : null

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold tracking-tight">Quarterly snapshot</h2>
          {comparison && (
            <p className="text-sm text-muted-foreground">{comparison}</p>
          )}
        </div>
        <Button
          type="button"
          variant={exact ? 'secondary' : 'outline'}
          size="sm"
          aria-pressed={exact}
          onClick={() => onExactChange(!exact)}
        >
          Exact figures
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {KPI_LABELS.map((label) => {
          const metric = metricByLabel(section, label)
          const polarity = polarityFor(label, metric?.pct_change)
          return (
            <Card key={label} size="sm">
              <CardHeader>
                <CardDescription>{label}</CardDescription>
                {comparison && (
                  <p className="text-xs text-muted-foreground">{comparison}</p>
                )}
                <CardTitle className="text-2xl font-semibold tabular-nums">
                  {formatMoney(metric?.current, exact)}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center gap-2">
                <span
                  className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold tabular-nums ${polarityStyles[polarity]}`}
                >
                  {formatPct(metric?.pct_change)}
                </span>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {formatSignedMoney(metric?.dollar_change, exact)}
                </span>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
