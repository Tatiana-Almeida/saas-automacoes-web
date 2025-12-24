import { FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<{ username?: string; password?: string }>({})
  const navigate = useNavigate()
  const loc = useLocation() as any
  const { login } = useAuth()

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setFieldErrors({})

    // client-side validation
    const errs: typeof fieldErrors = {}
    if (!username.trim()) errs.username = 'Usuário é obrigatório'
    if (!password) errs.password = 'Senha é obrigatória'
    if (password && password.length < 6) errs.password = 'Senha deve ter ao menos 6 caracteres'
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      setLoading(false)
      return
    }
    try {
      await login(username, password)
      // Sanitize post-login redirect to avoid open redirects
      const allowed = new Set<string>(['/', '/dashboard', '/users', '/settings', '/billing'])
      const sanitizeRedirect = (target?: string) => {
        if (!target) return '/'
        try {
          if (target.startsWith('/')) {
            if (target.startsWith('//')) return '/'
            const url = new URL(target, window.location.origin)
            if (url.origin !== window.location.origin) return '/'
            return allowed.has(url.pathname) ? (url.pathname + url.search + url.hash) : '/'
          }
          const url = new URL(target)
          if (url.origin === window.location.origin && allowed.has(url.pathname)) {
            return url.pathname + url.search + url.hash
          }
        } catch (_) {
          // fall through to default '/'
        }
        return '/'
      }
      const raw = (loc?.state?.from?.pathname as string | undefined) ?? undefined
      const to = sanitizeRedirect(raw)
      navigate(to, { replace: true })
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Falha ao entrar'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 360, margin: '48px auto' }}>
      <h2>Entrar</h2>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <label>
          Usuário ou Email
          <input value={username} onChange={e => setUsername(e.target.value)} required autoFocus aria-invalid={Boolean(fieldErrors.username)} />
          {fieldErrors.username && <div style={{ color: 'crimson', fontSize: 13 }}>{fieldErrors.username}</div>}
        </label>
        <label>
          Senha
          <input value={password} onChange={e => setPassword(e.target.value)} type="password" required aria-invalid={Boolean(fieldErrors.password)} />
          {fieldErrors.password && <div style={{ color: 'crimson', fontSize: 13 }}>{fieldErrors.password}</div>}
        </label>
        {error && <div style={{ color: 'crimson' }}>{error}</div>}
        <button type="submit" disabled={loading || !!Object.keys(fieldErrors).length}>{loading ? 'Entrando...' : 'Entrar'}</button>
      </form>
    </div>
  )
}
