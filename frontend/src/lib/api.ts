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

function parseSseChunk(chunk: string): { event: string; data: string } | null {
  let event = 'message'
  let data = ''
  for (const line of chunk.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7)
    if (line.startsWith('data: ')) data += line.slice(6)
  }
  if (!data) return null
  return { event, data }
}

export function fetchReportStream(
  ticker: string,
  options: { refresh?: boolean; filingDate?: string } | undefined,
  onProgress: (message: string) => void,
): Promise<Report> {
  const params = new URLSearchParams({ ticker })
  if (options?.refresh) params.set('refresh', 'true')
  if (options?.filingDate) params.set('filing_date', options.filingDate)

  const url = buildApiUrl(`/api/report/stream?${params}`)

  return fetch(url).then(async (response) => {
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

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('Streaming is not supported in this browser')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() ?? ''

      for (const chunk of chunks) {
        const parsed = parseSseChunk(chunk.trim())
        if (!parsed) continue

        if (parsed.event === 'progress') {
          const data = JSON.parse(parsed.data) as { message: string }
          onProgress(data.message)
          continue
        }

        if (parsed.event === 'complete') {
          const data = JSON.parse(parsed.data) as { report: Report }
          return data.report
        }

        if (parsed.event === 'failure') {
          const data = JSON.parse(parsed.data) as { detail: string }
          throw new Error(data.detail)
        }
      }
    }

    throw new Error('Report stream ended before completion')
  })
}

export function fetchHistory(ticker: string): Promise<HistoryResponse> {
  const params = new URLSearchParams({ ticker })
  return apiFetch<HistoryResponse>(`/api/history?${params}`)
}
