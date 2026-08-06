import type { EarningsDebrief } from '../api/client'

interface DebriefPanelProps {
  debrief: EarningsDebrief | null | undefined
}

const assessmentLabels: Record<EarningsDebrief['overall_assessment'], string> = {
  strong: 'Strong',
  mixed: 'Mixed',
  weak: 'Weak',
}

export default function DebriefPanel({ debrief }: DebriefPanelProps) {
  if (!debrief) {
    return (
      <section className="debrief-panel">
        <h2>Earnings Debrief</h2>
        <p className="muted">No debrief available for this report.</p>
      </section>
    )
  }

  return (
    <section className="debrief-panel">
      <div className="debrief-header">
        <h2>Earnings Debrief</h2>
        <span className={`badge badge-${debrief.overall_assessment}`}>
          {assessmentLabels[debrief.overall_assessment]}
        </span>
      </div>
      <p className="headline">{debrief.headline}</p>

      <div className="debrief-block">
        <h3>Revenue</h3>
        <p>
          <strong>{debrief.revenue_analysis.metric}</strong> ({debrief.revenue_analysis.trend}):{' '}
          {debrief.revenue_analysis.summary}
        </p>
      </div>

      <div className="debrief-block">
        <h3>Margins</h3>
        <p>{debrief.margin_analysis}</p>
      </div>

      {debrief.expense_analysis.length > 0 && (
        <div className="debrief-block">
          <h3>Expenses</h3>
          <ul>
            {debrief.expense_analysis.map((item) => (
              <li key={item.metric}>
                <strong>{item.metric}</strong> ({item.trend}): {item.summary}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="debrief-block">
        <h3>Key Takeaways</h3>
        <ul>
          {debrief.key_takeaways.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="debrief-block">
        <h3>Items to Watch</h3>
        <ul>
          {debrief.items_to_watch.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  )
}
