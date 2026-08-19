import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Login } from './Login'
import { useAuth } from '@/hooks/useAuth'

vi.mock('@/hooks/useAuth')
const mockedUseAuth = vi.mocked(useAuth)

describe('Login page', () => {
  beforeEach(() => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: vi.fn(), logout: vi.fn() })
  })

  it('shows a visible demo login for every role, per Section I', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    for (const role of ['Admin', 'Lecturer', 'Adviser', 'Student']) {
      expect(screen.getByText(new RegExp(`^${role}:$`))).toBeInTheDocument()
    }
    expect(screen.getByText('Demo@12345')).toBeInTheDocument()
  })

  it('fills the form when a demo account "Use" button is clicked', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)
    const useButtons = screen.getAllByRole('button', { name: 'Use' })
    await user.click(useButtons[0]) // Admin

    expect(screen.getByLabelText('Email')).toHaveValue('admin@university.edu.ng')
    expect(screen.getByLabelText('Password')).toHaveValue('Demo@12345')
  })

  it('calls login with the entered credentials on submit', async () => {
    const login = vi.fn().mockResolvedValue(undefined)
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login, logout: vi.fn() })
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)

    await user.type(screen.getByLabelText('Email'), 'admin@university.edu.ng')
    await user.type(screen.getByLabelText('Password'), 'Demo@12345')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(login).toHaveBeenCalledWith('admin@university.edu.ng', 'Demo@12345')
  })

  it('shows an error message when login fails, rather than silently doing nothing', async () => {
    const login = vi.fn().mockRejectedValue(new Error('network down'))
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login, logout: vi.fn() })
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)

    await user.type(screen.getByLabelText('Email'), 'admin@university.edu.ng')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to sign in. Please try again.')
  })
})
