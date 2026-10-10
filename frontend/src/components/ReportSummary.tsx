import { DownloadIcon, RefreshCwIcon } from 'lucide-react'

import { Button, buttonVariants } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { exportWorkbookUrl } from '@/lib/api'
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
        <CardAction className="flex flex-wrap justify-end gap-2">
          <a
            className={buttonVariants({ variant: 'outline', size: 'sm' })}
            href={exportWorkbookUrl(report.ticker)}
            download
          >
            <DownloadIcon />
            Download Excel
          </a>
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
        <div className="col-span-2 flex flex-wrap items-center gap-x-3 gap-y-1 pt-1">
          <span className="text-sm text-muted-foreground">
            Filing date: {report.filing_date}
          </span>
          {report.cached && (
            <span className="text-sm text-muted-foreground">Cached result</span>
          )}
        </div>
      </CardHeader>
    </Card>
  )
}
