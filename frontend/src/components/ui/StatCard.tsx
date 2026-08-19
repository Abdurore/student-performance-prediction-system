import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  tone?: 'default' | 'low' | 'moderate' | 'high' | 'critical'
}

const TONE_CLASSES: Record<NonNullable<StatCardProps['tone']>, string> = {
  default: 'bg-navy-50 text-navy-900',
  low: 'bg-green-50 text-[#15803D]',
  moderate: 'bg-yellow-50 text-[#CA8A04]',
  high: 'bg-orange-50 text-[#EA580C]',
  critical: 'bg-red-50 text-[#B91C1C]',
}

export function StatCard({ label, value, icon: Icon, tone = 'default' }: StatCardProps) {
  return (
    <div className="card flex items-center gap-4 p-5">
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${TONE_CLASSES[tone]}`}>
        <Icon size={18} />
      </span>
      <div>
        <p className="text-2xl font-semibold text-navy-900">{value}</p>
        <p className="text-sm text-slate-500">{label}</p>
      </div>
    </div>
  )
}
