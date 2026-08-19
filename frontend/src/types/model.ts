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

export interface ClassificationMetrics {
  accuracy: number
  precision_macro: number
  recall_macro: number
  f1_macro: number
  roc_auc: number
  pr_auc: number
  confusion_matrix: number[][]
  roc_curve: { fpr: number[]; tpr: number[] }
  calibration_curve: { prob_true: number[]; prob_pred: number[] }
}

export interface RegressionMetrics {
  mae: number
  rmse: number
  r2: number
  mape: number
  residual_plot_data: { y_true: number[]; residual: number[] }
  predicted_vs_actual_data: { y_true: number[]; y_pred: number[] }
}
