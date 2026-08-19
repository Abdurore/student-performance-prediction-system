import { useMutation } from '@tanstack/react-query'
import { Lightbulb, Loader2, RefreshCw, Target, TrendingUp } from 'lucide-react'
import { predictStudent } from '@/lib/endpoints'
import { ApiError } from '@/lib/api'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { StatCard } from '@/components/ui/StatCard'

export function PredictionPanel({ studentId }: { studentId: number }) {
  const prediction = useMutation({ mutationFn: () => predictStudent(studentId) })

  return (
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
  )
}
