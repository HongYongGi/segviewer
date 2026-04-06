import { create } from 'zustand'
import type { InferenceRequest, InferenceStatus } from '../types/inference'
import apiClient from '../api/client'

const MAX_POLL_RETRIES = 150  // 2s * 150 = 최대 5분
const POLL_INTERVAL_MS = 2000

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
        pollStatus(jobId, set, 0)
      }

      ws.onclose = () => {
        const current = get().status
        if (current && current.status !== 'completed' && current.status !== 'failed') {
          pollStatus(jobId, set, 0)
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
  set: (partial: Partial<InferenceState>) => void,
  retryCount: number
) {
  if (retryCount >= MAX_POLL_RETRIES) {
    set({
      running: false,
      status: {
        job_id: jobId,
        image_id: '',
        status: 'failed',
        progress: -1,
        stage: 'timeout',
        stage_detail: '',
        result_id: null,
        error: 'POLL_TIMEOUT',
        error_message: `폴링 타임아웃: ${MAX_POLL_RETRIES * POLL_INTERVAL_MS / 1000}초 초과`,
        elapsed_seconds: 0,
        labels: {},
      },
    })
    return
  }

  const poll = async () => {
    try {
      const res = await apiClient.get(`/inference/${jobId}/status`)
      set({ status: res.data })
      if (res.data.status !== 'completed' && res.data.status !== 'failed') {
        setTimeout(() => pollStatus(jobId, set, retryCount + 1), POLL_INTERVAL_MS)
      } else {
        set({ running: false })
      }
    } catch {
      set({ running: false })
    }
  }
  setTimeout(poll, POLL_INTERVAL_MS)
}
