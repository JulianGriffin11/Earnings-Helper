import { Button } from '@/components/ui/button'
import type { RecentTicker } from '@/lib/recent'

interface RecentTickersProps {
  items: RecentTicker[]
  onSelect: (ticker: string) => void
  disabled?: boolean
  activeTicker?: string | null
}

export default function RecentTickers({
  items,
  onSelect,
  disabled,
  activeTicker,
}: RecentTickersProps) {
  if (items.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground">Recent</span>
      {items.map((item) => (
        <Button
          key={item.ticker}
          type="button"
          size="sm"
          variant={item.ticker === activeTicker ? 'secondary' : 'outline'}
          disabled={disabled}
          title={item.name}
          onClick={() => onSelect(item.ticker)}
        >
          {item.ticker}
        </Button>
      ))}
    </div>
  )
}
