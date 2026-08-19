export interface ModelRegistryRead {
  id: number
  version: string
  task: string
  algorithm: string
  trained_at: string
  training_rows: number
  feature_list: string[]
  hyperparameters: Record<string, unknown>
  metrics: Record<string, number>
  fairness_report: Record<string, unknown> | null
  artifact_path: string
  is_active: boolean
}

export interface ModelComparisonRow {
  task: string
  algorithm: string
  is_active: boolean
  primary_metric_name: string
  primary_metric_value: number | null
  cv_std: number | null
  train_test_gap: number | null
  leakage_flag: boolean
}

export interface ModelComparisonResponse {
  rows: ModelComparisonRow[]
}

export interface RetrainResponse {
  status: string
  message: string
}
