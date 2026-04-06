export interface SegmentationMetadata {
  result_id: string
  image_id: string
  shape: [number, number, number]
  num_classes: number
  labels: Record<string, number>
  voxel_counts: Record<string, number>
  model: {
    dataset: string
    configuration: string
    folds: number[]
  }
  created_at: string
  edited: boolean
  edited_at: string | null
}

export interface LabelInfo {
  id: number
  name: string
  color: [number, number, number]
  visible: boolean
  voxelPercent: number
}
