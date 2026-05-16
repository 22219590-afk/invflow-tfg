import { useEffect, useState } from 'react'
import { X, Package, RefreshCw, AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react'
import { apiFetch } from '../core/api'
import { Product } from '../core/types'

// ─── Types ────────────────────────────────────────────────────────────────────

type ComponentLine = {
  child_id: number
  child_odoo_id: number
  name: string
  default_code: string | null
  bom_qty: number
  current_stock: number
  daily_need: number
  parent_daily_demand: number
  lead_time_need: number
  repl_needed: number
  abc_class: string
  status: 'OK' | 'Reorder' | 'Stockout'
}

type ComponentsData = {
  has_components: boolean
  parent_id: number
  parent_name: string
  parent_daily_demand: number
  components: ComponentLine[]
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { bg: string; color: string; border: string; label: string; Icon: any }> = {
  OK: {
    bg: '#f0fdf4', color: '#15803d', border: '#bbf7d0',
    label: 'Cubierto', Icon: CheckCircle,
  },
  Reorder: {
    bg: '#fff7ed', color: '#c2410c', border: '#fed7aa',
    label: 'Reposición', Icon: AlertTriangle,
  },
  Stockout: {
    bg: '#fef2f2', color: '#b91c1c', border: '#fecaca',
    label: 'Sin Stock', Icon: AlertCircle,
  },
}

const ABC_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  A: { bg: '#eff6ff', color: '#1e40af', border: '#bfdbfe' },
  B: { bg: '#f0fdf4', color: '#166534', border: '#bbf7d0' },
  C: { bg: '#f8fafc', color: '#475569', border: '#e2e8f0' },
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ComponentsModal({
  product,
  token,
  onClose,
}: {
  product: Product
  token: string
  onClose: () => void
}) {
  const [data, setData] = useState<ComponentsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    apiFetch(`/products/${product.id}/components`, token)
      .then((d: ComponentsData) => {
        setData(d)
        setLoading(false)
      })
      .catch((e: Error) => {
        setError(e.message || 'Error al cargar componentes')
        setLoading(false)
      })
  }, [product.id, token])

  // ── Trap ESC key ──────────────────────────────────────────────────────────
  useEffect(() => {
    const handle = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handle)
    return () => document.removeEventListener('keydown', handle)
  }, [onClose])

  const fmt = (v: number, dec = 2) => Number(v ?? 0).toFixed(dec)

  return (
    <div
      id="components-modal-backdrop"
      style={{
        position: 'fixed', inset: 0, zIndex: 600,
        background: 'rgba(15, 23, 42, 0.55)',
        backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px',
        animation: 'fadeIn 0.15s ease',
      }}
      onClick={e => { if ((e.target as HTMLElement).id === 'components-modal-backdrop') onClose() }}
    >
      <div style={{
        background: 'white',
        borderRadius: 16,
        boxShadow: '0 24px 80px rgba(0,0,0,0.22)',
        width: '100%',
        maxWidth: 860,
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        animation: 'slideUp 0.2s cubic-bezier(0.22, 1, 0.36, 1)',
      }}>

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div style={{
          padding: '20px 24px 16px',
          borderBottom: '1px solid #f1f5f9',
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
          background: 'linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40, height: 40,
              background: 'linear-gradient(135deg, var(--primary) 0%, #6366f1 100%)',
              borderRadius: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Package size={18} color="white" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontWeight: 800, fontSize: '1rem', color: '#0f172a' }}>
                Componentes del Producto
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: '#64748b' }}>
                {product.name}
                {product.default_code && (
                  <span style={{ marginLeft: 8, fontWeight: 600, color: '#94a3b8' }}>
                    [{product.default_code}]
                  </span>
                )}
              </p>
            </div>
          </div>
          <button
            id="components-modal-close"
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#94a3b8', padding: 4, borderRadius: 6,
              display: 'flex', alignItems: 'center',
              transition: 'color 0.15s',
            }}
            title="Cerrar (ESC)"
          >
            <X size={20} />
          </button>
        </div>

        {/* ── Context strip: parent demand ───────────────────────────────── */}
        {data?.has_components && (
          <div style={{
            padding: '10px 24px',
            background: '#f8fafc',
            borderBottom: '1px solid #f1f5f9',
            display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap',
          }}>
            <div style={{ fontSize: '0.74rem', color: '#64748b' }}>
              <span style={{ fontWeight: 700, color: '#0f172a' }}>Demanda diaria del producto final: </span>
              <span style={{
                background: '#eff6ff', color: '#1e40af',
                border: '1px solid #bfdbfe', borderRadius: 6,
                padding: '2px 8px', fontWeight: 700, fontSize: '0.75rem', marginLeft: 6,
              }}>
                {fmt(data.parent_daily_demand, 4)} uds/día
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', fontStyle: 'italic' }}>
              Las necesidades de cada componente se derivan proporcionalmente de esta demanda existente (sin recálculo).
            </div>
          </div>
        )}

        {/* ── Body ────────────────────────────────────────────────────────── */}
        <div style={{ overflowY: 'auto', flex: 1, padding: '16px 24px 24px' }}>

          {/* Loading */}
          {loading && (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#94a3b8' }}>
              <RefreshCw size={24} className="rotate-slow" style={{ margin: '0 auto 12px', display: 'block' }} />
              <p style={{ margin: 0, fontSize: '0.85rem' }}>Cargando componentes...</p>
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div style={{
              background: '#fef2f2', border: '1px solid #fecaca',
              borderRadius: 10, padding: '20px 24px', color: '#b91c1c',
              fontSize: '0.85rem', textAlign: 'center',
            }}>
              <AlertCircle size={20} style={{ margin: '0 auto 8px', display: 'block' }} />
              {error}
            </div>
          )}

          {/* No BOM */}
          {!loading && !error && data && !data.has_components && (
            <div style={{
              textAlign: 'center', padding: '60px 0', color: '#94a3b8',
            }}>
              <Package size={32} style={{ margin: '0 auto 12px', display: 'block', opacity: 0.4 }} />
              <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: '#64748b' }}>
                Este producto no tiene estructura de materiales (BOM)
              </p>
              <p style={{ margin: '6px 0 0', fontSize: '0.78rem' }}>
                Se vende directamente sin componentes asociados.
              </p>
            </div>
          )}

          {/* Components table */}
          {!loading && !error && data?.has_components && data.components.length > 0 && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{
                width: '100%', borderCollapse: 'separate', borderSpacing: 0,
                fontSize: '0.8rem',
              }}>
                <thead>
                  <tr style={{ background: '#f8fafc' }}>
                    {[
                      { label: 'COMPONENTE', align: 'left' },
                      { label: 'ABC', align: 'center' },
                      { label: 'CANT. BOM', align: 'center', title: 'Unidades del componente por cada unidad del producto final' },
                      { label: 'STOCK ACT.', align: 'center' },
                      { label: 'NECESIDAD DIARIA', align: 'center', title: 'Demanda padre × cantidad BOM' },
                      { label: 'NECESIDAD LT', align: 'center', title: 'Necesidad para cubrir el lead time del producto final' },
                      { label: 'A REPONER', align: 'center', title: 'Unidades que faltan para cubrir la necesidad en lead time' },
                      { label: 'ESTADO', align: 'center' },
                    ].map(col => (
                      <th key={col.label} title={col.title} style={{
                        textAlign: col.align as any,
                        padding: '8px 12px',
                        fontWeight: 700,
                        fontSize: '0.67rem',
                        color: '#64748b',
                        letterSpacing: '0.03em',
                        borderBottom: '2px solid #e2e8f0',
                        whiteSpace: 'nowrap',
                        cursor: col.title ? 'help' : 'default',
                      }}>
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.components.map((comp, idx) => {
                    const st = STATUS_CONFIG[comp.status] || STATUS_CONFIG.OK
                    const abcS = ABC_STYLE[comp.abc_class] || ABC_STYLE.C
                    const isLast = idx === data.components.length - 1

                    return (
                      <tr
                        key={comp.child_odoo_id}
                        style={{
                          background: idx % 2 === 0 ? 'white' : '#fafbff',
                          transition: 'background 0.1s',
                        }}
                      >
                        {/* Componente name */}
                        <td style={{ padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9' }}>
                          <div style={{ fontWeight: 600, fontSize: '0.83rem', color: '#0f172a' }}>
                            {comp.name}
                          </div>
                          {comp.default_code && (
                            <div style={{ fontSize: '0.63rem', color: '#94a3b8', marginTop: 1 }}>
                              {comp.default_code}
                            </div>
                          )}
                        </td>

                        {/* ABC */}
                        <td style={{ textAlign: 'center', padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9' }}>
                          <span style={{
                            background: abcS.bg, color: abcS.color, border: `1px solid ${abcS.border}`,
                            padding: '2px 8px', borderRadius: 5, fontSize: '0.68rem', fontWeight: 700,
                          }}>
                            {comp.abc_class}
                          </span>
                        </td>

                        {/* BOM qty */}
                        <td style={{ textAlign: 'center', padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9', fontWeight: 700, color: 'var(--primary)' }}>
                          ×{comp.bom_qty % 1 === 0 ? comp.bom_qty.toFixed(0) : comp.bom_qty}
                          <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 400, marginTop: 1 }}>uds/padre</div>
                        </td>

                        {/* Current stock */}
                        <td style={{ textAlign: 'center', padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9', fontWeight: 700 }}>
                          {fmt(comp.current_stock, 0)}
                          <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 400 }}>uds</div>
                        </td>

                        {/* Daily need (propagated) */}
                        <td style={{ textAlign: 'center', padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9' }}>
                          <div style={{ fontWeight: 600, color: '#4f46e5', fontSize: '0.82rem' }}>
                            {fmt(comp.daily_need, 3)}
                          </div>
                          <div style={{ fontSize: '0.6rem', color: '#94a3b8' }}>uds/día</div>
                          <div style={{ fontSize: '0.58rem', color: '#cbd5e1', marginTop: 1 }}>
                            ({fmt(comp.parent_daily_demand, 3)} × {comp.bom_qty})
                          </div>
                        </td>

                        {/* Lead time need */}
                        <td style={{ textAlign: 'center', padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9', color: '#334155' }}>
                          {fmt(comp.lead_time_need, 0)}
                          <div style={{ fontSize: '0.6rem', color: '#94a3b8' }}>uds (LT)</div>
                        </td>

                        {/* Repl needed */}
                        <td style={{ textAlign: 'center', padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9' }}>
                          {comp.repl_needed > 0 ? (
                            <span style={{ fontWeight: 700, color: '#ef4444', fontSize: '0.85rem' }}>
                              +{fmt(comp.repl_needed, 0)}
                            </span>
                          ) : (
                            <span style={{ color: '#22c55e', fontWeight: 700, fontSize: '0.85rem' }}>✓</span>
                          )}
                        </td>

                        {/* Status */}
                        <td style={{ textAlign: 'center', padding: '10px 12px', borderBottom: isLast ? 'none' : '1px solid #f1f5f9' }}>
                          <span style={{
                            background: st.bg, color: st.color, border: `1px solid ${st.border}`,
                            padding: '3px 10px', borderRadius: 20, fontSize: '0.65rem', fontWeight: 700,
                            display: 'inline-flex', alignItems: 'center', gap: 4,
                          }}>
                            <st.Icon size={10} />
                            {st.label}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              {/* Legend */}
              <div style={{
                marginTop: 16, padding: '10px 14px',
                background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0',
                fontSize: '0.7rem', color: '#64748b',
                display: 'flex', gap: 20, flexWrap: 'wrap',
              }}>
                <span><strong>Cant. BOM:</strong> unidades del componente por cada unidad de producto final</span>
                <span><strong>Necesidad diaria:</strong> demanda padre × Cant. BOM (propagación de demanda)</span>
                <span><strong>Necesidad LT:</strong> cobertura mínima durante el lead time del padre</span>
                <span><strong>A reponer:</strong> gap entre stock actual y necesidad en lead time</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
