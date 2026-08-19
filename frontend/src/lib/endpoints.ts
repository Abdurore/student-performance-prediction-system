import { api } from './api'
import type { TokenResponse, UserProfile } from '@/types/auth'
import type {
  AttendancePerformanceResponse,
  CorrelationsResponse,
  CourseDifficultyResponse,
  GpaDistributionResponse,
  LevelComparisonResponse,
  OverviewResponse,
  TrendsResponse,
} from '@/types/analytics'
import type { AtRiskResponse, BatchPredictionResponse, StudentPredictionResponse } from '@/types/prediction'
import type { Course, PaginatedStudents, StudentProfile } from '@/types/student'
import type { InterventionRead } from '@/types/intervention'
import type { ModelComparisonResponse, ModelRegistryRead, RetrainResponse } from '@/types/model'

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

export function predictBatch(studentIds: number[]): Promise<BatchPredictionResponse> {
  return api.post<BatchPredictionResponse>('/predictions/batch', { student_ids: studentIds })
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

export interface InterventionUpdatePayload {
  status?: string
  notes?: string | null
  outcome_note?: string | null
}

export function updateIntervention(id: number, payload: InterventionUpdatePayload): Promise<InterventionRead> {
  return api.put<InterventionRead>(`/interventions/${id}`, payload)
}

export function downloadStudentReport(studentId: number): Promise<Blob> {
  return api.postBlob(`/reports/student/${studentId}`)
}

export function downloadAtRiskReport(): Promise<Blob> {
  return api.postBlob('/reports/at-risk')
}

export function getCorrelations(): Promise<CorrelationsResponse> {
  return api.get<CorrelationsResponse>('/analytics/correlations')
}

export function getCourseDifficulty(): Promise<CourseDifficultyResponse> {
  return api.get<CourseDifficultyResponse>('/analytics/course-difficulty')
}

export function getGpaDistribution(): Promise<GpaDistributionResponse> {
  return api.get<GpaDistributionResponse>('/analytics/gpa-distribution')
}

export function getAttendancePerformance(): Promise<AttendancePerformanceResponse> {
  return api.get<AttendancePerformanceResponse>('/analytics/attendance-performance')
}

export function getLevelComparison(): Promise<LevelComparisonResponse> {
  return api.get<LevelComparisonResponse>('/analytics/level-comparison')
}

export function getModels(): Promise<ModelRegistryRead[]> {
  return api.get<ModelRegistryRead[]>('/models')
}

export function getModelComparison(): Promise<ModelComparisonResponse> {
  return api.get<ModelComparisonResponse>('/models/comparison')
}

export function getModelFairness(version: string): Promise<Record<string, unknown>> {
  return api.get<Record<string, unknown>>(`/models/${encodeURIComponent(version)}/fairness`)
}

export function activateModel(version: string): Promise<ModelRegistryRead> {
  return api.post<ModelRegistryRead>(`/models/${encodeURIComponent(version)}/activate`)
}

export function retrainModels(tasks?: string[]): Promise<RetrainResponse> {
  return api.post<RetrainResponse>('/models/retrain', { tasks: tasks ?? null })
}
