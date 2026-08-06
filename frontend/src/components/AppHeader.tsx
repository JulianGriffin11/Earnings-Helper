import { Separator } from '@/components/ui/separator'

import CompanySearch from './CompanySearch'

interface AppHeaderProps {
  onSelect: (ticker: string) => void
  disabled?: boolean
  activeTicker?: string | null
}

export default function AppHeader({
  onSelect,
  disabled,
  activeTicker,
}: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 lg:px-6">
        <div className="flex shrink-0 items-center gap-2">
          <h1 className="text-base font-semibold tracking-tight">
            Earnings Helper
          </h1>
          {activeTicker && (
            <>
              <Separator orientation="vertical" className="hidden h-4 sm:block" />
              <span className="hidden text-sm text-muted-foreground sm:inline">
                {activeTicker}
              </span>
            </>
          )}
        </div>

        <div className="ml-auto flex-1 sm:max-w-md">
          <CompanySearch onSelect={onSelect} disabled={disabled} />
        </div>
      </div>
    </header>
  )
}
