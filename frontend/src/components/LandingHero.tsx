import { AlertCircleIcon } from 'lucide-react'

import CompanySearch from './CompanySearch'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface LandingHeroProps {
  onSelect: (ticker: string) => void
  disabled?: boolean
  error?: string | null
}

export default function LandingHero({
  onSelect,
  disabled,
  error,
}: LandingHeroProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 pb-24 pt-16">
      <div className="mb-10 w-full max-w-2xl text-center">
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          Earnings Helper
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg">
          Year-over-year earnings from SEC filings, with a short debrief of what changed.
        </p>
      </div>

      <CompanySearch
        variant="hero"
        onSelect={onSelect}
        disabled={disabled}
        className="w-full"
      />

      {error && (
        <Alert variant="destructive" className="mt-6 w-full max-w-2xl">
          <AlertCircleIcon />
          <AlertTitle>Failed to load report</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!error && (
        <p className="mt-6 text-sm text-muted-foreground">
          Try AMZN, META, or AAPL
        </p>
      )}
    </div>
  )
}
