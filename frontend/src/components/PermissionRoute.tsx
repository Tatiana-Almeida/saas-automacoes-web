import { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function PermissionRoute({ children, require }: { children: ReactNode; require: string | string[] }) {
  const { isAuthenticated, hasPermission } = useAuth()
  const loc = useLocation()
  const needs: string[] = Array.isArray(require) ? require : [require]

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: loc }} />
  }
  const ok = needs.every((p) => hasPermission(p))
  if (!ok) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
