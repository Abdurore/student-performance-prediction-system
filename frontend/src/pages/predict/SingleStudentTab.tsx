import { useState } from 'react'
import { StudentPicker } from '@/components/predictions/StudentPicker'
import { PredictionPanel } from '@/components/predictions/PredictionPanel'
import type { StudentListItem } from '@/types/student'

export function SingleStudentTab() {
  const [selected, setSelected] = useState<StudentListItem | null>(null)

  if (!selected) {
    return (
      <div className="card p-5">
        <h2 className="mb-3 text-sm font-semibold text-navy-900">Choose a student</h2>
        <StudentPicker onSelect={setSelected} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="card flex items-center justify-between p-4">
        <div>
          <p className="text-sm font-medium text-navy-900">
            {selected.first_name} {selected.last_name}
          </p>
          <p className="text-xs text-slate-500">{selected.matric_no}</p>
        </div>
        <button
          type="button"
          onClick={() => setSelected(null)}
          className="text-sm font-medium text-navy-900 underline hover:text-amber-600"
        >
          Change student
        </button>
      </div>
      <PredictionPanel studentId={selected.id} />
    </div>
  )
}
