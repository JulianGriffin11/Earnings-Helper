function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '')
  if (!trimmed) return ''

  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    throw new Error(
      `Invalid VITE_API_BASE_URL "${raw}". Expected an absolute URL such as https://api.example.com`,
    )
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(
      `Invalid VITE_API_BASE_URL "${raw}". Only http and https URLs are supported.`,
    )
  }

  return `${parsed.origin}${parsed.pathname}`.replace(/\/+$/, '')
}

function readApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL

  if (raw === undefined || raw === '') {
    if (import.meta.env.PROD) {
      throw new Error(
        'VITE_API_BASE_URL is required in production. Set it to your deployed FastAPI origin (e.g. https://api.example.com).',
      )
    }
    return ''
  }

  if (!isNonEmptyString(raw)) {
    throw new Error('VITE_API_BASE_URL must be a string when set.')
  }

  return normalizeBaseUrl(raw)
}

export const env = {
  apiBaseUrl: readApiBaseUrl(),
} as const
