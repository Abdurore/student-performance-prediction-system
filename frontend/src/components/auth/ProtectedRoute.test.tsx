import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ProtectedRoute } from './ProtectedRoute'
import { useAuth } from '@/hooks/useAuth'

vi.mock('@/hooks/useAuth')
const mockedUseAuth = vi.mocked(useAuth)

function renderProtected(allowedRoles?: ('admin' | 'lecturer' | 'adviser' | 'student')[]) {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route path="/" element={<div>Home page</div>} />
        <Route element={<ProtectedRoute allowedRoles={allowedRoles} />}>
          <Route path="/dashboard" element={<div>Protected content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('shows a loading state while auth is resolving, without redirecting', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: true, login: vi.fn(), logout: vi.fn() })
    renderProtected()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.queryByText('Login page')).not.toBeInTheDocument()
  })

  it('redirects to /login when there is no authenticated user', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: vi.fn(), logout: vi.fn() })
    renderProtected()
    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('renders the protected content for an authenticated user with no role restriction', () => {
    mockedUseAuth.mockReturnValue({
      user: { id: 1, email: 'a@b.com', full_name: 'A', role: 'student', student_id: 1, is_active: true },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderProtected()
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('redirects to / when the user role is not in allowedRoles', () => {
    mockedUseAuth.mockReturnValue({
      user: { id: 1, email: 'a@b.com', full_name: 'A', role: 'student', student_id: 1, is_active: true },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderProtected(['admin', 'lecturer', 'adviser'])
    expect(screen.getByText('Home page')).toBeInTheDocument()
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
  })

  it('renders the protected content when the user role is in allowedRoles', () => {
    mockedUseAuth.mockReturnValue({
      user: { id: 1, email: 'a@b.com', full_name: 'A', role: 'admin', student_id: null, is_active: true },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderProtected(['admin', 'lecturer', 'adviser'])
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })
})
