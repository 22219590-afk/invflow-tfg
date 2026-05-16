import { useState, useEffect, useCallback } from 'react'
import MainLayout from './modules/core/MainLayout'
import LoginView from './modules/core/LoginView'
import DashboardModule from './modules/dashboard/DashboardModule'
import InventoryModule from './modules/plan_diario/InventoryModule'
import SimulationModule from './modules/simulacion/SimulationModule'
import ConfigModule from './modules/configuracion/ConfigModule'
import MPSModule from './modules/mps/MPSModule'
import ForecastModule from './modules/forecast/ForecastModule'
import UsersModule from './modules/usuarios/UsersModule'
import { apiFetch } from './modules/core/api'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [role, setRole] = useState(localStorage.getItem('role') || 'viewer')
  const [username, setUsername] = useState(localStorage.getItem('username') || '')
  const [view, setView] = useState('dashboard')
  const [syncing, setSyncing] = useState(false)
  const [devMode, setDevMode] = useState(false)

  // Auth persistence
  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token)
      localStorage.setItem('role', role)
      localStorage.setItem('username', username)
    } else {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('username')
    }
  }, [token, role, username])

  const handleLogin = (t: string, r: string, u: string) => {
    setToken(t)
    setRole(r)
    setUsername(u)
  }

  const handleLogout = () => {
    setToken('')
    setRole('viewer')
    setUsername('')
  }

  const handleSync = useCallback(async () => {
    setSyncing(true)
    try {
      await apiFetch('/sync', token, { method: 'POST' })
      // We could trigger a reload of the current view here if needed
      window.location.reload() 
    } catch (e: any) {
      alert(`Error de sincronización: ${e.message}`)
    } finally {
      setSyncing(false)
    }
  }, [token])

  if (!token) {
    return <LoginView onLogin={handleLogin} />
  }

  const renderView = () => {
    switch (view) {
      case 'dashboard':
        return <DashboardModule token={token} devMode={devMode} setView={setView} />
      case 'plan_diario':
        return <InventoryModule token={token} onSync={handleSync} syncing={syncing} />
      case 'mps':
        return <MPSModule token={token} />
      case 'forecast':
        return <ForecastModule token={token} />
      case 'simulation':
        return <SimulationModule token={token} />
      case 'users':
        return <UsersModule token={token} />
      case 'settings':
        return <ConfigModule token={token} devMode={devMode} setDevMode={setDevMode} />
      default:
        return <DashboardModule token={token} devMode={devMode} setView={setView} />
    }
  }

  return (
    <MainLayout 
      activeView={view} 
      setView={setView} 
      user={{ username, role }} 
      onLogout={handleLogout}
    >
      {renderView()}
    </MainLayout>
  )
}
