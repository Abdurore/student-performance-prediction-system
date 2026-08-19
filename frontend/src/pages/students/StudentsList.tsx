import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { keepPreviousData } from '@tanstack/react-query'
import { Search, Target, Users } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { getStudents } from '@/lib/endpoints'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useAuth } from '@/hooks/useAuth'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { RiskBadge } from '@/components/ui/RiskBadge'
import type { RiskTier } from '@/types/prediction'

const LEVELS = [100, 200, 300, 400]
const RISK_TIERS: RiskTier[] = ['low', 'moderate', 'high', 'critical']
const PAGE_SIZE = 20

export function StudentsList() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const canBatchPredict = user?.role === 'admin' || user?.role === 'lecturer' || user?.role === 'adviser'

  const [search, setSearch] = useState('')
  const [level, setLevel] = useState<string>('')
  const [riskTier, setRiskTier] = useState<string>('')
  const [department, setDepartment] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const debouncedSearch = useDebouncedValue(search, 300)
  const debouncedDepartment = useDebouncedValue(department, 300)

  const students = useQuery({
    queryKey: ['students', { debouncedSearch, level, riskTier, debouncedDepartment, page }],
    queryFn: () =>
      getStudents({
        search: debouncedSearch || undefined,
        level: level ? Number(level) : undefined,
        risk_tier: riskTier || undefined,
        department: debouncedDepartment || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    placeholderData: keepPreviousData,
  })

  const totalPages = students.data ? Math.max(1, Math.ceil(students.data.total / PAGE_SIZE)) : 1

  function resetToFirstPage<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v)
      setPage(1)
    }
  }

  function toggleSelected(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const pageIds = students.data?.items.map((s) => s.id) ?? []
  const allOnPageSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id))

  function toggleSelectAllOnPage() {
    setSelected((prev) => {
      const next = new Set(prev)
      if (allOnPageSelected) {
        pageIds.forEach((id) => next.delete(id))
      } else {
        pageIds.forEach((id) => next.add(id))
      }
      return next
    })
  }

  function handlePredictSelected() {
    navigate(`/predict?ids=${Array.from(selected).join(',')}`)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">Students</h1>
        <p className="text-sm text-slate-500">Search and filter the students you have access to.</p>
      </div>

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="min-w-[220px] flex-1">
          <label className="mb-1 block text-xs font-medium text-slate-500">Search</label>
          <div className="relative">
            <Search size={15} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(e) => resetToFirstPage(setSearch)(e.target.value)}
              placeholder="Name or matric number"
              className="w-full rounded-md border border-slate-300 py-1.5 pl-8 pr-3 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
            />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Department</label>
          <input
            value={department}
            onChange={(e) => resetToFirstPage(setDepartment)(e.target.value)}
            placeholder="e.g. Computer Science"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Level</label>
          <select
            value={level}
            onChange={(e) => resetToFirstPage(setLevel)(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
          >
            <option value="">All levels</option>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Risk tier</label>
          <select
            value={riskTier}
            onChange={(e) => resetToFirstPage(setRiskTier)(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
          >
            <option value="">All tiers</option>
            {RISK_TIERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {canBatchPredict && selected.size > 0 && (
        <div className="card flex items-center justify-between p-3">
          <p className="text-sm text-slate-600">{selected.size} student{selected.size === 1 ? '' : 's'} selected</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setSelected(new Set())}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-navy-900 hover:bg-slate-100"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={handlePredictSelected}
              className="flex items-center gap-2 rounded-md bg-navy-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-navy-700"
            >
              <Target size={14} />
              Predict selected
            </button>
          </div>
        </div>
      )}

      <div className="card p-5">
        {students.isLoading && <CardSkeleton rows={8} />}
        {students.isError && <ErrorState onRetry={() => students.refetch()} message="Could not load students." />}
        {students.data &&
          (students.data.items.length === 0 ? (
            <EmptyState icon={Users} title="No students found" guidance="Try adjusting your search or filters." />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs uppercase tracking-wide text-slate-400">
                      {canBatchPredict && (
                        <th className="w-8 pb-2">
                          <input type="checkbox" checked={allOnPageSelected} onChange={toggleSelectAllOnPage} />
                        </th>
                      )}
                      <th className="pb-2">Student</th>
                      <th className="pb-2">Department</th>
                      <th className="pb-2">Level</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2">Risk</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {students.data.items.map((student) => (
                      <tr key={student.id}>
                        {canBatchPredict && (
                          <td className="py-2">
                            <input
                              type="checkbox"
                              checked={selected.has(student.id)}
                              onChange={() => toggleSelected(student.id)}
                            />
                          </td>
                        )}
                        <td className="py-2">
                          <Link to={`/students/${student.id}`} className="font-medium text-navy-900 hover:text-amber-600">
                            {student.first_name} {student.last_name}
                          </Link>
                          <p className="text-xs text-slate-500">{student.matric_no}</p>
                        </td>
                        <td className="py-2 text-slate-600">{student.department}</td>
                        <td className="py-2 text-slate-600">{student.level}</td>
                        <td className="py-2 text-slate-600">{student.is_active ? 'Active' : 'Inactive'}</td>
                        <td className="py-2">{student.risk_tier ? <RiskBadge tier={student.risk_tier as RiskTier} /> : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
                <p>
                  Page {page} of {totalPages} · {students.data.total} students
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="rounded-md border border-slate-300 px-3 py-1 font-medium text-navy-900 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="rounded-md border border-slate-300 px-3 py-1 font-medium text-navy-900 disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ))}
      </div>
    </div>
  )
}
