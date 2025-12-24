import { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const loc = useLocation()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: loc }} />
  }
  return <>{children}</>
}
