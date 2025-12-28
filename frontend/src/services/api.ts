import axios, { AxiosError, AxiosRequestConfig } from 'axios'

// Prefer relative base URL to leverage Vite dev proxy; override via VITE_API_URL when needed
const API_URL = (import.meta as any).env?.VITE_API_URL ?? '/'

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Simple token storage helpers
const getAccess = () => localStorage.getItem('access_token')
const setAccess = (t?: string) => t ? localStorage.setItem('access_token', t) : localStorage.removeItem('access_token')
const getRefresh = () => localStorage.getItem('refresh_token')

// Attach Authorization header if token exists
api.interceptors.request.use((config) => {
  const token = getAccess()
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  // Optional: multi-tenant host override for dev
  const tenantHost = sessionStorage.getItem('tenant_host')
  if (tenantHost) {
    config.headers = config.headers || {}
    config.headers['Host'] = tenantHost
  }
  return config
})

// Refresh handling: ensure single refresh in-flight and replay queued requests
let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null
let pendingRequests: Array<(token: string | null) => void> = []

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise
  isRefreshing = true
  const refresh = getRefresh()
  if (!refresh) {
    isRefreshing = false
    refreshPromise = null
    return null
  }
  refreshPromise = api.post('/api/v1/auth/refresh', { refresh })
    .then((res) => {
      const data = (res as any).data?.data ?? (res as any).data
      const access = data?.access as string | undefined
      if (access) setAccess(access)
      return access ?? null
    })
    .catch(() => null)
    .finally(() => {
      isRefreshing = false
      const p = pendingRequests
      pendingRequests = []
      p.forEach((cb) => {
        cb(getAccess())
      })
      refreshPromise = null
    })
  return refreshPromise
}

// Response interceptor: on 401, try refresh once then retry the request
api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retry?: boolean })
    const status = error.response?.status
    const isAuthPath = (original?.url || '').includes('/api/v1/auth/')

    if (status === 401 && !original?._retry && !isAuthPath) {
      original._retry = true
      // queue request until refresh resolves
      if (!isRefreshing) {
        await refreshAccessToken()
      } else if (refreshPromise) {
        await refreshPromise
      }
      const newToken = getAccess()
      if (newToken) {
        original.headers = original.headers || {}
        ;(original.headers as any)['Authorization'] = `Bearer ${newToken}`
        return api.request(original)
      } else {
        setAccess(undefined)
      }
    }
    return Promise.reject(error)
  }
)
