import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Download, Loader2 } from 'lucide-react'
import { downloadAtRiskReport, getCorrelations, getCourseDifficulty, getTrends } from '@/lib/endpoints'
import { triggerBlobDownload } from '@/lib/download'
import { ApiError } from '@/lib/api'
import { CardSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { CorrelationHeatmap } from '@/components/analytics/CorrelationHeatmap'

export function AnalyticsPage() {
  const trends = useQuery({ queryKey: ['analytics', 'trends'], queryFn: getTrends })
  const correlations = useQuery({ queryKey: ['analytics', 'correlations'], queryFn: getCorrelations })
  const courseDifficulty = useQuery({ queryKey: ['analytics', 'course-difficulty'], queryFn: getCourseDifficulty })

  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  async function handleDownload() {
    setDownloadError(null)
    setIsDownloading(true)
    try {
      const blob = await downloadAtRiskReport()
      triggerBlobDownload(blob, 'at_risk_register.pdf')
    } catch (err) {
      setDownloadError(err instanceof ApiError ? err.message : 'Could not generate the report.')
    } finally {
      setIsDownloading(false)
    }
  }

  const sortedCourses = [...(courseDifficulty.data?.items ?? [])].sort((a, b) => b.failure_rate - a.failure_rate)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-navy-900">Analytics</h1>
          <p className="text-sm text-slate-500">Feature correlations and course difficulty across the institution.</p>
        </div>
        <button
          type="button"
          onClick={handleDownload}
          disabled={isDownloading}
          className="flex items-center gap-2 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-navy-900 hover:bg-slate-100 disabled:opacity-60"
        >
          {isDownloading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
          Download at-risk register (PDF)
        </button>
      </div>
      {downloadError && <p className="text-sm text-[#B91C1C]">{downloadError}</p>}

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">GPA trend by session</h2>
        {trends.isLoading && <Skeleton className="h-64 w-full" />}
        {trends.isError && <ErrorState onRetry={() => trends.refetch()} message="Could not load session trends." />}
        {trends.data &&
          (trends.data.points.length === 0 ? (
            <EmptyState title="No session history yet" guidance="GPA trends appear once students have completed at least one session." />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trends.data.points}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="session" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 5]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="average_gpa" name="Avg GPA" stroke="#0F2038" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="average_cgpa" name="Avg CGPA" stroke="#D97706" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ))}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">Feature correlations</h2>
        {correlations.isLoading && <Skeleton className="h-64 w-full" />}
        {correlations.isError && <ErrorState onRetry={() => correlations.refetch()} message="Could not load correlations." />}
        {correlations.data && <CorrelationHeatmap data={correlations.data} />}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">Course difficulty</h2>
        {courseDifficulty.isLoading && <CardSkeleton rows={8} />}
        {courseDifficulty.isError && (
          <ErrorState onRetry={() => courseDifficulty.refetch()} message="Could not load course difficulty." />
        )}
        {courseDifficulty.data && (
          <>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={sortedCourses.slice(0, 15)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="course_code" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" interval={0} height={60} />
                <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Bar dataKey="failure_rate" name="Failure rate" fill="#EA580C" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-slate-400">
                  <th className="pb-2">Course</th>
                  <th className="pb-2">Department</th>
                  <th className="pb-2">Completed</th>
                  <th className="pb-2">Avg score</th>
                  <th className="pb-2">Failure rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedCourses.slice(0, 15).map((course) => (
                  <tr key={course.course_id}>
                    <td className="py-2">
                      <p className="font-medium text-navy-900">{course.course_code}</p>
                      <p className="text-xs text-slate-500">{course.title}</p>
                    </td>
                    <td className="py-2 text-slate-600">{course.department}</td>
                    <td className="py-2 text-slate-600">{course.n_completed}</td>
                    <td className="py-2 text-slate-600">{course.average_score.toFixed(1)}</td>
                    <td className="py-2 text-slate-600">{Math.round(course.failure_rate * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {sortedCourses.length > 15 && (
              <p className="mt-3 text-xs text-slate-500">Showing the 15 hardest courses of {sortedCourses.length}, ranked by failure rate.</p>
            )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
