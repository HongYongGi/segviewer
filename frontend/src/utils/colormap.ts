export const DEFAULT_COLORS: [number, number, number][] = [
  [255, 0, 0],
  [0, 0, 255],
  [0, 255, 0],
  [255, 255, 0],
  [0, 255, 255],
  [255, 0, 255],
  [255, 165, 0],
  [128, 0, 255],
  [128, 255, 0],
  [255, 128, 128],
]

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatPercent(value: number): string {
  if (value < 0.01) return '<0.01%'
  return `${value.toFixed(2)}%`
}
