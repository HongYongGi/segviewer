import { create } from 'zustand'
import type { InferenceRequest, InferenceStatus } from '../types/inference'
import apiClient from '../api/client'

interface InferenceState {
  jobId: string | null
  status: InferenceStatus | null
  running: boolean

  runInference: (request: InferenceRequest) => Promise<void>
  reset: () => void
}

export const useInferenceStore = create<InferenceState>((set, get) => ({
  jobId: null,
  status: null,
  running: false,

  runInference: async (request: InferenceRequest) => {
    set({ running: true, status: null })
    try {
      const res = await apiClient.post('/inference/run', request)
      const jobId = res.data.job_id

      set({ jobId })

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/inference/${jobId}`
      const ws = new WebSocket(wsUrl)

      ws.onmessage = (event) => {
        const data: InferenceStatus = JSON.parse(event.data)
        set({ status: data })
        if (data.status === 'completed' || data.status === 'failed') {
          set({ running: false })
          ws.close()
        }
      }

      ws.onerror = () => {
        set({ running: false })
        ws.close()
        pollStatus(jobId, set)
      }

      ws.onclose = () => {
        const current = get().status
        if (current && current.status !== 'completed' && current.status !== 'failed') {
          pollStatus(jobId, set)
        }
      }
    } catch {
      set({ running: false })
    }
  },

  reset: () => set({ jobId: null, status: null, running: false }),
}))

async function pollStatus(
  jobId: string,
  set: (partial: Partial<InferenceState>) => void
) {
  const poll = async () => {
    try {
      const res = await apiClient.get(`/inference/${jobId}/status`)
      set({ status: res.data })
      if (res.data.status !== 'completed' && res.data.status !== 'failed') {
        setTimeout(poll, 2000)
      } else {
        set({ running: false })
      }
    } catch {
      set({ running: false })
    }
  }
  setTimeout(poll, 2000)
}
