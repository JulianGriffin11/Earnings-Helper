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

export interface ReportResponse {
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

export interface SearchResult {
  ticker: string
  name: string
  cik: string
}

export interface SearchResponse {
  results: SearchResult[]
}

export interface HistoryItem {
  filing_date: string
  period_end: string | null
  created_at: string
  report_id: number
}

export interface HistoryResponse {
  ticker: string
  items: HistoryItem[]
}

async function apiFetch<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // ignore json parse errors
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export function searchCompanies(query: string): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query })
  return apiFetch<SearchResponse>(`/api/search?${params}`)
}

export function fetchReport(
  ticker: string,
  options?: { refresh?: boolean; filingDate?: string },
): Promise<ReportResponse> {
  const params = new URLSearchParams({ ticker })
  if (options?.refresh) params.set('refresh', 'true')
  if (options?.filingDate) params.set('filing_date', options.filingDate)
  return apiFetch<ReportResponse>(`/api/report?${params}`)
}

export function fetchHistory(ticker: string): Promise<HistoryResponse> {
  const params = new URLSearchParams({ ticker })
  return apiFetch<HistoryResponse>(`/api/history?${params}`)
}

export function secEdgarUrl(cik: string): string {
  return `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cik}`
}
