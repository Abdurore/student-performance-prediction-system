import { useAuth } from '@/hooks/useAuth'
import { AdminDashboard } from '@/pages/dashboard/AdminDashboard'
import { LecturerDashboard } from '@/pages/dashboard/LecturerDashboard'
import { AdviserDashboard } from '@/pages/dashboard/AdviserDashboard'
import { StudentDashboard } from '@/pages/dashboard/StudentDashboard'

export function Dashboard() {
  const { user } = useAuth()

  switch (user?.role) {
    case 'admin':
      return <AdminDashboard />
    case 'lecturer':
      return <LecturerDashboard />
    case 'adviser':
      return <AdviserDashboard />
    case 'student':
      return <StudentDashboard />
    default:
      return null
  }
}
