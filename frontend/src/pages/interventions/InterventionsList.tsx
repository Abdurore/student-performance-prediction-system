import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardList } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getInterventions, updateIntervention } from '@/lib/endpoints'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { useAuth } from '@/hooks/useAuth'
import type { InterventionRead } from '@/types/intervention'

const STATUSES = ['planned', 'in_progress', 'completed', 'cancelled']

const STATUS_TONES: Record<string, string> = {
  planned: 'bg-slate-100 text-slate-600',
  in_progress: 'bg-yellow-50 text-[#CA8A04]',
  completed: 'bg-green-50 text-[#15803D]',
  cancelled: 'bg-red-50 text-[#B91C1C]',
}

function StatusUpdateSelect({ intervention }: { intervention: InterventionRead }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (status: string) => updateIntervention(intervention.id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['interventions'] }),
  })

  return (
    <select
      value={intervention.status}
      disabled={mutation.isPending}
      onChange={(e) => mutation.mutate(e.target.value)}
      className="rounded-md border border-slate-300 px-2 py-1 text-xs capitalize focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
    >
      {STATUSES.map((s) => (
        <option key={s} value={s}>
          {s.replace(/_/g, ' ')}
        </option>
      ))}
    </select>
  )
}

export function InterventionsList() {
  const { user } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'adviser'
  const [statusFilter, setStatusFilter] = useState('')

  const interventions = useQuery({ queryKey: ['interventions'], queryFn: () => getInterventions() })

  const filtered = (interventions.data ?? []).filter((i) => !statusFilter || i.status === statusFilter)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">Interventions</h1>
        <p className="text-sm text-slate-500">Support actions logged for students within your scope.</p>
      </div>

      <div className="card flex items-end gap-3 p-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm capitalize focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card p-5">
        {interventions.isLoading && <CardSkeleton rows={6} />}
        {interventions.isError && <ErrorState onRetry={() => interventions.refetch()} message="Could not load interventions." />}
        {interventions.data &&
          (filtered.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title="No interventions found"
              guidance="Interventions logged from a student's profile page will appear here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-slate-400">
                    <th className="pb-2">Student</th>
                    <th className="pb-2">Action</th>
                    <th className="pb-2">Notes</th>
                    <th className="pb-2">Created</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((item) => (
                    <tr key={item.id}>
                      <td className="py-2">
                        <Link to={`/students/${item.student_id}`} className="font-medium text-navy-900 hover:text-amber-600">
                          Student #{item.student_id}
                        </Link>
                      </td>
                      <td className="py-2 capitalize text-slate-600">{item.action_type.replace(/_/g, ' ')}</td>
                      <td className="max-w-xs truncate py-2 text-slate-600">{item.notes || '—'}</td>
                      <td className="py-2 text-slate-600">{new Date(item.created_at).toLocaleDateString()}</td>
                      <td className="py-2">
                        {canManage ? (
                          <StatusUpdateSelect intervention={item} />
                        ) : (
                          <span className={`rounded-full px-2 py-1 text-xs font-medium capitalize ${STATUS_TONES[item.status]}`}>
                            {item.status.replace(/_/g, ' ')}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </div>
    </div>
  )
}
