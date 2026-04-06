import { create } from 'zustand'
import type { ModelEntry, ModelConfiguration } from '../types/model'
import apiClient from '../api/client'

interface ModelState {
  models: ModelEntry[]
  selectedDataset: ModelEntry | null
  selectedConfig: ModelConfiguration | null
  selectedFolds: number[]
  loading: boolean

  fetchModels: () => Promise<void>
  selectDataset: (dataset: ModelEntry | null) => void
  selectConfig: (config: ModelConfiguration | null) => void
  setFolds: (folds: number[]) => void
}

export const useModelStore = create<ModelState>((set) => ({
  models: [],
  selectedDataset: null,
  selectedConfig: null,
  selectedFolds: [],
  loading: false,

  fetchModels: async () => {
    set({ loading: true })
    try {
      const res = await apiClient.get('/models/')
      set({ models: res.data.models, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  selectDataset: (dataset) =>
    set({
      selectedDataset: dataset,
      selectedConfig: dataset?.configurations[0] ?? null,
      selectedFolds: dataset?.configurations[0]?.available_folds ?? [],
    }),

  selectConfig: (config) =>
    set({
      selectedConfig: config,
      selectedFolds: config?.available_folds ?? [],
    }),

  setFolds: (folds) => set({ selectedFolds: folds }),
}))
