export interface RecentTicker {
  ticker: string
  name: string
  viewedAt: string
}

const STORAGE_KEY = 'earnings-helper.recent'
const MAX_RECENT = 6

function isRecentTicker(value: unknown): value is RecentTicker {
  if (typeof value !== 'object' || value === null) return false
  const entry = value as Record<string, unknown>
  return (
    typeof entry.ticker === 'string' &&
    typeof entry.name === 'string' &&
    typeof entry.viewedAt === 'string'
  )
}

export function readRecent(): RecentTicker[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isRecentTicker).slice(0, MAX_RECENT)
  } catch {
    return []
  }
}

export function rememberRecent(ticker: string, name: string): RecentTicker[] {
  const next: RecentTicker[] = [
    { ticker, name, viewedAt: new Date().toISOString() },
    ...readRecent().filter((entry) => entry.ticker !== ticker),
  ].slice(0, MAX_RECENT)

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Ignore quota and private-mode failures; the in-memory list still updates.
  }

  return next
}
