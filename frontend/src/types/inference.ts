export interface InferenceRequest {
  image_id: string
  dataset_id: string
  dataset_name: string
  full_dataset_name: string
  trainer: string
  plans: string
  configuration: string
  folds: number[]
  labels: Record<string, number>
}

export interface InferenceStatus {
  job_id: string
  image_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress: number
  stage: string
  stage_detail: string
  result_id: string | null
  error: string | null
  error_message: string | null
  elapsed_seconds: number
  labels: Record<string, number>
}
