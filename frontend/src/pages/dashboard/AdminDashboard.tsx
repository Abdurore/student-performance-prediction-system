import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ClipboardList, GraduationCap, Users } from 'lucide-react'
import { Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getAtRisk, getInterventions, getOverview, getTrends } from '@/lib/endpoints'
import { CardSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { StatCard } from '@/components/ui/StatCard'
import { RiskBadge } from '@/components/ui/RiskBadge'
import type { RiskTier } from '@/types/prediction'

const RISK_COLORS: Record<RiskTier, string> = {
  low: '#15803D',
  moderate: '#CA8A04',
  high: '#EA580C',
  critical: '#B91C1C',
}

export function AdminDashboard() {
  const overview = useQuery({ queryKey: ['analytics', 'overview'], queryFn: getOverview })
  const trends = useQuery({ queryKey: ['analytics', 'trends'], queryFn: getTrends })
  const atRisk = useQuery({ queryKey: ['predictions', 'at-risk'], queryFn: () => getAtRisk() })
  const interventions = useQuery({ queryKey: ['interventions'], queryFn: () => getInterventions() })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">Institution overview</h1>
        <p className="text-sm text-slate-500">Live totals, risk distribution, and recent activity across all students.</p>
      </div>

      {overview.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[84px]" />
          ))}
        </div>
      )}
      {overview.isError && <ErrorState onRetry={() => overview.refetch()} message="Could not load institution totals." />}
      {overview.data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Active students" value={overview.data.active_students} icon={Users} />
          <StatCard label="Average CGPA" value={overview.data.average_cgpa.toFixed(2)} icon={GraduationCap} />
          <StatCard
            label="Critical risk"
            value={overview.data.at_risk_critical}
            icon={AlertTriangle}
            tone="critical"
          />
          <StatCard label="Open interventions" value={overview.data.total_interventions_open} icon={ClipboardList} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold text-navy-900">Risk distribution</h2>
          {overview.isLoading && <Skeleton className="h-64 w-full" />}
          {overview.isError && <ErrorState onRetry={() => overview.refetch()} />}
          {overview.data &&
            (() => {
              const pieData = [
                { tier: 'low' as const, name: 'Low', value: overview.data.at_risk_low },
                { tier: 'moderate' as const, name: 'Moderate', value: overview.data.at_risk_moderate },
                { tier: 'high' as const, name: 'High', value: overview.data.at_risk_high },
                { tier: 'critical' as const, name: 'Critical', value: overview.data.at_risk_critical },
              ]
              const total = pieData.reduce((sum, d) => sum + d.value, 0)
              if (total === 0) {
                return <EmptyState title="No risk scores yet" guidance="Risk tiers will appear here once predictions have been generated for students." />
              }
              return (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90} paddingAngle={2}>
                      {pieData.map((entry) => (
                        <Cell key={entry.tier} fill={RISK_COLORS[entry.tier]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )
            })()}
        </div>

        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold text-navy-900">GPA trend by session</h2>
          {trends.isLoading && <Skeleton className="h-64 w-full" />}
          {trends.isError && <ErrorState onRetry={() => trends.refetch()} />}
          {trends.data &&
            (trends.data.points.length === 0 ? (
              <EmptyState title="No session history yet" guidance="GPA trends appear once students have completed at least one session." />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={trends.data.points}>
                  <XAxis dataKey="session" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 5]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="average_gpa" name="Avg GPA" stroke="#0F2038" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="average_cgpa" name="Avg CGPA" stroke="#D97706" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold text-navy-900">At-risk leaderboard</h2>
          {atRisk.isLoading && <CardSkeleton rows={5} />}
          {atRisk.isError && <ErrorState onRetry={() => atRisk.refetch()} />}
          {atRisk.data &&
            (atRisk.data.items.length === 0 ? (
              <EmptyState title="No at-risk students" guidance="Students flagged as moderate risk or above will be listed here." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs uppercase tracking-wide text-slate-400">
                      <th className="pb-2">Student</th>
                      <th className="pb-2">Dept / Level</th>
                      <th className="pb-2">Risk</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {atRisk.data.items.slice(0, 8).map((item) => (
                      <tr key={item.student_id}>
                        <td className="py-2">
                          <p className="font-medium text-navy-900">{item.full_name}</p>
                          <p className="text-xs text-slate-500">{item.matric_no}</p>
                        </td>
                        <td className="py-2 text-slate-600">
                          {item.department} · L{item.level}
                        </td>
                        <td className="py-2">
                          <RiskBadge tier={item.risk_tier} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
        </div>

        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold text-navy-900">Recent interventions</h2>
          {interventions.isLoading && <CardSkeleton rows={5} />}
          {interventions.isError && <ErrorState onRetry={() => interventions.refetch()} />}
          {interventions.data &&
            (interventions.data.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="No interventions logged"
                guidance="Interventions created by advisers or admins for at-risk students will show up here."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs uppercase tracking-wide text-slate-400">
                      <th className="pb-2">Student</th>
                      <th className="pb-2">Action</th>
                      <th className="pb-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {interventions.data.slice(0, 8).map((item) => (
                      <tr key={item.id}>
                        <td className="py-2 text-slate-600">#{item.student_id}</td>
                        <td className="py-2 text-slate-600">{item.action_type}</td>
                        <td className="py-2 capitalize text-slate-600">{item.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
