import { useEffect, useState } from 'react'
import { api } from '../services/api'

type AuditLog = {
  id?: number
  action?: string
  method?: string
  path?: string
  status_code?: number
  created_at?: string
}

export default function Auditing() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const r = await api.get('/api/v1/auditing/logs?limit=10')
        const data = r.data?.data ?? r.data
        setLogs(Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [])
      } catch (e: any) {
        setError(e?.message || 'Falha ao carregar logs de auditoria')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div>
      <h2>Auditoria</h2>
      {loading && <div>Carregando...</div>}
      {error && <div style={{ color: 'crimson' }}>{error}</div>}
      {!loading && !error && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: 8 }}>Ação</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: 8 }}>Método</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: 8 }}>Path</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: 8 }}>Status</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: 8 }}>Quando</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l, i) => (
              <tr key={i}>
                <td style={{ padding: 8 }}>{l.action || '-'}</td>
                <td style={{ padding: 8 }}>{l.method || '-'}</td>
                <td style={{ padding: 8 }}>{l.path || '-'}</td>
                <td style={{ padding: 8 }}>{l.status_code ?? '-'}</td>
                <td style={{ padding: 8 }}>{l.created_at || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
