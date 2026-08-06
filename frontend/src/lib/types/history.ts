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
