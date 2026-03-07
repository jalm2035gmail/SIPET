import axios from 'axios'
import { getAccessToken } from './auth_storage'
import { refreshAccessToken } from './token_refresh'

export const fastapiApi = axios.create({
  baseURL: import.meta.env.VITE_FASTAPI_API_URL || 'http://localhost:8001/api'
})

fastapiApi.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

fastapiApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error?.response?.status

    if (status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const newAccess = await refreshAccessToken()
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return fastapiApi(originalRequest)
      } catch (refreshError) {
        window.location.href = '/web/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
