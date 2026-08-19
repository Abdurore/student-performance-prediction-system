import { UserCircle } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

export function ProfilePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">Profile</h1>
        <p className="text-sm text-slate-500">Your account details.</p>
      </div>

      <div className="card flex items-center gap-4 p-6">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-navy-50 text-navy-900">
          <UserCircle size={32} />
        </span>
        <div>
          <p className="text-lg font-semibold text-navy-900">{user?.full_name}</p>
          <p className="text-sm text-slate-500">{user?.email}</p>
          <p className="mt-1 text-xs font-medium capitalize text-amber-600">{user?.role}</p>
        </div>
      </div>

      <div className="card p-6 text-sm text-slate-500">
        Account details are managed by your institution administrator. Contact them to update your name, email, or role.
      </div>
    </div>
  )
}
