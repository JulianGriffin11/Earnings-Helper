import { useEffect, useRef } from 'react'

import type { ProgressStep } from '@/lib/types'

interface ReportProgressLogProps {
  steps: ProgressStep[]
}

export default function ReportProgressLog({ steps }: ReportProgressLogProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    container.scrollTop = container.scrollHeight
  }, [steps])

  if (steps.length === 0) return null

  return (
    <div
      ref={containerRef}
      className="max-h-48 overflow-y-auto rounded-lg border border-border/60 bg-muted/20 px-4 py-3"
      aria-live="polite"
      aria-label="Report generation progress"
    >
      <ol className="flex flex-col gap-1.5 font-mono text-sm">
        {steps.map((step) => (
          <li
            key={step.id}
            className={
              step.status === 'active'
                ? 'animate-in fade-in slide-in-from-bottom-2 text-muted-foreground duration-300'
                : 'text-muted-foreground/60 duration-300'
            }
          >
            <span className={step.status === 'active' ? 'animate-pulse' : undefined}>
              {step.message}
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}
