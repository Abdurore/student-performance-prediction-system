import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export function AppShell() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <div className="pl-64">
        <main className="mx-auto max-w-content px-6 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
