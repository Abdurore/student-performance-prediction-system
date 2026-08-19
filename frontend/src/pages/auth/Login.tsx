import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { GraduationCap, Loader2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { ApiError } from '@/lib/api'

const DEMO_ACCOUNTS = [
  { role: 'Admin', email: 'admin@university.edu.ng' },
  { role: 'Lecturer', email: 'lecturer01@university.edu.ng' },
  { role: 'Adviser', email: 'adviser01@university.edu.ng' },
  { role: 'Student', email: 'eco.24.00002@university.edu.ng' },
]
const DEMO_PASSWORD = 'Demo@12345'

export function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user) {
    const redirectTo = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={redirectTo} replace />
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to sign in. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function useDemoAccount(demoEmail: string) {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
    setError(null)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-navy-900 text-white">
            <GraduationCap size={22} />
          </span>
          <h1 className="text-lg font-semibold text-navy-900">Student Performance Prediction</h1>
          <p className="text-sm text-slate-500">Sign in to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4 p-6">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-navy-600 focus:outline-none focus:ring-1 focus:ring-navy-600"
            />
          </div>

          {error && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-[#B91C1C]">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-navy-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-navy-700 disabled:opacity-60"
          >
            {isSubmitting && <Loader2 size={16} className="animate-spin" />}
            Sign in
          </button>
        </form>

        <div className="mt-6 rounded-lg border border-amber-100 bg-amber-50 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-600">
            Demo credentials (offline academic demo)
          </p>
          <ul className="space-y-1.5 text-sm">
            {DEMO_ACCOUNTS.map((account) => (
              <li key={account.email} className="flex items-center justify-between gap-3">
                <span className="text-slate-600">
                  <span className="font-medium text-navy-900">{account.role}:</span> {account.email}
                </span>
                <button
                  type="button"
                  onClick={() => useDemoAccount(account.email)}
                  className="shrink-0 rounded border border-amber-200 bg-white px-2 py-0.5 text-xs font-medium text-amber-600 hover:bg-amber-100"
                >
                  Use
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-500">
            Password for all demo accounts: <span className="font-mono">{DEMO_PASSWORD}</span>
          </p>
        </div>
      </div>
    </div>
  )
}
