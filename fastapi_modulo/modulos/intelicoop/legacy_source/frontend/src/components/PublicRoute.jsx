import { Navigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export default function PublicRoute({ children }) {
  const { isAuthenticated } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/web" replace />
  }

  return children
}
