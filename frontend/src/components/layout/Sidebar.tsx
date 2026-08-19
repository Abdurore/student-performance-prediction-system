import { BarChart3, ClipboardList, Cpu, GraduationCap, LayoutDashboard, LogOut, Target, User, Users } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import type { UserRole } from '@/types/auth'

interface NavItem {
  label: string
  to: string
  icon: typeof LayoutDashboard
  end?: boolean
  roles?: UserRole[]
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, end: true },
  { label: 'Students', to: '/students', icon: Users },
  { label: 'Interventions', to: '/interventions', icon: ClipboardList },
  { label: 'Predict', to: '/predict', icon: Target, roles: ['admin', 'lecturer', 'adviser'] },
  { label: 'Analytics', to: '/analytics', icon: BarChart3, roles: ['admin', 'lecturer', 'adviser'] },
  { label: 'Models', to: '/models', icon: Cpu, roles: ['admin'] },
  { label: 'Profile', to: '/profile', icon: User },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  const items = NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role)))

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
        {items.map(({ label, to, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
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
