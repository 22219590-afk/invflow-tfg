import { useState, useEffect, useMemo } from 'react'
import { Play } from 'lucide-react'
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts'
import { apiFetch } from '../core/api'
import { Product } from '../core/types'

export default function SimulationModule({ token }: { token: string }) {
  const [products, setProducts] = useState<Product[]>([])
  const [selectedId, setSelectedId] = useState<number | ''>('')
  const [demandDelta, setDemandDelta] = useState(0)
  const [leadTimeDelta, setLeadTimeDelta] = useState(0)
  const [executed, setExecuted] = useState(false)

  useEffect(() => {
    apiFetch('/products', token).then(setProducts).catch(console.error)
  }, [token])

  const selectedProduct = products.find(p => p.id === Number(selectedId))

  const simData = useMemo(() => {
    if (!selectedProduct || !executed) return null
    const baseDemand = selectedProduct.daily_demand || 5
    const baseLt = selectedProduct.lead_time_days || 14
    const newDemand = baseDemand * (1 + demandDelta / 100)
    const newLt = baseLt * (1 + leadTimeDelta / 100)
    const newSs = Math.ceil(newDemand * 3 + newLt * newDemand * 0.2)
    const newRop = Math.ceil(newDemand * newLt + newSs)
    const newMax = Math.ceil(newRop + newDemand * 15)
    const newRecQty = newMax - newSs
    const currCoverage = selectedProduct.current_stock / (newDemand || 1)

    const chart = []
    let currentStock = selectedProduct.current_stock || newMax
    let daysToArrival = -1, incomingQty = 0
    for (let day = 0; day <= 60; day++) {
      chart.push({ day, stock: Math.max(0, currentStock), reorder: newRop, safety: newSs })
      if (currentStock <= newRop && daysToArrival === -1) { daysToArrival = Math.round(newLt); incomingQty = newRecQty }
      currentStock -= newDemand
      if (daysToArrival > 0) daysToArrival--
      else if (daysToArrival === 0) { currentStock += incomingQty; daysToArrival = -1; incomingQty = 0 }
    }
    return { newDemand, newLt, newSs, newRop, newMax, newRecQty, currCoverage, chart }
  }, [selectedProduct, demandDelta, leadTimeDelta, executed])

  function handleExecute() {
    if (!selectedProduct) return
    setExecuted(false)
    setTimeout(() => setExecuted(true), 50)
  }

  useEffect(() => { setExecuted(false) }, [selectedId, demandDelta, leadTimeDelta])

  return (
    <div className="animate-in">
      <div className="view-header">
        <div>
          <h2 className="view-title">Simulación</h2>
          <p className="view-subtitle">Proyecta el impacto de cambios en demanda y tiempos de entrega</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleExecute}
          disabled={!selectedProduct}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <Play size={16} /> Ejecutar Simulación
        </button>
      </div>

      <div className="sim-layout" style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 24 }}>
        <div className="sim-panel" style={{ background: 'white', padding: 24, borderRadius: 16, border: '1px solid #e2e8f0' }}>
          <div className="form-group mb-4" style={{ marginBottom: '24px' }}>
            <label className="form-label" style={{ fontWeight: 700 }}>Producto</label>
            <select className="form-input" value={selectedId} onChange={e => setSelectedId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">-- Seleccionar Producto --</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name} ({p.default_code})</option>)}
            </select>
          </div>

          <div className="form-group mb-4" style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span className="form-label" style={{ marginBottom: 0, fontWeight: 700 }}>Cambio en Demanda:</span>
              <span style={{ color: demandDelta > 0 ? '#ef4444' : demandDelta < 0 ? '#10b981' : '#64748b', fontWeight: 'bold' }}>{demandDelta > 0 ? '+' : ''}{demandDelta}%</span>
            </div>
            <input type="range" min="-50" max="100" className="slider" style={{ width: '100%' }} value={demandDelta} onChange={e => setDemandDelta(Number(e.target.value))} />
          </div>

          <div className="form-group mb-6" style={{ marginBottom: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span className="form-label" style={{ marginBottom: 0, fontWeight: 700 }}>Cambio en Lead Time:</span>
              <span style={{ color: leadTimeDelta > 0 ? '#f59e0b' : leadTimeDelta < 0 ? '#10b981' : '#64748b', fontWeight: 'bold' }}>{leadTimeDelta > 0 ? '+' : ''}{leadTimeDelta}%</span>
            </div>
            <input type="range" min="-50" max="100" className="slider" style={{ width: '100%' }} value={leadTimeDelta} onChange={e => setLeadTimeDelta(Number(e.target.value))} />
          </div>

          {selectedProduct && (
            <div style={{ background: '#f8fafc', padding: 20, borderRadius: 12, border: '1px solid #e2e8f0' }}>
              <h4 style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 700, marginBottom: 16 }}>ESTADO BASE</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>STOCK</div>
                  <div style={{ fontWeight: 700 }}>{selectedProduct.current_stock?.toFixed(0)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>DEMANDA/DÍA</div>
                  <div style={{ fontWeight: 700 }}>{selectedProduct.daily_demand?.toFixed(1)}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="sim-results">
          {!simData ? (
            <div style={{ height: '100%', background: 'white', borderRadius: 16, border: '2px dashed #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
              Ajusta los parámetros y pulsa Ejecutar
            </div>
          ) : (
            <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                <div className="detail-stat-card">
                  <div className="stat-label">NUEVA SS</div>
                  <div className="stat-value">{simData.newSs}</div>
                </div>
                <div className="detail-stat-card">
                  <div className="stat-label">NUEVO ROP</div>
                  <div className="stat-value">{simData.newRop}</div>
                </div>
                <div className="detail-stat-card">
                  <div className="stat-label">NUEVO LOTE</div>
                  <div className="stat-value">{simData.newRecQty}</div>
                </div>
                <div className="detail-stat-card">
                  <div className="stat-label">COBERTURA</div>
                  <div className="stat-value">{simData.currCoverage.toFixed(1)} <span style={{fontSize: '0.7rem'}}>días</span></div>
                </div>
              </div>

              <div className="chart-card" style={{ padding: 24 }}>
                <h3 className="chart-title">Proyección de Stock (60 días)</h3>
                <div style={{ height: 350, marginTop: 24 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={simData.chart}>
                      <defs>
                        <linearGradient id="gStock" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="day" label={{ value: 'Días', position: 'insideBottom', offset: -5, fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Area type="stepAfter" dataKey="stock" stroke="#3b82f6" strokeWidth={3} fill="url(#gStock)" name="Stock Proyectado" />
                      <Area type="monotone" dataKey="reorder" stroke="#f59e0b" strokeWidth={1} strokeDasharray="5 5" fill="none" name="Punto Pedido (ROP)" />
                      <Area type="monotone" dataKey="safety" stroke="#ef4444" strokeWidth={1} strokeDasharray="3 3" fill="none" name="Stock Seguridad" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
