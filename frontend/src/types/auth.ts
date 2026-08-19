export type UserRole = 'admin' | 'lecturer' | 'adviser' | 'student'

export interface TokenResponse {
  access_token: string
  token_type: string
  role: UserRole
  user_id: number
  full_name: string
}

export interface UserProfile {
  id: number
  email: string
  full_name: string
  role: UserRole
  student_id: number | null
  is_active: boolean
}
