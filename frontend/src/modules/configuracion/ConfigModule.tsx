import { useState, useEffect } from 'react'
import { Settings, RefreshCw, TrendingUp } from 'lucide-react'
import { apiFetch } from '../core/api'

type ConfigItem = { key: string, value: string, description?: string }

export default function ConfigModule({ token, devMode, setDevMode }: { token: string; devMode: boolean; setDevMode: (v: boolean) => void }) {
  const [configs, setConfigs] = useState<ConfigItem[]>([])
  const [activeTab, setActiveTab] = useState('erp')
  const [status, setStatus] = useState<{ text: string, ok: boolean | null }>({ text: '', ok: null })

  useEffect(() => {
    apiFetch('/config', token).then(setConfigs).catch(console.error)
  }, [token])

  const erpConfigs = configs.filter(c => c.key.startsWith('odoo_'))
  const paramConfigs = configs.filter(c => ['service_level_a', 'service_level_b', 'service_level_c', 'abc_threshold_a', 'abc_threshold_b', 'lead_time_default_days', 'ordering_cost', 'holding_rate', 'review_period_b_days'].includes(c.key))

  const handleUpdate = (key: string, value: string) => {
    setConfigs(prev => prev.map(c => c.key === key ? { ...c, value } : c))
  }

  const applyConfig = async () => {
    try {
      // For simplicity, we update one by one as the current API seems to expect single updates
      // (Based on main.py @app.put("/config"))
      for (const c of configs) {
        await apiFetch('/config', token, {
          method: 'PUT',
          body: JSON.stringify({ key: c.key, value: c.value })
        })
      }
      setStatus({ text: 'Configuración guardada. Reiniciando servicios...', ok: true })
      setTimeout(() => window.location.reload(), 1500)
    } catch (e: any) {
      setStatus({ text: `Error: ${e.message}`, ok: false })
    }
  }

  const renderConfigTable = (items: ConfigItem[]) => (
    <div className="table-wrapper animate-in" style={{ background: 'white', borderRadius: 16, border: '1px solid #e2e8f0' }}>
      <table className="inv-table">
        <thead>
          <tr>
            <th style={{ width: '30%' }}>PARÁMETRO</th>
            <th>VALOR</th>
            <th>DESCRIPCIÓN</th>
          </tr>
        </thead>
        <tbody>
          {items.map(c => (
            <tr key={c.key}>
              <td style={{ fontWeight: 600, fontSize: '0.85rem' }}>{c.key.replace(/_/g, ' ').toUpperCase()}</td>
              <td>
                <input
                  className="form-input"
                  style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                  value={c.value}
                  onChange={e => handleUpdate(c.key, e.target.value)}
                  type={c.key.includes('password') || c.key.includes('api_key') ? 'password' : 'text'}
                />
              </td>
              <td style={{ fontSize: '0.75rem', color: '#64748b' }}>{c.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <div className="animate-in">
      <div className="view-header">
        <div>
          <h2 className="view-title">Configuración</h2>
          <p className="view-subtitle">Ajustes globales del motor de planificación</p>
        </div>
      </div>

      <div className="tabs-header">
        <button className={`tab-btn ${activeTab === 'erp' ? 'active' : ''}`} onClick={() => setActiveTab('erp')}>1. Conexión ERP</button>
        <button className={`tab-btn ${activeTab === 'params' ? 'active' : ''}`} onClick={() => setActiveTab('params')}>2. Parámetros Estándar</button>
      </div>

      {status.text && (
        <div style={{
          background: status.ok ? '#f0fdf4' : '#eff6ff',
          color: status.ok ? '#166534' : '#1e40af',
          padding: '12px 16px', borderRadius: '8px', marginBottom: '20px', fontWeight: 500, fontSize: '0.9rem'
        }}>
          {status.text}
        </div>
      )}

      {activeTab === 'erp' && (
        <div className="animate-in">
          {renderConfigTable(erpConfigs)}
          <div style={{ marginTop: 20, padding: 20, background: 'white', borderRadius: 16, border: '1px solid #e2e8f0' }}>
            <h4 style={{ marginBottom: 12 }}>Estado de la Conexión</h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981' }}></div>
              <span style={{ fontWeight: 600 }}>Odoo Online</span>
              <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto' }} onClick={() => apiFetch('/odoo/test', token).then(r => alert(`Conexión OK: ${r.odoo_version}`))}>Probar Conexión</button>
            </div>
          </div>
        </div>
      )}
      
      {activeTab === 'params' && renderConfigTable(paramConfigs)}

      <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #e2e8f0', paddingTop: 24 }}>
        <div />
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600 }}>
            <input type="checkbox" checked={devMode} onChange={e => setDevMode(e.target.checked)} />
            Modo Desarrollador
          </label>
          <button className="btn btn-primary" onClick={applyConfig}>Guardar Cambios</button>
        </div>
      </div>
    </div>
  )
}
