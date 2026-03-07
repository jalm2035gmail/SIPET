import { createContext, useContext, useMemo, useState } from 'react'

import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../services/auth_storage'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => getAccessToken())
  const [refreshToken, setRefreshToken] = useState(() => getRefreshToken())

  const login = ({ access, refresh }) => {
    setTokens({ access, refresh })
    setAccessToken(access || null)
    setRefreshToken(refresh || null)
  }

  const logout = () => {
    clearTokens()
    setAccessToken(null)
    setRefreshToken(null)
  }

  const value = useMemo(
    () => ({
      accessToken,
      refreshToken,
      isAuthenticated: Boolean(accessToken),
      login,
      logout
    }),
    [accessToken, refreshToken]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
