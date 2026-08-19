import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, BarChart3, CheckCircle2, Loader2, RotateCw, ShieldCheck } from 'lucide-react'
import { activateModel, getModelComparison, getModelFairness, getModels, retrainModels } from '@/lib/endpoints'
import { ApiError } from '@/lib/api'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'
import { FairnessReport } from '@/components/models/FairnessReport'
import { ModelDiagnostics } from '@/components/models/ModelDiagnostics'
import type { ModelComparisonRow } from '@/types/model'

const TASKS = [
  { value: 'risk_classification', label: 'Risk classification' },
  { value: 'gpa_regression', label: 'GPA regression' },
  { value: 'course_score', label: 'Course score' },
]

function versionFor(row: ModelComparisonRow): string {
  return `${row.task}__${row.algorithm}`
}

function ComparisonRow({ row, metrics }: { row: ModelComparisonRow; metrics: Record<string, unknown> | undefined }) {
  const queryClient = useQueryClient()
  const [showFairness, setShowFairness] = useState(false)
  const [showDiagnostics, setShowDiagnostics] = useState(false)

  const activateMutation = useMutation({
    mutationFn: () => activateModel(versionFor(row)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['models'] }),
  })
  const fairness = useQuery({
    queryKey: ['models', 'fairness', versionFor(row)],
    queryFn: () => getModelFairness(versionFor(row)),
    enabled: showFairness,
  })

  function handleActivate() {
    if (window.confirm(`Activate ${row.algorithm} as the live model for ${row.task}? This affects real predictions immediately.`)) {
      activateMutation.mutate()
    }
  }

  return (
    <>
      <tr>
        <td className="py-2 text-slate-600">{row.task.replace(/_/g, ' ')}</td>
        <td className="py-2 font-medium text-navy-900">{row.algorithm.replace(/_/g, ' ')}</td>
        <td className="py-2 text-slate-600">
          {row.primary_metric_value !== null ? `${row.primary_metric_name}: ${row.primary_metric_value.toFixed(3)}` : '—'}
        </td>
        <td className="py-2 text-slate-600">{row.cv_std !== null ? row.cv_std.toFixed(3) : '—'}</td>
        <td className="py-2">
          {row.leakage_flag ? (
            <span className="flex items-center gap-1 text-xs font-medium text-[#B91C1C]">
              <AlertTriangle size={13} /> Leakage risk
            </span>
          ) : (
            <span className="text-xs text-slate-400">None</span>
          )}
        </td>
        <td className="py-2">
          {row.is_active ? (
            <span className="flex items-center gap-1 text-xs font-semibold text-[#15803D]">
              <CheckCircle2 size={13} /> Active
            </span>
          ) : (
            <button
              type="button"
              onClick={handleActivate}
              disabled={activateMutation.isPending}
              className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-navy-900 hover:bg-slate-100 disabled:opacity-60"
            >
              {activateMutation.isPending ? 'Activating…' : 'Activate'}
            </button>
          )}
        </td>
        <td className="py-2">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowFairness((v) => !v)}
              className="flex items-center gap-1 text-xs font-medium text-navy-900 hover:text-amber-600"
            >
              <ShieldCheck size={13} />
              {showFairness ? 'Hide' : 'Fairness'}
            </button>
            <button
              type="button"
              onClick={() => setShowDiagnostics((v) => !v)}
              className="flex items-center gap-1 text-xs font-medium text-navy-900 hover:text-amber-600"
            >
              <BarChart3 size={13} />
              {showDiagnostics ? 'Hide' : 'Diagnostics'}
            </button>
          </div>
        </td>
      </tr>
      {showFairness && (
        <tr>
          <td colSpan={7} className="bg-slate-50 px-3 py-4">
            {fairness.isLoading && <p className="text-sm text-slate-500">Loading fairness report…</p>}
            {fairness.isError && (
              <p className="text-sm text-slate-500">
                {fairness.error instanceof ApiError && fairness.error.status === 404
                  ? 'No fairness report has been generated for this model yet.'
                  : 'Could not load the fairness report.'}
              </p>
            )}
            {fairness.data && <FairnessReport report={fairness.data} />}
          </td>
        </tr>
      )}
      {showDiagnostics && (
        <tr>
          <td colSpan={7} className="bg-slate-50 px-3 py-4">
            {metrics ? <ModelDiagnostics metrics={metrics} /> : <p className="text-sm text-slate-500">No metrics available.</p>}
          </td>
        </tr>
      )}
    </>
  )
}

export function ModelsPage() {
  const comparison = useQuery({ queryKey: ['models', 'comparison'], queryFn: getModelComparison })
  const registry = useQuery({ queryKey: ['models', 'registry'], queryFn: getModels })
  const metricsByVersion = new Map((registry.data ?? []).map((m) => [m.version, m.metrics]))
  const queryClient = useQueryClient()
  const [selectedTasks, setSelectedTasks] = useState<string[]>([])

  const retrainMutation = useMutation({
    mutationFn: () => retrainModels(selectedTasks.length > 0 ? selectedTasks : undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['models'] }),
  })

  function toggleTask(task: string) {
    setSelectedTasks((prev) => (prev.includes(task) ? prev.filter((t) => t !== task) : [...prev, task]))
  }

  function handleRetrain() {
    const scope = selectedTasks.length > 0 ? selectedTasks.join(', ') : 'all tasks'
    if (
      window.confirm(
        `Retrain ${scope}? This re-trains and tunes every algorithm for the selected task(s) and can take several minutes. The app will be unresponsive to other requests while it runs.`,
      )
    ) {
      retrainMutation.mutate()
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">Models</h1>
        <p className="text-sm text-slate-500">Compare trained algorithms, review fairness audits, and manage the active model per task.</p>
      </div>

      <div className="card p-5">
        <h2 className="mb-3 text-sm font-semibold text-navy-900">Retrain</h2>
        <div className="mb-3 flex flex-wrap gap-4">
          {TASKS.map((t) => (
            <label key={t.value} className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={selectedTasks.includes(t.value)} onChange={() => toggleTask(t.value)} />
              {t.label}
            </label>
          ))}
        </div>
        <button
          type="button"
          onClick={handleRetrain}
          disabled={retrainMutation.isPending}
          className="flex items-center gap-2 rounded-md bg-navy-900 px-4 py-1.5 text-sm font-semibold text-white hover:bg-navy-700 disabled:opacity-60"
        >
          {retrainMutation.isPending ? <Loader2 size={15} className="animate-spin" /> : <RotateCw size={15} />}
          {retrainMutation.isPending ? 'Retraining…' : 'Retrain'}
        </button>
        {retrainMutation.isSuccess && <p className="mt-2 text-sm text-[#15803D]">{retrainMutation.data.message}</p>}
        {retrainMutation.isError && <p className="mt-2 text-sm text-[#B91C1C]">Retraining failed. Check server logs.</p>}
      </div>

      <div className="card p-5">
        <h2 className="mb-4 text-sm font-semibold text-navy-900">Model comparison</h2>
        {comparison.isLoading && <CardSkeleton rows={8} />}
        {comparison.isError && <ErrorState onRetry={() => comparison.refetch()} message="Could not load model comparison." />}
        {comparison.data && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-slate-400">
                  <th className="pb-2">Task</th>
                  <th className="pb-2">Algorithm</th>
                  <th className="pb-2">Primary metric</th>
                  <th className="pb-2">CV std</th>
                  <th className="pb-2">Leakage check</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Fairness</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {comparison.data.rows.map((row) => (
                  <ComparisonRow key={`${row.task}-${row.algorithm}`} row={row} metrics={metricsByVersion.get(versionFor(row))} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
