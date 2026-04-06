import axios from 'axios'
import { useToastStore } from '../stores/toastStore'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300_000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message || error.message || '알 수 없는 오류가 발생했습니다.'
    const code = error.response?.data?.error || 'UNKNOWN_ERROR'

    console.error(`[API Error] ${code}: ${message}`)

    useToastStore.getState().addToast({
      type: 'error',
      message: `${message}`,
    })

    return Promise.reject(error)
  },
)

export default apiClient
