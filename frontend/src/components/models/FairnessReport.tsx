interface GroupFairness {
  demographic_parity_difference: number
  equal_opportunity_difference: number
  predictive_parity_difference: number
  flagged: boolean
}

interface FairnessReportShape {
  task: string
  algorithm: string
  n_test_rows: number
  groups: Record<string, GroupFairness>
}

function isFairnessReportShape(value: unknown): value is FairnessReportShape {
  return typeof value === 'object' && value !== null && 'groups' in value
}

export function FairnessReport({ report }: { report: Record<string, unknown> }) {
  if (!isFairnessReportShape(report)) {
    return <p className="text-sm text-slate-500">Unrecognised fairness report format.</p>
  }

  const groupEntries = Object.entries(report.groups)

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">Evaluated on {report.n_test_rows} temporal holdout rows.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wide text-slate-400">
              <th className="pb-2">Attribute</th>
              <th className="pb-2">Demographic parity Δ</th>
              <th className="pb-2">Equal opportunity Δ</th>
              <th className="pb-2">Predictive parity Δ</th>
              <th className="pb-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {groupEntries.map(([attribute, g]) => (
              <tr key={attribute}>
                <td className="py-2 font-medium capitalize text-navy-900">{attribute.replace(/_/g, ' ')}</td>
                <td className="py-2 text-slate-600">{(g.demographic_parity_difference * 100).toFixed(1)} pp</td>
                <td className="py-2 text-slate-600">{(g.equal_opportunity_difference * 100).toFixed(1)} pp</td>
                <td className="py-2 text-slate-600">{(g.predictive_parity_difference * 100).toFixed(1)} pp</td>
                <td className="py-2">
                  {g.flagged ? (
                    <span className="risk-badge-high">Flagged</span>
                  ) : (
                    <span className="risk-badge-low">Within threshold</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
