import { formatCurrency, formatPct } from '@/lib/format'
import type { YoYSection } from '@/lib/types'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface YoYTableProps {
  title: string
  section: YoYSection
}

export default function YoYTable({ title, section }: YoYTableProps) {
  if (!section.period_end) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          {section.period_end} vs {section.prior_period_end}
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Metric</TableHead>
              <TableHead className="text-right">Current</TableHead>
              <TableHead className="text-right">Prior</TableHead>
              <TableHead className="text-right">$ Change</TableHead>
              <TableHead className="text-right">% Change</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {section.metrics.map((metric) => (
              <TableRow key={metric.label}>
                <TableCell className="font-medium">{metric.label}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(metric.current)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(metric.prior)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatCurrency(metric.dollar_change)}
                </TableCell>
                <TableCell
                  className={`text-right font-medium tabular-nums ${
                    metric.pct_change == null
                      ? ''
                      : metric.pct_change >= 0
                        ? 'text-emerald-600'
                        : 'text-destructive'
                  }`}
                >
                  {formatPct(metric.pct_change)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
