import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AlertTriangle, Download, Loader2, Upload } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { predictBatch } from '@/lib/endpoints'
import { buildBatchTemplateCsv, parseStudentIdsCsv, type ParsedBatchCsv } from '@/lib/csv'
import { triggerBlobDownload } from '@/lib/download'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { ErrorState } from '@/components/ui/ErrorState'
import type { RiskTier } from '@/types/prediction'

export function BatchUploadTab() {
  const [searchParams] = useSearchParams()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [parsed, setParsed] = useState<ParsedBatchCsv | null>(null)
  const [source, setSource] = useState<'csv' | 'selection' | null>(null)

  const batchMutation = useMutation({ mutationFn: (ids: number[]) => predictBatch(ids) })

  useEffect(() => {
    const idsParam = searchParams.get('ids')
    if (!idsParam) return
    const ids = Array.from(
      new Set(
        idsParam
          .split(',')
          .map((v) => Number(v.trim()))
          .filter((v) => Number.isInteger(v) && v > 0),
      ),
    )
    if (ids.length > 0) {
      setParsed({ rows: [], validIds: ids, invalidCount: 0, duplicateCount: 0 })
      setSource('selection')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleDownloadTemplate() {
    const blob = new Blob([buildBatchTemplateCsv()], { type: 'text/csv' })
    triggerBlobDownload(blob, 'batch_predict_template.csv')
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result ?? '')
      setParsed(parseStudentIdsCsv(text))
      setSource('csv')
      batchMutation.reset()
    }
    reader.readAsText(file)
  }

  function handleReset() {
    setParsed(null)
    setSource(null)
    batchMutation.reset()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="space-y-6">
      <div className="card space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-navy-900">Batch prediction</h2>
            <p className="text-sm text-slate-500">
              Upload a CSV of internal student IDs (one per row, header <code className="font-mono">student_id</code>) to run
              risk predictions for many students at once.
            </p>
          </div>
          <button
            type="button"
            onClick={handleDownloadTemplate}
            className="flex shrink-0 items-center gap-2 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-navy-900 hover:bg-slate-100"
          >
            <Download size={15} />
            Download template
          </button>
        </div>

        {source !== 'selection' && (
          <div>
            <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 hover:border-navy-600 hover:text-navy-900">
              <Upload size={16} />
              {parsed ? 'Choose a different CSV file' : 'Choose a CSV file'}
              <input ref={fileInputRef} type="file" accept=".csv,text/csv" onChange={handleFileChange} className="hidden" />
            </label>
          </div>
        )}

        {source === 'selection' && parsed && (
          <p className="text-sm text-slate-600">
            {parsed.validIds.length} student{parsed.validIds.length === 1 ? '' : 's'} selected from the Students list.{' '}
            <button type="button" onClick={handleReset} className="text-navy-900 underline hover:text-amber-600">
              Clear selection
            </button>
          </p>
        )}

        {parsed && source === 'csv' && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-4 text-sm">
            <p className="font-medium text-navy-900">Validation preview</p>
            <ul className="mt-2 space-y-1 text-slate-600">
              <li>{parsed.rows.length} rows read</li>
              <li className="text-[#15803D]">{parsed.validIds.length} valid student IDs</li>
              {parsed.duplicateCount > 0 && <li className="text-[#CA8A04]">{parsed.duplicateCount} duplicate rows skipped</li>}
              {parsed.invalidCount > 0 && (
                <li className="flex items-center gap-1.5 text-[#B91C1C]">
                  <AlertTriangle size={13} />
                  {parsed.invalidCount} rows could not be read as a valid student ID
                </li>
              )}
            </ul>
          </div>
        )}

        {parsed && parsed.validIds.length > 0 && (
          <button
            type="button"
            onClick={() => batchMutation.mutate(parsed.validIds)}
            disabled={batchMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-700 disabled:opacity-60"
          >
            {batchMutation.isPending && <Loader2 size={15} className="animate-spin" />}
            Run batch prediction ({parsed.validIds.length})
          </button>
        )}
      </div>

      {batchMutation.isError && <ErrorState onRetry={() => parsed && batchMutation.mutate(parsed.validIds)} message="Batch prediction failed." />}

      {batchMutation.data && (
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-navy-900">Results</h2>
            <p className="text-sm text-slate-500">
              {batchMutation.data.total_succeeded} of {batchMutation.data.total_requested} succeeded
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-slate-400">
                  <th className="pb-2">Matric no.</th>
                  <th className="pb-2">Risk</th>
                  <th className="pb-2">Probability</th>
                  <th className="pb-2">Predicted GPA</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {batchMutation.data.results.map((row) => (
                  <tr key={row.student_id}>
                    <td className="py-2 font-medium text-navy-900">{row.matric_no}</td>
                    <td className="py-2">
                      {row.risk_tier ? (
                        <RiskBadge tier={row.risk_tier as RiskTier} />
                      ) : (
                        <span className="text-xs text-[#B91C1C]">{row.error ?? 'No result'}</span>
                      )}
                    </td>
                    <td className="py-2 text-slate-600">{row.probability !== null ? `${Math.round(row.probability * 100)}%` : '—'}</td>
                    <td className="py-2 text-slate-600">{row.predicted_gpa !== null ? row.predicted_gpa.toFixed(2) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
