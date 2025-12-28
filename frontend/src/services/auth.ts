import { api } from './api'

type LoginPayload = { username: string; password: string }

export async function loginApi({ username, password }: LoginPayload) {
  const res = await api.post('/api/v1/auth/token', { username, password })
  const data = res.data?.data ?? res.data
  const access: string | undefined = data?.access
  const refresh: string | undefined = data?.refresh
  if (access) localStorage.setItem('access_token', access)
  if (refresh) localStorage.setItem('refresh_token', refresh)
  return data
}

export async function refreshApi(refresh: string) {
  const res = await api.post('/api/v1/auth/refresh', { refresh })
  const data = res.data?.data ?? res.data
  const access: string | undefined = data?.access
  if (access) localStorage.setItem('access_token', access)
  return data
}

export async function logoutApi() {
  const refresh = localStorage.getItem('refresh_token')
  try {
    if (refresh) await api.post('/api/v1/auth/logout', { refresh })
  } catch (_) {
    // ignore
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }
}
