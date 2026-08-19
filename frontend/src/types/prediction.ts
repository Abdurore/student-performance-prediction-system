export type RiskTier = 'low' | 'moderate' | 'high' | 'critical'

export interface Contributor {
  feature: string
  rank: number
  shap_value: number
  raw_value: number | string | boolean | null
  sentence: string
}

export interface RiskPrediction {
  probability: number
  risk_tier: RiskTier
  algorithm: string
  top_factors: Contributor[]
}

export interface GpaPrediction {
  predicted_gpa: number
  predicted_cgpa: number
  interval_low: number
  interval_high: number
  algorithm: string
  top_factors: Contributor[]
}

export interface CourseScorePrediction {
  course_id: number
  course_code: string
  predicted_score: number
  algorithm: string
  top_factors: Contributor[]
}

export interface StudentPredictionResponse {
  student_id: number
  session: string
  semester: string
  risk: RiskPrediction | null
  gpa: GpaPrediction | null
  course_scores: CourseScorePrediction[]
}

export interface AtRiskItem {
  student_id: number
  matric_no: string
  full_name: string
  department: string
  level: number
  risk_tier: RiskTier
  probability: number
  adviser_id: number | null
}

export interface AtRiskResponse {
  items: AtRiskItem[]
  total: number
}

export interface BatchPredictionRow {
  student_id: number
  matric_no: string
  risk_tier: RiskTier | null
  probability: number | null
  predicted_gpa: number | null
  error: string | null
}

export interface BatchPredictionResponse {
  total_requested: number
  total_succeeded: number
  results: BatchPredictionRow[]
}
