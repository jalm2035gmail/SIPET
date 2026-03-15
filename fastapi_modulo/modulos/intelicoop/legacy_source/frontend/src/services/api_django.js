import axios from 'axios'
import { getAccessToken } from './auth_storage'
import { refreshAccessToken } from './token_refresh'

export const djangoApi = axios.create({
  MAINURL: import.meta.env.VITE_DJANGO_API_URL || '/api'
})

djangoApi.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

djangoApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error?.response?.status
    const requestUrl = originalRequest?.url || ''
    const isAuthRoute = requestUrl.includes('/auth/login/') || requestUrl.includes('/auth/refresh/')

    if (status === 401 && originalRequest && !originalRequest._retry && !isAuthRoute) {
      originalRequest._retry = true
      try {
        const newAccess = await refreshAccessToken()
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return djangoApi(originalRequest)
      } catch (refreshError) {
        window.location.href = '/backend/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
