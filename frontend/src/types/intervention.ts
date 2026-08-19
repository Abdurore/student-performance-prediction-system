export interface InterventionRead {
  id: number
  student_id: number
  prediction_id: number | null
  created_by: number
  action_type: string
  notes: string | null
  status: string
  outcome_note: string | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}
