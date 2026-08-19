import type { LucideIcon } from 'lucide-react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  guidance: string
}

export function EmptyState({ icon: Icon = Inbox, title, guidance }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 px-6 py-10 text-center">
      <Icon size={22} className="text-slate-400" />
      <p className="text-sm font-medium text-navy-900">{title}</p>
      <p className="max-w-sm text-sm text-slate-500">{guidance}</p>
    </div>
  )
}
