import { useState } from 'react'
import { apiFetch } from './api'

export default function LoginView({ onLogin }: { onLogin: (t: string, r: string, u: string) => void }) {
  const [username, setUs] = useState('')
  const [password, setPw] = useState('')
  const [error, setErr] = useState('')

  async function handleSubmit(e: any) {
    e.preventDefault()
    try {
      const d = await apiFetch('/auth/login', '', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username, password })
      })
      onLogin(d.access_token, d.role, username)
    } catch { 
      setErr('Credenciales incorrectas') 
    }
  }

  return (
    <div className="login-container">
      <div className="login-card animate-in-up">
        <div className="sidebar-brand" style={{ justifyContent: 'center', marginBottom: '32px' }}>
          <div className="sidebar-logo">IV</div>
          <div className="sidebar-title">InvFlow</div>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: 16 }}>
            <label className="form-label">Usuario</label>
            <input className="form-input" value={username} onChange={e => setUs(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 24 }}>
            <label className="form-label">Contraseña</label>
            <input className="form-input" type="password" value={password} onChange={e => setPw(e.target.value)} />
          </div>
          {error && <p style={{ color: '#ef4444', marginBottom: 16, fontSize: '0.85rem' }}>{error}</p>}
          <button className="btn btn-primary w-full" type="submit">Entrar al Sistema</button>
        </form>
      </div>
    </div>
  )
}
