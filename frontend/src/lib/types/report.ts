export interface MetricRow {
  label: string
  tag?: string | null
  current?: number | null
  prior?: number | null
  dollar_change?: number | null
  pct_change?: number | null
}

export interface YoYSection {
  period_end: string | null
  prior_period_end: string | null
  metrics: MetricRow[]
}

export interface MetricHighlight {
  metric: string
  trend: 'up' | 'down' | 'flat'
  summary: string
}

export interface EarningsDebrief {
  headline: string
  overall_assessment: 'strong' | 'mixed' | 'weak'
  revenue_analysis: MetricHighlight
  margin_analysis: string
  expense_analysis: MetricHighlight[]
  key_takeaways: string[]
  items_to_watch: string[]
}

export interface Report {
  company: string
  cik: string
  ticker: string
  quarterly: YoYSection
  annual: YoYSection
  filing_date: string
  cached: boolean
  debrief?: EarningsDebrief | null
  debrief_cached?: boolean
}
