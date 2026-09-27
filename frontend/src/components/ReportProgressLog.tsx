import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import type { ProgressStep } from '@/lib/types'

interface ReportProgressLogProps {
  steps: ProgressStep[]
  mode: 'loading' | 'success' | 'error'
}

function StepList({ steps }: { steps: ProgressStep[] }) {
  return (
    <ol className="flex flex-col gap-1.5 font-mono text-sm">
      {steps.map((step) => (
        <li
          key={step.id}
          className={
            step.status === 'active'
              ? 'text-muted-foreground'
              : 'text-muted-foreground/60'
          }
        >
          <span className={step.status === 'active' ? 'animate-pulse' : undefined}>
            {step.message}
          </span>
        </li>
      ))}
    </ol>
  )
}

export default function ReportProgressLog({ steps, mode }: ReportProgressLogProps) {
  if (steps.length === 0) return null

  if (mode === 'success') {
    return (
      <Accordion defaultValue={[]}>
        <AccordionItem value="sec-retrieval">
          <AccordionTrigger>SEC retrieval</AccordionTrigger>
          <AccordionContent>
            <StepList steps={steps} />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    )
  }

  const latest = steps[steps.length - 1]
  const earlier = steps.slice(0, -1)

  return (
    <div
      className="rounded-lg border border-border/60 bg-muted/20 px-4 py-3"
      aria-live="polite"
      aria-label="Report generation progress"
    >
      {mode === 'loading' && latest && (
        <p className="animate-pulse font-mono text-sm text-muted-foreground">
          {latest.message}
        </p>
      )}
      {earlier.length > 0 && (
        <div className={mode === 'loading' ? 'mt-2' : undefined}>
          <StepList steps={mode === 'loading' ? earlier : steps} />
        </div>
      )}
      {mode === 'error' && earlier.length === 0 && (
        <StepList steps={steps} />
      )}
    </div>
  )
}
