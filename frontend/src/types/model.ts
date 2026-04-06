export interface ModelConfiguration {
  trainer: string
  plans: string
  configuration: string
  available_folds: number[]
  has_postprocessing: boolean
  labels: Record<string, number>
  num_classes: number
  checkpoint_type: string
}

export interface ModelEntry {
  dataset_id: string
  dataset_name: string
  full_dataset_name: string
  configurations: ModelConfiguration[]
}

export interface ModelsResponse {
  models: ModelEntry[]
  nnunet_results_path: string
  scanned_at: string | null
}
