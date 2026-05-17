import { useState, useEffect } from 'react'
import { X, Save, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
import { apiFetch } from '../core/api'
import { Product } from '../core/types'

const POLICY_OPTIONS = [
  { value: 'A', label: 'A — Revisión Continua (s,Q)', desc: 'Pedido automático cuando stock ≤ Stock Mínimo (ROP). Para artículos críticos de alta rotación.' },
  { value: 'B', label: 'B — Revisión Periódica (T,S)', desc: 'Revisión cada T días. Reponer hasta stock máximo objetivo S. Para rotación media.' },
  { value: 'C', label: 'C — Bajo Demanda', desc: 'Pedido puntual según necesidad. Para artículos de baja rotación o demanda irregular.' },
]

// Calculated params shown per policy (read-only)
const CALC_FIELDS: Record<string, { key: string; label: string; unit: string }[]> = {
  A: [
    { key: 'eoq',                label: 'Lote Económico (Q*)',     unit: 'uds' },
    { key: 'min_stock',          label: 'Stock Mínimo / ROP (s)',  unit: 'uds' },
    { key: 'target_stock_level', label: 'Stock Máximo (s+Q)',      unit: 'uds' },
    { key: 'safety_stock',       label: 'Stock Seguridad (SS)',    unit: 'uds' },
    { key: 'num_orders_year',    label: 'Nº Pedidos / Año',        unit: '' },
    { key: 'cost_order',         label: 'Coste Pedido (Cp)',       unit: '€' },
    { key: 'cost_holding',       label: 'Coste Almacén (Ca)',      unit: '€' },
    { key: 'cost_total',         label: 'Coste Total (CT)',        unit: '€' },
  ],
  B: [
    { key: 'review_period',      label: 'Periodo de Revisión',     unit: 'días' },
    { key: 'safety_stock',       label: 'Stock de Seguridad',      unit: 'uds' },
    { key: 'target_stock_level', label: 'Stock Máximo',            unit: 'uds' },
    { key: 'min_stock',          label: 'Stock Mínimo',            unit: 'uds' },
    { key: 'recommended_qty',    label: 'Cantidad a Pedir',        unit: 'uds' },
  ],
  C: [
    { key: 'safety_stock',       label: 'Stock Seguridad (SS)',    unit: 'uds' },
    { key: 'cost_order',         label: 'Coste Pedido (Cp)',       unit: '€' },
    { key: 'cost_holding',       label: 'Coste Almacén (Ca)',      unit: '€' },
  ],
}

export default function ProductDetailModal({ product, token, onClose, onSave }: {
  product: Product; token: string; onClose: () => void; onSave: (updated?: any) => void
}) {
  const [policy, setPolicy] = useState(product.stock_policy_override || product.abc_class || 'C')
  const [leadTime, setLeadTime] = useState(String(product.lead_time_days ?? ''))
  const [serviceLevel, setServiceLevel] = useState(String(product.target_service_level || 99))
  const [saving, setSaving] = useState(false)
  const [saveState, setSaveState] = useState<'idle' | 'ok' | 'err'>('idle')
  const [calcProduct, setCalcProduct] = useState<any>(product)
  // Forecast state and fetch removed for modular refactoring

  async function handleSave() {
    setSaving(true)
    setSaveState('idle')
    try {
      // Step 1: Update editable params
      await apiFetch(`/products/${product.id}`, token, {
        method: 'PUT',
        body: JSON.stringify({
          stock_policy_override: policy,
          lead_time_days: leadTime ? Number(leadTime) : undefined,
          target_service_level: serviceLevel ? Number(serviceLevel) : undefined,
        })
      })

      // Step 2: Full recalculate with new policy
      const updated = await apiFetch(
        `/products/${product.id}/update-policy?policy_override=${policy}&target_service_level=${serviceLevel || 95}`,
        token,
        { method: 'POST' }
      )
      setCalcProduct(updated)
      setSaveState('ok')
      setTimeout(() => { setSaveState('idle'); onSave(updated) }, 1400)
    } catch {
      setSaveState('err')
    } finally {
      setSaving(false)
    }
  }

  const sf = (key: string) => {
    const v = (calcProduct as any)[key]
    if (v === null || v === undefined || isNaN(Number(v))) return 0
    return Number(v)
  }

  const fmtVal = (key: string, unit: string) => {
    const n = sf(key)
    if (unit === '€' && n >= 1000) return `${(n / 1000).toFixed(1)}k€`
    if (unit === '€') return `${n.toFixed(2)}€`
    if (Number.isInteger(n)) return `${n}`
    return `${n.toFixed(1)}`
  }

  const calcFields = CALC_FIELDS[policy] || CALC_FIELDS.C

  // Daily demand: read-only, comes from Odoo sync
  const dailyDemand = sf('daily_demand') || sf('manual_daily_demand')

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card animate-in-up"
        style={{ maxWidth: 680, width: '95vw', maxHeight: '92vh', overflowY: 'auto' }}
        onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.63rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
              Plan Diario — Detalle Producto
            </div>
            <div className="modal-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{product.name}</div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: 3 }}>
              {product.default_code}
              <span style={{ marginLeft: 10, fontWeight: 700, color: 'var(--primary)' }}>
                ABC: {product.abc_class || 'SIN_DEFINIR'}
              </span>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: 4 }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* Demand — read-only info */}
          <div style={{ background: '#f0f7ff', borderRadius: 10, padding: '12px 16px', border: '1px solid #bfdbfe', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: '0.63rem', fontWeight: 700, color: '#1e40af', textTransform: 'uppercase' }}>Demanda media / día</div>
              <div style={{ fontWeight: 800, fontSize: '1rem', color: '#1e3a8a' }}>{dailyDemand.toFixed(2)} uds</div>
              <div style={{ fontSize: '0.6rem', color: '#3b82f6', marginTop: 2 }}>Calculado desde histórico de ventas Odoo</div>
            </div>
            <div>
              <div style={{ fontSize: '0.63rem', fontWeight: 700, color: '#1e40af', textTransform: 'uppercase' }}>Stock actual</div>
              <div style={{ fontWeight: 800, fontSize: '1rem', color: '#1e3a8a' }}>{sf('current_stock').toFixed(0)} uds</div>
            </div>
            {sf('incoming_qty') > 0 && (
              <div>
                <div style={{ fontSize: '0.63rem', fontWeight: 700, color: '#c2410c', textTransform: 'uppercase' }}>En tránsito (pend.)</div>
                <div style={{ fontWeight: 800, fontSize: '1rem', color: '#ea580c' }}>+{sf('incoming_qty').toFixed(0)} uds</div>
              </div>
            )}
          </div>

          {/* Policy Selector */}
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Política de Gestión de Stock
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {POLICY_OPTIONS.map(opt => (
                <label key={opt.value} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer',
                  padding: '10px 14px', borderRadius: 8,
                  background: policy === opt.value ? '#eff6ff' : 'white',
                  border: `1.5px solid ${policy === opt.value ? 'var(--primary)' : '#e2e8f0'}`,
                  transition: 'all 0.15s',
                }}>
                  <input type="radio" name="modal-policy" value={opt.value} checked={policy === opt.value}
                    onChange={() => setPolicy(opt.value)} style={{ marginTop: 3, accentColor: 'var(--primary)' }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#0f172a' }}>{opt.label}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: 2 }}>{opt.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Editable Input Params */}
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Parámetros de Cálculo
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>Lead Time proveedor</div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <input type="number" className="form-input" style={{ padding: '8px 10px', fontSize: '0.85rem' }}
                    value={leadTime} onChange={e => setLeadTime(e.target.value)} placeholder="días" min={1} />
                  <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>días</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>Nivel de Servicio</div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <input type="number" className="form-input" style={{ padding: '8px 10px', fontSize: '0.85rem' }}
                    value={serviceLevel} onChange={e => setServiceLevel(e.target.value)} min={50} max={99.9} step={0.5} />
                  <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Calculated Results */}
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Parámetros Calculados — Política {policy}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
              {calcFields
                .filter(f => {
                  // Política A: Todos
                  // Política B: Solo EOQ, T, SS, Recommended
                  // Política C: Solo SS
                  if (policy === 'A') return true;
                  if (policy === 'B') return ['eoq', 'review_period', 'safety_stock', 'recommended_qty', 'target_stock_level'].includes(f.key);
                  if (policy === 'C') return ['safety_stock', 'cost_order', 'cost_holding'].includes(f.key);
                  return false;
                })
                .map(f => (
                <div key={f.key} style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 14px', border: '1px solid #f1f5f9' }}>
                  <div style={{ fontSize: '0.6rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{f.label}</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', marginTop: 3 }}>
                    {fmtVal(f.key, f.unit)}
                    {f.unit && f.unit !== '€' && <span style={{ fontSize: '0.65rem', fontWeight: 400, color: '#94a3b8', marginLeft: 4 }}>{f.unit}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Traceability Panel — AUDIT (For Policy A and B) */}
          {(policy === 'A' || policy === 'B') && (
            <div style={{ background: '#f8fafc', borderRadius: 10, padding: 16, border: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#475569', marginBottom: 10, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 6 }}>
                <RefreshCw size={14} /> Panel de Trazabilidad Industrial (Auditoría {policy})
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px 10px' }}>
                <div>
                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase' }}>Ventas 12 Meses (D)</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{sf('annual_demand').toFixed(0)} <span style={{ fontSize: '0.65rem', fontWeight: 400 }}>uds</span></div>
                </div>
                <div>
                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase' }}>Demanda Diaria (d)</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{sf('daily_demand').toFixed(2)} <span style={{ fontSize: '0.65rem', fontWeight: 400 }}>uds/día</span></div>
                </div>
                <div>
                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase' }}>Días Laborables</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>240 <span style={{ fontSize: '0.65rem', fontWeight: 400 }}>días</span></div>
                </div>
                <div>
                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase' }}>Desv. Típica (σ)</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{sf('demand_std_dev').toFixed(2)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase' }}>Valor Z (Niv. Serv)</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{sf('z_value').toFixed(2)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase' }}>Lead Time (LT)</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{sf('lead_time_days')} <span style={{ fontSize: '0.65rem', fontWeight: 400 }}>días</span></div>
                </div>
              </div>
              <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px dashed #e2e8f0', fontSize: '0.68rem', color: '#64748b', fontStyle: 'italic' }}>
                Fórmulas: [A] SS=Z·σ·√L, MAX=MIN+EOQ | [B] R=√(2Co/V·Ch), SS=Z·σ·√(L+R), S=SS+D(L+R)
              </div>
            </div>
          )}


          {/* Save */}
          {saveState === 'err' && (
            <div style={{ background: '#fef2f2', borderRadius: 8, padding: '10px 14px', fontSize: '0.78rem', color: '#b91c1c', border: '1px solid #fecaca' }}>
              Error al guardar. Verifica conexión con el servidor.
            </div>
          )}
          {saveState === 'ok' && (
            <div style={{ background: '#f0fdf4', borderRadius: 8, padding: '10px 14px', fontSize: '0.78rem', color: '#15803d', border: '1px solid #bbf7d0', display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle size={15} /> Guardado y recalculado correctamente.
            </div>
          )}
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-ghost" style={{ flex: 1 }} onClick={onClose}>Cancelar</button>
            <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleSave} disabled={saving}>
              <Save size={15} />
              {saving ? 'Guardando y recalculando...' : 'Guardar y Recalcular'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
