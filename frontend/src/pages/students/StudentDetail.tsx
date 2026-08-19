import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ClipboardList, Download, Lightbulb, Loader2, RefreshCw, Target, TrendingUp } from 'lucide-react'
import {
  createIntervention,
  downloadStudentReport,
  getInterventions,
  getStudent,
  predictStudent,
} from '@/lib/endpoints'
import { triggerBlobDownload } from '@/lib/download'
import { ApiError } from '@/lib/api'
import { CardSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { StatCard } from '@/components/ui/StatCard'
import { useAuth } from '@/hooks/useAuth'

const ACTION_TYPES = [
  { value: 'counselling', label: 'Counselling' },
  { value: 'tutorial', label: 'Tutorial' },
  { value: 'guardian_contact', label: 'Guardian contact' },
  { value: 'workload_review', label: 'Workload review' },
  { value: 'referral', label: 'Referral' },
  { value: 'other', label: 'Other' },
]

export function StudentDetail() {
  const { id } = useParams<{ id: string }>()
  const studentId = Number(id)
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const canManageIntervention = user?.role === 'admin' || user?.role === 'adviser'

  const profile = useQuery({ queryKey: ['student', studentId], queryFn: () => getStudent(studentId) })
  const interventions = useQuery({
    queryKey: ['interventions', studentId],
    queryFn: () => getInterventions(studentId),
  })

  const prediction = useMutation({ mutationFn: () => predictStudent(studentId) })
  const [reportError, setReportError] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  const [actionType, setActionType] = useState(ACTION_TYPES[0].value)
  const [notes, setNotes] = useState('')
  const createMutation = useMutation({
    mutationFn: () => createIntervention({ student_id: studentId, action_type: actionType, notes: notes || null }),
    onSuccess: () => {
      setNotes('')
      queryClient.invalidateQueries({ queryKey: ['interventions', studentId] })
    },
  })

  async function handleDownloadReport() {
    setReportError(null)
    setIsDownloading(true)
    try {
      const blob = await downloadStudentReport(studentId)
      triggerBlobDownload(blob, `student_${studentId}_report.pdf`)
    } catch (err) {
      setReportError(err instanceof ApiError ? err.message : 'Could not generate the report.')
    } finally {
      setIsDownloading(false)
    }
  }

  if (profile.isError) {
    const forbidden = profile.error instanceof ApiError && profile.error.status === 403
    return (
      <EmptyState
        title={forbidden ? 'Not authorized' : 'Could not load student'}
        guidance={forbidden ? 'You do not have access to this student record.' : 'Something went wrong loading this profile.'}
      />
    )
  }

  return (
    <div className="space-y-6">
      <Link to="/students" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-navy-900">
        <ArrowLeft size={15} />
        Back to students
      </Link>

      {profile.isLoading && <CardSkeleton rows={4} />}
      {profile.data && (
        <div className="card flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <h1 className="text-xl font-semibold text-navy-900">
              {profile.data.first_name} {profile.data.last_name}
            </h1>
            <p className="text-sm text-slate-500">
              {profile.data.matric_no} · {profile.data.department} · Level {profile.data.level} · {profile.data.programme}
            </p>
          </div>
          <button
            type="button"
            onClick={handleDownloadReport}
            disabled={isDownloading}
            className="flex items-center gap-2 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-navy-900 hover:bg-slate-100 disabled:opacity-60"
          >
            {isDownloading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
            Download report
          </button>
        </div>
      )}
      {reportError && <p className="text-sm text-[#B91C1C]">{reportError}</p>}

      <div className="card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-navy-900">Prediction</h2>
          <button
            type="button"
            onClick={() => prediction.mutate()}
            disabled={prediction.isPending}
            className="flex items-center gap-2 rounded-md bg-navy-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-navy-700 disabled:opacity-60"
          >
            {prediction.isPending ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            {prediction.data ? 'Refresh prediction' : 'Run prediction'}
          </button>
        </div>

        {prediction.isError && (
          <ErrorState
            onRetry={() => prediction.mutate()}
            message={
              prediction.error instanceof ApiError && prediction.error.status === 404
                ? 'This student has no ongoing enrolment to predict for.'
                : 'Could not generate a prediction.'
            }
          />
        )}
        {!prediction.data && !prediction.isError && !prediction.isPending && (
          <EmptyState title="No prediction yet" guidance="Click 'Run prediction' to generate a live risk, GPA, and course-score forecast from the active models." />
        )}
        {prediction.data && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {prediction.data.risk && (
                <div className="card flex items-center justify-between p-4">
                  <div>
                    <p className="text-sm text-slate-500">Risk tier</p>
                    <div className="mt-1">
                      <RiskBadge tier={prediction.data.risk.risk_tier} />
                    </div>
                  </div>
                  <p className="text-lg font-semibold text-navy-900">{Math.round(prediction.data.risk.probability * 100)}%</p>
                </div>
              )}
              {prediction.data.gpa && (
                <>
                  <StatCard label="Predicted GPA" value={prediction.data.gpa.predicted_gpa.toFixed(2)} icon={TrendingUp} />
                  <StatCard label="Predicted CGPA" value={prediction.data.gpa.predicted_cgpa.toFixed(2)} icon={Target} />
                </>
              )}
            </div>

            <div>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-navy-900">
                <Lightbulb size={15} className="text-amber-600" />
                Contributing factors
              </h3>
              <ul className="space-y-1.5">
                {Array.from(
                  new Set(
                    [...(prediction.data.risk?.top_factors ?? []), ...(prediction.data.gpa?.top_factors ?? [])].map(
                      (f) => f.sentence,
                    ),
                  ),
                ).map((sentence) => (
                  <li key={sentence} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600" />
                    {sentence}
                  </li>
                ))}
              </ul>
            </div>

            {prediction.data.course_scores.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-navy-900">Course score forecasts</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-xs uppercase tracking-wide text-slate-400">
                        <th className="pb-2">Course</th>
                        <th className="pb-2">Predicted score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {prediction.data.course_scores.map((cs) => (
                        <tr key={cs.course_id}>
                          <td className="py-2 text-slate-600">{cs.course_code}</td>
                          <td className="py-2 font-medium text-navy-900">{cs.predicted_score.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">Academic history</h2>
        {profile.isLoading && <Skeleton className="h-32 w-full" />}
        {profile.data &&
          (profile.data.academic_history.length === 0 ? (
            <EmptyState title="No academic history yet" guidance="Session-by-session GPA/CGPA will appear here once a semester has been completed." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-slate-400">
                    <th className="pb-2">Session</th>
                    <th className="pb-2">Semester</th>
                    <th className="pb-2">GPA</th>
                    <th className="pb-2">CGPA</th>
                    <th className="pb-2">Standing</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {profile.data.academic_history.map((item, i) => (
                    <tr key={`${item.session}-${item.semester}-${i}`}>
                      <td className="py-2 text-slate-600">{item.session}</td>
                      <td className="py-2 text-slate-600">{item.semester}</td>
                      <td className="py-2 text-slate-600">{item.gpa.toFixed(2)}</td>
                      <td className="py-2 text-slate-600">{item.cgpa.toFixed(2)}</td>
                      <td className="py-2 capitalize text-slate-600">{item.standing.replace(/_/g, ' ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">Enrolments</h2>
        {profile.isLoading && <Skeleton className="h-32 w-full" />}
        {profile.data &&
          (profile.data.enrolments.length === 0 ? (
            <EmptyState title="No enrolments yet" guidance="Course enrolments will appear here once registered." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-slate-400">
                    <th className="pb-2">Course</th>
                    <th className="pb-2">Session</th>
                    <th className="pb-2">Score</th>
                    <th className="pb-2">Grade</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {profile.data.enrolments.slice(0, 20).map((e, i) => (
                    <tr key={`${e.course_code}-${e.session}-${i}`}>
                      <td className="py-2">
                        <p className="font-medium text-navy-900">{e.course_code}</p>
                        <p className="text-xs text-slate-500">{e.course_title}</p>
                      </td>
                      <td className="py-2 text-slate-600">
                        {e.session} S{e.semester}
                      </td>
                      <td className="py-2 text-slate-600">{e.total_score ?? '—'}</td>
                      <td className="py-2 text-slate-600">{e.grade ?? '—'}</td>
                      <td className="py-2 capitalize text-slate-600">{e.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {profile.data.enrolments.length > 20 && (
                <p className="mt-3 text-xs text-slate-500">Showing 20 of {profile.data.enrolments.length} enrolments.</p>
              )}
            </div>
          ))}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-navy-900">
          <ClipboardList size={15} />
          Interventions
        </h2>
        {interventions.isLoading && <CardSkeleton rows={3} />}
        {interventions.isError && <ErrorState onRetry={() => interventions.refetch()} message="Could not load interventions." />}
        {interventions.data &&
          (interventions.data.length === 0 ? (
            <EmptyState icon={ClipboardList} title="No interventions logged" guidance="Interventions for this student will appear here." />
          ) : (
            <ul className="mb-4 divide-y divide-slate-100">
              {interventions.data.map((item) => (
                <li key={item.id} className="py-2 text-sm">
                  <p className="font-medium capitalize text-navy-900">{item.action_type.replace(/_/g, ' ')}</p>
                  <p className="text-xs capitalize text-slate-500">
                    {item.status.replace(/_/g, ' ')} · {new Date(item.created_at).toLocaleDateString()}
                  </p>
                  {item.notes && <p className="mt-1 text-slate-600">{item.notes}</p>}
                </li>
              ))}
            </ul>
          ))}

        {canManageIntervention && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              createMutation.mutate()
            }}
            className="space-y-3 border-t border-slate-100 pt-4"
          >
            <h3 className="text-sm font-semibold text-navy-900">Log a new intervention</h3>
            <div className="flex flex-wrap gap-3">
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
              >
                {ACTION_TYPES.map((a) => (
                  <option key={a.value} value={a.value}>
                    {a.label}
                  </option>
                ))}
              </select>
            </div>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notes (optional)"
              rows={2}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
            />
            {createMutation.isError && <p className="text-sm text-[#B91C1C]">Could not log this intervention.</p>}
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex items-center gap-2 rounded-md bg-navy-900 px-4 py-1.5 text-sm font-semibold text-white hover:bg-navy-700 disabled:opacity-60"
            >
              {createMutation.isPending && <Loader2 size={14} className="animate-spin" />}
              Log intervention
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
