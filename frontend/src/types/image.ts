export interface ImageMetadata {
  filename: string
  shape: [number, number, number]
  spacing: [number, number, number]
  orientation: string
  dtype: string
  hu_range: [number, number]
  file_size_bytes: number
  affine: number[][]
}

export interface UploadResponse {
  image_id: string
  filename: string
  metadata: ImageMetadata
}

export interface ImageListItem {
  image_id: string
  filename: string
  shape: [number, number, number]
  spacing: [number, number, number]
}
