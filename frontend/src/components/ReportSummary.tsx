import { RefreshCwIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import type { Report } from '@/lib/types'

interface ReportSummaryProps {
  report: Report
  onRefresh: () => void
  refreshDisabled: boolean
}

export default function ReportSummary({
  report,
  onRefresh,
  refreshDisabled,
}: ReportSummaryProps) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>Earnings Report</CardDescription>
        <CardTitle className="text-xl font-semibold">
          {report.ticker} — {report.company}
        </CardTitle>
        <CardAction>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={refreshDisabled}
          >
            <RefreshCwIcon />
            Refresh
          </Button>
        </CardAction>
        <div className="col-span-2 pt-1">
          <span className="text-sm text-muted-foreground">
            Filing date: {report.filing_date}
          </span>
        </div>
      </CardHeader>
    </Card>
  )
}
