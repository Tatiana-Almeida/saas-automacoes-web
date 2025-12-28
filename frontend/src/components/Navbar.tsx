import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Navbar() {
  const { user, logout, hasPermission } = useAuth()
  const navigate = useNavigate()

  const onLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav style={{ borderBottom: '1px solid #eee', padding: '12px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Link to="/" style={{ fontWeight: 600, textDecoration: 'none' }}>SaaS</Link>
        {user && (
          <>
            <Link to="/" style={{ textDecoration: 'none' }}>Dashboard</Link>
            {(hasPermission('view_users') || hasPermission('manage_users')) && (
              <Link to="/users" style={{ textDecoration: 'none' }}>Usuários</Link>
            )}
            {hasPermission('audit_list') && (
              <Link to="/auditing" style={{ textDecoration: 'none' }}>Auditoria</Link>
            )}
            {hasPermission('plan_change') && (
              <Link to="/plans" style={{ textDecoration: 'none' }}>Planos</Link>
            )}
          </>
        )}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          {user ? (
            <>
              <span style={{ color: '#555' }}>Olá, {user.username}</span>
              <button onClick={onLogout}>Sair</button>
            </>
          ) : (
            <Link to="/login">Entrar</Link>
          )}
        </div>
      </div>
    </nav>
  )
}
