import { create } from 'zustand'
import type { LabelInfo, SegmentationMetadata } from '../types/segmentation'
import apiClient from '../api/client'

const DEFAULT_COLORS: [number, number, number][] = [
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

function generateColor(index: number): [number, number, number] {
  if (index < DEFAULT_COLORS.length) return DEFAULT_COLORS[index]
  const hue = ((index + 1) * 137.508) % 360
  return hsvToRgb(hue, 0.8, 0.9)
}

function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  const c = v * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = v - c
  let r = 0, g = 0, b = 0
  if (h < 60) { r = c; g = x }
  else if (h < 120) { r = x; g = c }
  else if (h < 180) { g = c; b = x }
  else if (h < 240) { g = x; b = c }
  else if (h < 300) { r = x; b = c }
  else { r = c; b = x }
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)]
}

interface SegmentationState {
  resultId: string | null
  metadata: SegmentationMetadata | null
  segData: Uint8Array | null
  labels: LabelInfo[]
  opacity: number
  loading: boolean

  loadSegmentation: (resultId: string) => Promise<void>
  toggleVisibility: (labelId: number) => void
  setOpacity: (opacity: number) => void
  reset: () => void
}

export const useSegmentationStore = create<SegmentationState>((set) => ({
  resultId: null,
  metadata: null,
  segData: null,
  labels: [],
  opacity: 50,
  loading: false,

  loadSegmentation: async (resultId: string) => {
    set({ loading: true })
    try {
      const [volRes, metaRes] = await Promise.all([
        apiClient.get(`/segments/${resultId}/volume`, { responseType: 'arraybuffer' }),
        apiClient.get(`/segments/${resultId}/metadata`),
      ])

      const meta: SegmentationMetadata = metaRes.data
      const segData = new Uint8Array(volRes.data)
      const totalVoxels = segData.length

      const labelsMap = meta.labels
      const voxelCounts = meta.voxel_counts || {}
      let colorIdx = 0
      const labels: LabelInfo[] = []

      for (const [name, id] of Object.entries(labelsMap)) {
        if (id === 0) continue
        const count = voxelCounts[String(id)] || 0
        labels.push({
          id,
          name,
          color: generateColor(colorIdx),
          visible: true,
          voxelPercent: totalVoxels > 0 ? (count / totalVoxels) * 100 : 0,
        })
        colorIdx++
      }

      set({ resultId, metadata: meta, segData, labels, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  toggleVisibility: (labelId: number) =>
    set((state) => ({
      labels: state.labels.map((l) =>
        l.id === labelId ? { ...l, visible: !l.visible } : l
      ),
    })),

  setOpacity: (opacity: number) => set({ opacity }),

  reset: () =>
    set({
      resultId: null,
      metadata: null,
      segData: null,
      labels: [],
      opacity: 50,
      loading: false,
    }),
}))
