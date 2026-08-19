import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { getStudents } from '@/lib/endpoints'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import type { StudentListItem } from '@/types/student'

export function StudentPicker({ onSelect }: { onSelect: (student: StudentListItem) => void }) {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 300)

  const students = useQuery({
    queryKey: ['students', 'picker', debouncedSearch],
    queryFn: () => getStudents({ search: debouncedSearch || undefined, page_size: 8 }),
    enabled: debouncedSearch.length > 0,
  })

  return (
    <div>
      <div className="relative max-w-sm">
        <Search size={15} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or matric number"
          className="w-full rounded-md border border-slate-300 py-1.5 pl-8 pr-3 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
        />
      </div>
      {students.data && students.data.items.length > 0 && (
        <ul className="mt-2 max-w-sm divide-y divide-slate-100 rounded-md border border-slate-200">
          {students.data.items.map((student) => (
            <li key={student.id}>
              <button
                type="button"
                onClick={() => onSelect(student)}
                className="flex w-full flex-col items-start px-3 py-2 text-left text-sm hover:bg-slate-50"
              >
                <span className="font-medium text-navy-900">
                  {student.first_name} {student.last_name}
                </span>
                <span className="text-xs text-slate-500">{student.matric_no}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {students.data && debouncedSearch && students.data.items.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">No matching students.</p>
      )}
    </div>
  )
}
