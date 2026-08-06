import { env } from './env'
import type { HistoryResponse } from './types/history'
import type { Report } from './types/report'
import type { SearchResponse } from './types/search'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function readErrorDetail(body: unknown): string | undefined {
  if (!isRecord(body)) return undefined
  const detail = body.detail
  return typeof detail === 'string' ? detail : undefined
}

function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (!env.apiBaseUrl) {
    return normalizedPath
  }
  return `${env.apiBaseUrl}${normalizedPath}`
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(buildApiUrl(path))
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body: unknown = await response.json()
      const parsedDetail = readErrorDetail(body)
      if (parsedDetail) detail = parsedDetail
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
): Promise<Report> {
  const params = new URLSearchParams({ ticker })
  if (options?.refresh) params.set('refresh', 'true')
  if (options?.filingDate) params.set('filing_date', options.filingDate)
  return apiFetch<Report>(`/api/report?${params}`)
}

export function fetchHistory(ticker: string): Promise<HistoryResponse> {
  const params = new URLSearchParams({ ticker })
  return apiFetch<HistoryResponse>(`/api/history?${params}`)
}
