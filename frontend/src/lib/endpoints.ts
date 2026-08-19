import { api } from './api'
import type { TokenResponse, UserProfile } from '@/types/auth'
import type { OverviewResponse, TrendsResponse } from '@/types/analytics'
import type { AtRiskResponse, StudentPredictionResponse } from '@/types/prediction'
import type { Course, PaginatedStudents, StudentProfile } from '@/types/student'
import type { InterventionRead } from '@/types/intervention'

export function login(email: string, password: string): Promise<TokenResponse> {
  return api.post<TokenResponse>('/auth/login', { email, password })
}

export function getMe(): Promise<UserProfile> {
  return api.get<UserProfile>('/auth/me')
}

export function getOverview(): Promise<OverviewResponse> {
  return api.get<OverviewResponse>('/analytics/overview')
}

export function getTrends(): Promise<TrendsResponse> {
  return api.get<TrendsResponse>('/analytics/trends')
}

export interface StudentListFilters {
  level?: number
  department?: string
  risk_tier?: string
  adviser_id?: number
  search?: string
  page?: number
  page_size?: number
}

export function getStudents(filters: StudentListFilters = {}): Promise<PaginatedStudents> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  const query = params.toString()
  return api.get<PaginatedStudents>(`/students${query ? `?${query}` : ''}`)
}

export function getStudent(studentId: number): Promise<StudentProfile> {
  return api.get<StudentProfile>(`/students/${studentId}`)
}

export function getCourses(): Promise<Course[]> {
  return api.get<Course[]>('/courses')
}

export function getAtRisk(tier?: string): Promise<AtRiskResponse> {
  const query = tier ? `?tier=${encodeURIComponent(tier)}` : ''
  return api.get<AtRiskResponse>(`/predictions/at-risk${query}`)
}

export function predictStudent(studentId: number): Promise<StudentPredictionResponse> {
  return api.post<StudentPredictionResponse>(`/predictions/student/${studentId}`)
}

export function getInterventions(studentId?: number): Promise<InterventionRead[]> {
  const query = studentId !== undefined ? `?student_id=${studentId}` : ''
  return api.get<InterventionRead[]>(`/interventions${query}`)
}

export interface InterventionCreatePayload {
  student_id: number
  prediction_id?: number | null
  action_type: string
  notes?: string | null
}

export function createIntervention(payload: InterventionCreatePayload): Promise<InterventionRead> {
  return api.post<InterventionRead>('/interventions', payload)
}
