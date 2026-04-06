import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300_000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error) {
      const { error: code, message } = error.response.data
      console.error(`[API Error] ${code}: ${message}`)
    }
    return Promise.reject(error)
  },
)

export default apiClient
