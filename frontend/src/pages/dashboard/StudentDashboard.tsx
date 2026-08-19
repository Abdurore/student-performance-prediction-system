import { useQuery } from '@tanstack/react-query'
import { Lightbulb, Target, TrendingUp } from 'lucide-react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getStudent, predictStudent } from '@/lib/endpoints'
import { ApiError } from '@/lib/api'
import { CardSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { StatCard } from '@/components/ui/StatCard'
import { useAuth } from '@/hooks/useAuth'

export function StudentDashboard() {
  const { user } = useAuth()
  const studentId = user?.student_id ?? null

  const profile = useQuery({
    queryKey: ['student', studentId],
    queryFn: () => getStudent(studentId as number),
    enabled: studentId !== null,
  })
  const prediction = useQuery({
    queryKey: ['predictions', 'student', studentId],
    queryFn: () => predictStudent(studentId as number),
    enabled: studentId !== null,
  })

  if (studentId === null) {
    return (
      <EmptyState
        title="No linked student record"
        guidance="Your account is not linked to a student record yet. Contact your academic adviser for assistance."
      />
    )
  }

  const factorSentences = Array.from(
    new Set([...(prediction.data?.risk?.top_factors ?? []), ...(prediction.data?.gpa?.top_factors ?? [])].map((f) => f.sentence)),
  )
  const noOngoingSemester = prediction.error instanceof ApiError && prediction.error.status === 404

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">My academic outlook</h1>
        <p className="text-sm text-slate-500">Your GPA trend, current outlook, and steps you can take to improve next semester.</p>
      </div>

      {prediction.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[84px]" />
          ))}
        </div>
      )}
      {prediction.isError && noOngoingSemester && (
        <EmptyState
          icon={TrendingUp}
          title="No active semester to predict for"
          guidance="A prediction will appear here once you have an ongoing semester with recorded coursework."
        />
      )}
      {prediction.isError && !noOngoingSemester && (
        <ErrorState onRetry={() => prediction.refetch()} message="Could not load your prediction." />
      )}
      {prediction.data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {prediction.data.gpa && (
            <>
              <StatCard label="Predicted GPA (this semester)" value={prediction.data.gpa.predicted_gpa.toFixed(2)} icon={TrendingUp} />
              <StatCard label="Predicted CGPA" value={prediction.data.gpa.predicted_cgpa.toFixed(2)} icon={Target} />
            </>
          )}
          {prediction.data.risk && (
            <div className="card flex items-center justify-between p-5">
              <div>
                <p className="text-sm text-slate-500">Current outlook</p>
                <div className="mt-1">
                  <RiskBadge tier={prediction.data.risk.risk_tier} />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">GPA / CGPA trend</h2>
        {profile.isLoading && <Skeleton className="h-64 w-full" />}
        {profile.isError && <ErrorState onRetry={() => profile.refetch()} message="Could not load your academic history." />}
        {profile.data &&
          (profile.data.academic_history.length === 0 ? (
            <EmptyState title="No academic history yet" guidance="Your GPA trend will appear here once a semester has been completed." />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart
                data={profile.data.academic_history.map((item) => ({ ...item, label: `${item.session} S${item.semester}` }))}
              >
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 5]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="gpa" name="GPA" stroke="#0F2038" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="cgpa" name="CGPA" stroke="#D97706" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ))}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-navy-900">
          <Lightbulb size={16} className="text-amber-600" />
          Focus areas for next semester
        </h2>
        {prediction.isLoading && <CardSkeleton rows={3} />}
        {prediction.isError && noOngoingSemester && (
          <EmptyState
            icon={Lightbulb}
            title="No focus areas yet"
            guidance="Personalised suggestions will appear here once you have an ongoing semester to predict for."
          />
        )}
        {prediction.isError && !noOngoingSemester && (
          <ErrorState onRetry={() => prediction.refetch()} message="Could not load your focus areas." />
        )}
        {prediction.data &&
          (factorSentences.length === 0 ? (
            <EmptyState
              icon={Lightbulb}
              title="No focus areas yet"
              guidance="Personalised suggestions will appear here once you have enough academic history for a prediction."
            />
          ) : (
            <ul className="space-y-2">
              {factorSentences.map((sentence) => (
                <li key={sentence} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-600" />
                  {sentence}
                </li>
              ))}
            </ul>
          ))}
      </div>
    </div>
  )
}
