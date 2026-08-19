import { useQuery } from '@tanstack/react-query'
import { BookOpen, Users } from 'lucide-react'
import { getAtRisk, getCourses } from '@/lib/endpoints'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { StatCard } from '@/components/ui/StatCard'
import { useAuth } from '@/hooks/useAuth'

export function LecturerDashboard() {
  const { user } = useAuth()
  const courses = useQuery({ queryKey: ['courses'], queryFn: getCourses })
  const atRisk = useQuery({ queryKey: ['predictions', 'at-risk'], queryFn: () => getAtRisk() })

  const myCourses = courses.data?.filter((c) => c.lecturer_id === user?.id) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">My courses</h1>
        <p className="text-sm text-slate-500">Courses you teach and the risk profile of students enrolled in them.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard label="Courses taught" value={myCourses.length} icon={BookOpen} />
        <StatCard label="Students at risk" value={atRisk.data?.total ?? 0} icon={Users} tone="high" />
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">Courses</h2>
        {courses.isLoading && <CardSkeleton rows={4} />}
        {courses.isError && <ErrorState onRetry={() => courses.refetch()} message="Could not load your courses." />}
        {courses.data &&
          (myCourses.length === 0 ? (
            <EmptyState icon={BookOpen} title="No courses assigned" guidance="Courses you are assigned to teach will appear here." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-slate-400">
                    <th className="pb-2">Code</th>
                    <th className="pb-2">Title</th>
                    <th className="pb-2">Level</th>
                    <th className="pb-2">Semester</th>
                    <th className="pb-2">Units</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {myCourses.map((course) => (
                    <tr key={course.id}>
                      <td className="py-2 font-medium text-navy-900">{course.course_code}</td>
                      <td className="py-2 text-slate-600">{course.title}</td>
                      <td className="py-2 text-slate-600">{course.level}</td>
                      <td className="py-2 text-slate-600 capitalize">{course.semester}</td>
                      <td className="py-2 text-slate-600">{course.credit_units}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">Class risk</h2>
        {atRisk.isLoading && <CardSkeleton rows={5} />}
        {atRisk.isError && <ErrorState onRetry={() => atRisk.refetch()} message="Could not load class risk." />}
        {atRisk.data &&
          (atRisk.data.items.length === 0 ? (
            <EmptyState title="No at-risk students" guidance="Students in your courses flagged as moderate risk or above will be listed here." />
          ) : (
            <>
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
                    {atRisk.data.items.slice(0, 10).map((item) => (
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
              {atRisk.data.items.length > 10 && (
                <p className="mt-3 text-xs text-slate-500">
                  Showing 10 of {atRisk.data.items.length} students at risk across your courses.
                </p>
              )}
            </>
          ))}
      </div>
    </div>
  )
}
