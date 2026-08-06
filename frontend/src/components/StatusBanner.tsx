interface StatusBannerProps {
  variant: 'loading' | 'error'
  message: string
}

export default function StatusBanner({ variant, message }: StatusBannerProps) {
  const classes =
    variant === 'loading'
      ? 'border border-accent-border bg-accent-bg text-text-heading'
      : 'border border-red-200 bg-error-bg text-negative'

  return (
    <div
      className={`mb-6 rounded-lg px-4 py-3 text-center ${classes}`}
      role="status"
    >
      {message}
    </div>
  )
}
