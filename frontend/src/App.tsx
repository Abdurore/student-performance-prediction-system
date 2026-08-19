import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AppShell } from '@/components/layout/AppShell'
import { Login } from '@/pages/auth/Login'
import { Dashboard } from '@/pages/Dashboard'
import { StudentsList } from '@/pages/students/StudentsList'
import { StudentDetail } from '@/pages/students/StudentDetail'
import { InterventionsList } from '@/pages/interventions/InterventionsList'
import { AnalyticsPage } from '@/pages/analytics/AnalyticsPage'
import { ModelsPage } from '@/pages/models/ModelsPage'
import { ProfilePage } from '@/pages/profile/ProfilePage'

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/students" element={<StudentsList />} />
          <Route path="/students/:id" element={<StudentDetail />} />
          <Route path="/interventions" element={<InterventionsList />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route element={<ProtectedRoute allowedRoles={['admin', 'lecturer', 'adviser']} />}>
            <Route path="/analytics" element={<AnalyticsPage />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route path="/models" element={<ModelsPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
