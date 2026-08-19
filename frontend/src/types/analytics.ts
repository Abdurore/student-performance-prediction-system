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
