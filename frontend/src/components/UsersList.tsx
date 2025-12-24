import React, { useEffect, useState } from 'react'
import { api } from '../services/api'

type User = { id: number; username: string; email?: string | null; is_staff?: boolean }

export default function UsersList() {
  const [users, setUsers] = useState<User[]>([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await api.get('/api/v1/users', { params: { page, page_size: pageSize } })
        const payload = res.data?.data ?? res.data
        // Handle common shapes: array, { results: [], next, previous }
        if (Array.isArray(payload)) {
          if (!mounted) return
          setUsers(payload)
          setHasNext(payload.length === pageSize)
          setHasPrev(page > 1)
        } else if (payload && Array.isArray(payload.results)) {
          if (!mounted) return
          setUsers(payload.results)
          setHasNext(Boolean(payload.next))
          setHasPrev(Boolean(payload.previous))
        } else {
          // fallback: attempt to coerce single object
          if (!mounted) return
          setUsers(payload ? [payload] : [])
          setHasNext(false)
          setHasPrev(page > 1)
        }
      } catch (err: any) {
        setError(err?.message || 'Erro ao carregar usuários')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    load()
    return () => {
      mounted = false
    }
  }, [page, pageSize])

  return (
    <div>
      <h3>Usuários</h3>
      {loading && <div>Carregando...</div>}
      {error && <div style={{ color: 'crimson' }}>{error}</div>}
      {!loading && users.length === 0 && <div>Nenhum usuário encontrado</div>}
      {users.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Usuário</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Email</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Staff</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td style={{ padding: 8, borderBottom: '1px solid #f3f3f3' }}>{u.id}</td>
                <td style={{ padding: 8, borderBottom: '1px solid #f3f3f3' }}>{u.username}</td>
                <td style={{ padding: 8, borderBottom: '1px solid #f3f3f3' }}>{u.email || '—'}</td>
                <td style={{ padding: 8, borderBottom: '1px solid #f3f3f3' }}>{u.is_staff ? 'Sim' : 'Não'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={!hasPrev || loading}>Anterior</button>
        <div style={{ alignSelf: 'center' }}>Página {page}</div>
        <button onClick={() => setPage(p => p + 1)} disabled={!hasNext || loading}>Próxima</button>
      </div>
    </div>
  )
}
