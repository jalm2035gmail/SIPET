import axios from 'axios'

import { clearTokens, getRefreshToken, setTokens } from './auth_storage'

const djangoMAINUrl = import.meta.env.VITE_DJANGO_API_URL || '/api'

export async function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) {
    clearTokens()
    throw new Error('No refresh token available')
  }

  const response = await axios.post(`${djangoMAINUrl}/auth/refresh/`, { refresh })
  const newAccess = response.data?.access

  if (!newAccess) {
    clearTokens()
    throw new Error('Refresh did not return access token')
  }

  setTokens({ access: newAccess, refresh })
  return newAccess
}
