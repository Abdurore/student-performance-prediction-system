import { GraduationCap, LayoutDashboard, LogOut } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

const NAV_ITEMS = [{ label: 'Dashboard', to: '/', icon: LayoutDashboard }]

export function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="fixed inset-y-0 left-0 flex w-64 flex-col bg-navy-900 text-white">
      <div className="flex items-center gap-2 px-5 py-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10">
          <GraduationCap size={18} />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-semibold">Student Performance</p>
          <p className="text-xs text-navy-100/70">Prediction System</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
                isActive ? 'bg-amber-600 text-white' : 'text-navy-100/80 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 px-3 py-4">
        <div className="mb-2 px-2">
          <p className="truncate text-sm font-medium">{user?.full_name}</p>
          <p className="text-xs capitalize text-navy-100/70">{user?.role}</p>
        </div>
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-navy-100/80 transition hover:bg-white/10 hover:text-white"
        >
          <LogOut size={16} />
          Log out
        </button>
      </div>
    </aside>
  )
}
