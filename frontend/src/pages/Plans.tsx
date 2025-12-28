import { useEffect, useState } from 'react'
import { api } from '../services/api'

type ThrottleStatus = Record<string, string>
type DailySummaryItem = { key: string; used: number; limit: number; percent: number }

export default function Plans() {
  const [throttle, setThrottle] = useState<ThrottleStatus>({})
  const [daily, setDaily] = useState<DailySummaryItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const t = await api.get('/api/v1/throttle/status')
        setThrottle((t.data?.data ?? t.data) || {})
      } catch (e: any) {
        setError(e?.message || 'Falha ao carregar status de throttle')
      }
      try {
        const d = await api.get('/api/v1/throttle/daily/summary')
        const arr = (d.data?.data ?? d.data) as any
        const items: DailySummaryItem[] = Array.isArray(arr)
          ? arr
          : Object.entries(arr || {}).map(([key, val]: any) => ({ key, ...(val || {}) }))
        setDaily(items)
      } catch (_) {}
    }
    load()
  }, [])

  return (
    <div>
      <h2>Plano e Limites</h2>
      {error && <div style={{ color: 'crimson' }}>{error}</div>}
      <div style={{ marginTop: 12 }}>
        <h3>Rate Limits (por escopo)</h3>
        <ul>
          {Object.keys(throttle).length === 0 && <li>N/D</li>}
          {Object.entries(throttle).map(([k, v]) => (
            <li key={k}><b>{k}</b>: {String(v)}</li>
          ))}
        </ul>
      </div>
      <div style={{ marginTop: 12 }}>
        <h3>Resumo Diário</h3>
        {daily.length === 0 ? <div>N/D</div> : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: 8 }}>Chave</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: 8 }}>Usado</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: 8 }}>Limite</th>
                <th style={{ textAlign: 'right', borderBottom: '1px solid #eee', padding: 8 }}>%</th>
              </tr>
            </thead>
            <tbody>
              {daily.map((it) => (
                <tr key={it.key}>
                  <td style={{ padding: 8 }}>{it.key}</td>
                  <td style={{ padding: 8, textAlign: 'right' }}>{it.used}</td>
                  <td style={{ padding: 8, textAlign: 'right' }}>{it.limit}</td>
                  <td style={{ padding: 8, textAlign: 'right' }}>{it.percent}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
