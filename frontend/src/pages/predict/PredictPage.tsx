import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SingleStudentTab } from './SingleStudentTab'
import { BatchUploadTab } from './BatchUploadTab'

type Tab = 'single' | 'batch'

export function PredictPage() {
  const [searchParams] = useSearchParams()
  const [tab, setTab] = useState<Tab>(searchParams.get('ids') ? 'batch' : 'single')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">Predict</h1>
        <p className="text-sm text-slate-500">Run a live prediction for one student, or upload a CSV to predict many at once.</p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(['single', 'batch'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium ${
              tab === t ? 'border-b-2 border-amber-600 text-navy-900' : 'text-slate-500 hover:text-navy-900'
            }`}
          >
            {t === 'single' ? 'Single student' : 'Batch upload'}
          </button>
        ))}
      </div>

      {tab === 'single' ? <SingleStudentTab /> : <BatchUploadTab />}
    </div>
  )
}
