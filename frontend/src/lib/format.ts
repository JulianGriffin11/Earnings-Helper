export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatCompactCurrency(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatMoney(
  value: number | null | undefined,
  exact: boolean,
): string {
  return exact ? formatCurrency(value) : formatCompactCurrency(value)
}

export function formatSignedMoney(
  value: number | null | undefined,
  exact: boolean,
): string {
  if (value == null) return 'n/a'
  const formatted = formatMoney(value, exact)
  return value > 0 ? `+${formatted}` : formatted
}

export function formatPct(value: number | null | undefined): string {
  if (value == null) return 'n/a'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
