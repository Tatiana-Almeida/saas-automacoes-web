import { useAuth } from '../hooks/useAuth'
import { api } from '../services/api'
import { useEffect, useState } from 'react'

export default function Dashboard() {
  const { user, permissions, hasPermission } = useAuth()
  const [me, setMe] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const r = await api.get('/api/v1/users/me')
        setMe(r.data?.data ?? r.data)
      } catch (e: any) {
        setError(e?.message || 'Falha ao carregar dados')
      }
    }
    load()
  }, [])
  return (
    <div>
      <h2>Dashboard</h2>
      <p>Bem-vindo ao painel. {user ? `Usuário: ${user.username}` : ''}</p>
      {error && <div style={{ color: 'crimson' }}>{error}</div>}
      {me && (
        <div style={{ margin: '12px 0' }}>
          <div><b>email:</b> {me.email || '-'}</div>
          <div><b>staff:</b> {me.is_staff ? 'sim' : 'não'}</div>
        </div>
      )}
      <div style={{ marginTop: 16 }}>
        <h3>Permissões</h3>
        {permissions.length === 0 ? <div>Sem permissões específicas.</div> : (
          <ul>
            {permissions.map((p) => <li key={p}>{p}</li>)}
          </ul>
        )}
      </div>
      <div style={{ marginTop: 16 }}>
        <h3>Ações Disponíveis</h3>
        <ul>
          {hasPermission('rbac_change') && <li>Gerir RBAC</li>}
          {hasPermission('plan_change') && <li>Alterar Plano</li>}
          {hasPermission('audit_list') && <li>Ver Auditoria</li>}
        </ul>
      </div>
    </div>
  )
}
