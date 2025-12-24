import React, { createContext, useEffect, useState } from 'react'
import { api } from '../services/api'
import { loginApi, logoutApi } from '../services/auth'

type User = { id: number; username: string; email?: string | null; is_staff?: boolean }
type Permissions = string[]

type AuthContextValue = {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  permissions: Permissions
  hasPermission: (perm: string) => boolean
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [permissions, setPermissions] = useState<Permissions>([])

  // Try to load current user if token exists
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    const load = async () => {
      try {
        const me = await api.get('/api/v1/users/me')
        const userData = me.data?.data ?? me.data
        setUser(userData)
        // load permissions via RBAC endpoint
        if (userData?.id) {
          const permsRes = await api.get(`/api/v1/rbac/users/${userData.id}/permissions`)
          const arr = permsRes.data?.data ?? permsRes.data
          const names: string[] = Array.isArray(arr) ? arr.map((p: any) => p?.code || p?.name || String(p)) : []
          setPermissions(names.filter(Boolean))
        }
      } catch (_) {
        setUser(null)
        setPermissions([])
      }
    }
    load()
  }, [])

  const login = async (username: string, password: string) => {
    await loginApi({ username, password })
    const r = await api.get('/api/v1/users/me')
    const userData = r.data?.data ?? r.data
    setUser(userData)
    if (userData?.id) {
      const permsRes = await api.get(`/api/v1/rbac/users/${userData.id}/permissions`)
      const arr = permsRes.data?.data ?? permsRes.data
      const names: string[] = Array.isArray(arr) ? arr.map((p: any) => p?.code || p?.name || String(p)) : []
      setPermissions(names.filter(Boolean))
    }
  }

  const logout = () => {
    logoutApi()
    setUser(null)
    setPermissions([])
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, permissions, hasPermission: (perm: string) => permissions.includes(perm) }}>
      {children}
    </AuthContext.Provider>
  )
}
