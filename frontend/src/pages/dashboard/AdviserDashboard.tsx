import { useQuery } from '@tanstack/react-query'
import { Users } from 'lucide-react'
import { getAtRisk } from '@/lib/endpoints'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { StatCard } from '@/components/ui/StatCard'
import type { AtRiskItem, RiskTier } from '@/types/prediction'

const TIER_ORDER: RiskTier[] = ['critical', 'high', 'moderate', 'low']
const TIER_LABELS: Record<RiskTier, string> = {
  critical: 'Critical — act now',
  high: 'High — schedule this week',
  moderate: 'Moderate — monitor',
  low: 'Low — stable',
}

export function AdviserDashboard() {
  const atRisk = useQuery({ queryKey: ['predictions', 'at-risk'], queryFn: () => getAtRisk() })

  const groups: Record<RiskTier, AtRiskItem[]> = { low: [], moderate: [], high: [], critical: [] }
  for (const item of atRisk.data?.items ?? []) {
    groups[item.risk_tier].push(item)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">My caseload</h1>
        <p className="text-sm text-slate-500">Your advisees, grouped by urgency so the most pressing cases surface first.</p>
      </div>

      <StatCard label="Total advisees flagged" value={atRisk.data?.total ?? 0} icon={Users} tone="high" />

      {atRisk.isLoading && <CardSkeleton rows={6} />}
      {atRisk.isError && <ErrorState onRetry={() => atRisk.refetch()} message="Could not load your caseload." />}
      {atRisk.data &&
        (atRisk.data.items.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No advisees flagged"
            guidance="Once your assigned students receive a risk prediction, they will be grouped here by urgency."
          />
        ) : (
          <div className="space-y-4">
            {TIER_ORDER.filter((tier) => groups[tier].length > 0).map((tier) => (
              <div key={tier} className="card p-5">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-navy-900">{TIER_LABELS[tier]}</h2>
                  <RiskBadge tier={tier} />
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-xs uppercase tracking-wide text-slate-400">
                        <th className="pb-2">Student</th>
                        <th className="pb-2">Dept / Level</th>
                        <th className="pb-2">Probability</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {groups[tier].map((item) => (
                        <tr key={item.student_id}>
                          <td className="py-2">
                            <p className="font-medium text-navy-900">{item.full_name}</p>
                            <p className="text-xs text-slate-500">{item.matric_no}</p>
                          </td>
                          <td className="py-2 text-slate-600">
                            {item.department} · L{item.level}
                          </td>
                          <td className="py-2 text-slate-600">{Math.round(item.probability * 100)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        ))}
    </div>
  )
}
