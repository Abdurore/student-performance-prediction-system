export interface OverviewResponse {
  total_students: number
  active_students: number
  at_risk_low: number
  at_risk_moderate: number
  at_risk_high: number
  at_risk_critical: number
  average_cgpa: number
  total_interventions_open: number
}

export interface SessionGpaPoint {
  session: string
  average_gpa: number
  average_cgpa: number
  n_students: number
}

export interface TrendsResponse {
  points: SessionGpaPoint[]
}

export interface CorrelationsResponse {
  features: string[]
  matrix: number[][]
}

export interface CourseDifficultyItem {
  course_id: number
  course_code: string
  title: string
  department: string
  n_completed: number
  average_score: number
  failure_rate: number
}

export interface CourseDifficultyResponse {
  items: CourseDifficultyItem[]
}

export interface GpaHistogramBucket {
  range_low: number
  range_high: number
  count: number
}

export interface GpaDistributionResponse {
  buckets: GpaHistogramBucket[]
  n_students: number
}

export interface AttendancePerformancePoint {
  attendance_rate: number
  total_score: number
}

export interface AttendancePerformanceResponse {
  points: AttendancePerformancePoint[]
  slope: number
  intercept: number
  n_total: number
  n_sampled: number
}

export interface LevelComparisonItem {
  level: number
  n_students: number
  average_gpa: number
  average_cgpa: number
  at_risk_low: number
  at_risk_moderate: number
  at_risk_high: number
  at_risk_critical: number
}

export interface LevelComparisonResponse {
  levels: LevelComparisonItem[]
}
