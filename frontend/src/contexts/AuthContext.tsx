import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getStoredToken, setStoredToken } from '@/lib/api'
import { getMe, login as loginRequest } from '@/lib/endpoints'
import type { UserProfile } from '@/types/auth'

interface AuthContextValue {
  user: UserProfile | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = getStoredToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => {
        setStoredToken(null)
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const token = await loginRequest(email, password)
    setStoredToken(token.access_token)
    const profile = await getMe()
    setUser(profile)
  }, [])

  const logout = useCallback(() => {
    setStoredToken(null)
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, isLoading, login, logout }), [user, isLoading, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
