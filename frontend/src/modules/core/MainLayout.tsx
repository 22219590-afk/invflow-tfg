import React, { useState } from 'react'
import { 
  LayoutDashboard, Package, Zap, Settings, LogOut, ChevronLeft, ChevronRight, 
  Calendar, BarChart3, TrendingUp, Users 
} from 'lucide-react'

function NavItem({ label, icon, active, onClick, collapsed }: {
  label: string; icon: React.ReactNode; active: boolean; onClick: () => void; collapsed?: boolean
}) {
  return (
    <button
      className={`nav-item ${active ? 'active' : ''}`}
      onClick={onClick}
      title={collapsed ? label : undefined}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        {icon}
      </div>
      {!collapsed && <span>{label}</span>}
    </button>
  )
}

export default function MainLayout({ 
  children, 
  activeView, 
  setView, 
  user, 
  onLogout 
}: { 
  children: React.ReactNode; 
  activeView: string; 
  setView: (v: string) => void; 
  user: { username: string, role: string };
  onLogout: () => void;
}) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="app-layout">
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-logo">IV</div>
          {!collapsed && <div className="sidebar-title">InvFlow</div>}
          <button className="collapse-btn" onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-group">
            {!collapsed && <div className="nav-group-label">MÓDULOS</div>}
            <NavItem 
              label="Dashboard" 
              icon={<LayoutDashboard size={20} />} 
              active={activeView === 'dashboard'} 
              onClick={() => setView('dashboard')} 
              collapsed={collapsed}
            />
            <NavItem 
              label="Plan Diario" 
              icon={<Calendar size={20} />} 
              active={activeView === 'plan_diario'} 
              onClick={() => setView('plan_diario')} 
              collapsed={collapsed}
            />
            <NavItem 
              label="Simulación" 
              icon={<Zap size={20} />} 
              active={activeView === 'simulation'} 
              onClick={() => setView('simulation')} 
              collapsed={collapsed}
            />
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="nav-group" style={{ marginBottom: '20px', padding: '0 10px' }}>
            {!collapsed && <div className="nav-group-label">SISTEMA</div>}
            <NavItem 
              label="Usuarios" 
              icon={<Users size={20} />} 
              active={activeView === 'users'} 
              onClick={() => setView('users')} 
              collapsed={collapsed}
            />
            <NavItem 
              label="Configuración" 
              icon={<Settings size={20} />} 
              active={activeView === 'settings'} 
              onClick={() => setView('settings')} 
              collapsed={collapsed}
            />
            <button className={`nav-item logout ${collapsed ? 'collapsed-logout' : ''}`} onClick={onLogout} title="Cerrar Sesión" style={{ border: 'none', background: 'transparent' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <LogOut size={20} />
              </div>
              {!collapsed && <span>Cerrar Sesión</span>}
            </button>
          </div>

          <div className="sidebar-user">
            <div className="user-avatar">{user.username[0].toUpperCase()}</div>
            {!collapsed && (
              <div className="user-info">
                <div className="user-name">{user.username}</div>
                <div className="user-role">{user.role}</div>
              </div>
            )}
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid #f1f5f9' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 500, letterSpacing: '0.025em' }}>
            INVFLOW / <span style={{ color: '#0f172a', fontWeight: 700 }}>{activeView.toUpperCase()}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }}></div>
            SISTEMA OPERATIVO
          </div>
        </header>

        <div className="view-container" style={{ position: 'relative' }}>
          {children}
        </div>
      </main>
    </div>
  )
}
