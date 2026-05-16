import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  RefreshCw, Package, DollarSign, AlertTriangle, Clock,
  Search, Settings, ShoppingBag, ArrowUpDown, ChevronDown, ChevronUp, Layers
} from 'lucide-react'
import { apiFetch } from '../core/api'
import { Product } from '../core/types'
import ProductDetailModal from './ProductDetailModal'
import OrderModal from './OrderModal'
import ComponentsModal from './ComponentsModal'

type SortConfig = { key: string; dir: 'asc' | 'desc' }
type ActiveFilter = 'ALL' | 'A' | 'B' | 'C' | 'Reorder' | 'Stockout' | 'Overstock'

const POLICY_LABEL: Record<string, string> = {
  A: 'Revisión Continua',
  B: 'Revisión Periódica',
  C: 'Bajo Demanda',
}

const ABC_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  A: { bg: '#eff6ff', color: '#1e40af', border: '#bfdbfe' },
  B: { bg: '#f0fdf4', color: '#166534', border: '#bbf7d0' },
  C: { bg: '#f8fafc', color: '#475569', border: '#e2e8f0' },
}

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  OK:        { bg: '#f0fdf4', color: '#15803d', label: 'OK' },
  Reorder:   { bg: '#fff7ed', color: '#c2410c', label: 'Reorden' },
  Stockout:  { bg: '#fef2f2', color: '#b91c1c', label: 'Rotura' },
  Overstock: { bg: '#eff6ff', color: '#1d4ed8', label: 'Sobrestock' },
}

const QUICK_FILTERS: { key: ActiveFilter; label: string }[] = [
  { key: 'ALL', label: 'Todos' },
  { key: 'A',   label: 'Clase A' },
  { key: 'B',   label: 'Clase B' },
  { key: 'C',   label: 'Clase C' },
  { key: 'Reorder',   label: '⚠ Reorden' },
  { key: 'Stockout',  label: '🔴 Rotura' },
  { key: 'Overstock', label: '🔵 Sobrestock' },
]

function ColHeader({ col, label, center, sortConfig, setSortConfig, colFilters, setColFilters, openFilterCol, setOpenFilterCol }: any) {
  const isSort = sortConfig?.key === col
  const hasFilter = !!colFilters[col]?.trim()
  const isOpen = openFilterCol === col

  return (
    <th style={{ position: 'relative', whiteSpace: 'nowrap', textAlign: center ? 'center' : 'left' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 3, justifyContent: center ? 'center' : 'flex-start' }}>
        <button
          onClick={() => setSortConfig((p: any) => p?.key === col ? (p.dir === 'asc' ? { key: col, dir: 'desc' } : null) : { key: col, dir: 'asc' })}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '0.72rem', color: isSort ? 'var(--primary)' : 'inherit', display: 'flex', alignItems: 'center', gap: 3, padding: 0 }}>
          {label}
          <ArrowUpDown size={10} style={{ opacity: isSort ? 1 : 0.3 }} />
        </button>
        <button onClick={e => { e.stopPropagation(); setOpenFilterCol(isOpen ? null : col) }}
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '1px', color: hasFilter ? 'var(--primary)' : '#cbd5e1', display: 'flex' }}>
          {isOpen ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
        </button>
      </div>
      {isOpen && (
        <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, zIndex: 300, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: 12, minWidth: 180, boxShadow: '0 8px 24px rgba(0,0,0,0.1)' }}>
          <div style={{ fontSize: '0.68rem', color: '#64748b', fontWeight: 700, marginBottom: 6 }}>Filtrar por {label}</div>
          <input className="form-input" style={{ padding: '6px 10px', fontSize: '0.8rem' }} placeholder="Buscar..."
            value={colFilters[col] || ''} onChange={e => setColFilters((p: any) => ({ ...p, [col]: e.target.value }))} autoFocus />
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button onClick={() => { setSortConfig({ key: col, dir: 'asc' }); setOpenFilterCol(null) }} style={{ flex: 1, fontSize: '0.7rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 5, padding: '4px', cursor: 'pointer' }}>↑ Asc</button>
            <button onClick={() => { setSortConfig({ key: col, dir: 'desc' }); setOpenFilterCol(null) }} style={{ flex: 1, fontSize: '0.7rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 5, padding: '4px', cursor: 'pointer' }}>↓ Desc</button>
            {hasFilter && <button onClick={() => setColFilters((p: any) => ({ ...p, [col]: '' }))} style={{ fontSize: '0.7rem', background: '#fef2f2', color: '#ef4444', border: '1px solid #fecaca', borderRadius: 5, padding: '4px 8px', cursor: 'pointer' }}>✕</button>}
          </div>
        </div>
      )}
    </th>
  )
}

export default function InventoryModule({ token, onSync, syncing }: { token: string; onSync: () => void; syncing: boolean }) {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [kpis, setKpis] = useState<any>(null)
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(null)
  const [colFilters, setColFilters] = useState<Record<string, string>>({})
  const [openFilterCol, setOpenFilterCol] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>('ALL')
  const [viewingProduct, setViewingProduct] = useState<Product | null>(null)
  const [orderingProduct, setOrderingProduct] = useState<Product | null>(null)
  const [viewingComponents, setViewingComponents] = useState<Product | null>(null)
  const [recalculating, setRecalculating] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    return Promise.all([
      apiFetch('/products', token),
      apiFetch('/kpis?period_days=30', token),
    ]).then(([prods, k]) => {
      setProducts(prods)
      setKpis(k)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [token])

  useEffect(() => { load() }, [load])

  const handleRecalculate = useCallback(async () => {
    setRecalculating(true)
    try {
      await apiFetch('/recalculate', token, { method: 'POST' })
      await load()
    } catch (e) {
      console.error('[Plan Diario] Recalculate failed', e)
    } finally {
      setRecalculating(false)
    }
  }, [token, load])

  useEffect(() => {
    if (!openFilterCol) return
    const h = () => setOpenFilterCol(null)
    setTimeout(() => document.addEventListener('click', h), 0)
    return () => document.removeEventListener('click', h)
  }, [openFilterCol])

  /**
   * Called when ProductDetailModal saves.
   * - Immediately patches the updated product in state (no flicker, no reload needed)
   * - Then fires a background reload to sync KPIs
   * This makes policy changes reactive WITHOUT reloading the app.
   */
  const handleProductSaved = useCallback((updated?: any) => {
    setViewingProduct(null)
    if (updated && updated.id) {
      console.log(`[Plan Diario] Política guardada para ${updated.name}: Override=${updated.stock_policy_override}, ABC=${updated.abc_class}`)
      console.log(`[Plan Diario] Nuevos valores: EOQ=${updated.eoq}, MIN=${updated.min_stock}, MAX=${updated.max_stock}, SS=${updated.safety_stock}, T=${updated.review_period}`)
      // 1. Patch this product in-place immediately for instant UI update
      setProducts(prev => prev.map(p => p.id === updated.id ? { ...p, ...updated } : p))
      // 2. Background refresh for KPIs and full product list consistency
      Promise.all([
        apiFetch('/products', token),
        apiFetch('/kpis?period_days=30', token),
      ]).then(([prods, k]) => {
        setProducts(prods)
        setKpis(k)
      }).catch(() => {})
    } else {
      load()
    }
  }, [token, load])

  const filteredSorted = useMemo(() => {
    let data = [...products]

    if (activeFilter !== 'ALL') {
      if (['A', 'B', 'C'].includes(activeFilter)) {
        // Filter by EFFECTIVE policy (override takes precedence over abc_class)
        data = data.filter(p => (p.stock_policy_override || p.abc_class || 'C') === activeFilter)
      } else {
        data = data.filter(p => p.status === activeFilter)
      }
    }

    if (searchQuery.trim()) {
      const sq = searchQuery.toLowerCase()
      data = data.filter(p => p.name.toLowerCase().includes(sq) || (p.default_code || '').toLowerCase().includes(sq))
    }

    for (const [key, val] of Object.entries(colFilters)) {
      if (!val.trim()) continue
      data = data.filter(p => String((p as any)[key] ?? '').toLowerCase().includes(val.toLowerCase()))
    }

    if (sortConfig) {
      data.sort((a, b) => {
        const av = (a as any)[sortConfig.key], bv = (b as any)[sortConfig.key]
        if (av == null) return 1; if (bv == null) return -1
        const cmp = typeof av === 'number' ? av - bv : String(av).localeCompare(String(bv))
        return sortConfig.dir === 'asc' ? cmp : -cmp
      })
    }
    return data
  }, [products, colFilters, sortConfig, searchQuery, activeFilter])

  const sf = (v: any) => (v === null || v === undefined || isNaN(Number(v))) ? 0 : Number(v)
  const fmt = (v: any, dec = 0) => sf(v).toFixed(dec)
  const fmtCurr = (v: any) => { const n = sf(v); if (n >= 1000000) return `${(n/1000000).toFixed(2)}M€`; if (n >= 1000) return `${(n/1000).toFixed(1)}k€`; return `${n.toFixed(0)}€` }

  const criticalCount = products.filter(p => p.status === 'Reorder' || p.status === 'Stockout').length
  const totalPending = products.reduce((acc, p) => acc + sf(p.incoming_qty), 0)

  const colProps = { sortConfig, setSortConfig, colFilters, setColFilters, openFilterCol, setOpenFilterCol }

  return (
    <div className="animate-in">
      {/* Header */}
      <div className="view-header">
        <div>
          <h2 className="view-title">Plan Diario</h2>
          <p className="view-subtitle">Gestión de aprovisionamiento y control de stock operativo</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-ghost" onClick={handleRecalculate} disabled={recalculating}
            title="Recalcular clasificación ABC y parámetros sin sincronizar con Odoo">
            <RefreshCw size={14} className={recalculating ? 'rotate-slow' : ''} />
            {recalculating ? 'Recalculando...' : 'Recalcular'}
          </button>
          <button className={`btn ${syncing ? 'btn-ghost' : 'btn-primary'}`} onClick={onSync} disabled={syncing}>
            <RefreshCw size={15} className={syncing ? 'rotate-slow' : ''} />
            {syncing ? 'Sincronizando...' : 'Sincronizar Odoo'}
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="inventory-stats" style={{ marginBottom: 24 }}>
        {[
          { label: 'TOTAL REFS.', value: products.length, icon: Package },
          { label: 'VALOR INVENTARIO', value: fmtCurr(kpis?.total_value), icon: DollarSign },
          { label: 'ALERTAS CRÍTICAS', value: criticalCount, icon: AlertTriangle },
          { label: 'EN TRÁNSITO', value: `${totalPending.toFixed(0)} uds`, icon: Clock },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="inv-kpi" style={{ borderLeftColor: 'var(--primary)', padding: '16px 20px' }}>
            <div>
              <div className="inv-kpi-label">{label}</div>
              <div className="inv-kpi-value" style={{ fontSize: '1.1rem' }}>{value}</div>
            </div>
            <div style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f7ff', borderRadius: 8, color: 'var(--primary)', flexShrink: 0 }}>
              <Icon size={16} />
            </div>
          </div>
        ))}
      </div>

      {/* Quick Filters + Search */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {QUICK_FILTERS.map(f => (
            <button key={f.key} onClick={() => setActiveFilter(f.key)} style={{
              padding: '6px 14px', borderRadius: 20, fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
              border: `1.5px solid ${activeFilter === f.key ? 'var(--primary)' : '#e2e8f0'}`,
              background: activeFilter === f.key ? 'var(--primary)' : 'white',
              color: activeFilter === f.key ? 'white' : '#64748b',
              transition: 'all 0.15s',
            }}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="search-box" style={{ flex: 1, maxWidth: 300 }}>
          <Search className="search-icon" size={14} />
          <input className="search-input" placeholder="Buscar producto o referencia..."
            value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
        </div>
        <span style={{ fontSize: '0.78rem', color: '#94a3b8', whiteSpace: 'nowrap' }}>{filteredSorted.length} artículos</span>
      </div>

      {/* Table */}
      <div className="table-wrapper">
        <table className="inv-table">
          <thead>
            <tr>
              <ColHeader col="name" label="PRODUCTO" {...colProps} />
              <th style={{ textAlign: 'center' }}>ABC</th>
              <th style={{ textAlign: 'center' }}>POLÍTICA</th>
              <ColHeader col="current_stock" label="STOCK ACT." center {...colProps} />
              <ColHeader col="eoq" label="LOTE ECON." center {...colProps} />
              <ColHeader col="min_stock" label="STOCK MÍN." center {...colProps} />
              <th style={{ textAlign: 'center' }}>STOCK MÁX.</th>
              <ColHeader col="safety_stock" label="STOCK SEG." center {...colProps} />
              <th style={{ textAlign: 'center' }}>DEMANDA</th>
              <th style={{ textAlign: 'center' }}>LEAD TIME</th>
              <th style={{ textAlign: 'center' }}>T REVISIÓN</th>
              <th style={{ textAlign: 'center' }}>ESTADO</th>
              <th style={{ textAlign: 'center' }}>COMPONENTES</th>
              <th style={{ textAlign: 'right' }}>ACCIONES</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={14} style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}>
                <RefreshCw size={20} className="rotate-slow" style={{ margin: '0 auto 8px', display: 'block' }} />
                Cargando datos...
              </td></tr>
            ) : filteredSorted.length === 0 ? (
              <tr><td colSpan={14} style={{ textAlign: 'center', padding: 60, color: '#94a3b8', fontSize: '0.85rem' }}>
                Sin resultados. Sincroniza con Odoo para cargar productos.
              </td></tr>
            ) : filteredSorted.map(p => {
              const status = p.status || 'OK'
              const statusStyle = STATUS_STYLE[status] || STATUS_STYLE.OK

              // ─── POLÍTICA EFECTIVA ───────────────────────────────────────────
              // stock_policy_override tiene prioridad absoluta sobre abc_class.
              // Si no hay override, se usa la clase ABC del motor de clasificación.
              const policy: string = p.stock_policy_override || p.abc_class || 'C'
              const abcStyle = ABC_STYLE[policy] || ABC_STYLE.C

              // ─── STOCK EN TRÁNSITO ───────────────────────────────────────────
              // incoming_qty > 0  →  pedido confirmado pendiente de recepción
              // incoming_qty = 0  →  pedido ya validado/recibido; stock real actualizado
              const pending = sf(p.incoming_qty)
              const lt = sf(p.lead_time_days)

              // ─── VISIBILIDAD DE COLUMNAS POR POLÍTICA ───────────────────────
              // POLÍTICA A — Revisión Continua (s,Q):
              //   Mostrar: EOQ, Stock Mín (ROP), Stock Máx, Stock Seg, Lead Time
              //   Ocultar: T Revisión
              //
              // POLÍTICA B — Revisión Periódica (T,S):
              //   Mostrar: EOQ, Stock Seg, T Revisión
              //   Ocultar: Stock Mín, Stock Máx
              //
              // POLÍTICA C — Bajo Demanda:
              //   Mostrar: datos básicos + Stock Seg (si calculado)
              //   Ocultar: EOQ, Stock Mín, Stock Máx, T Revisión
              const showEOQ = policy === 'A' || policy === 'B'
              const showMin = policy === 'A' || policy === 'B'  // B usa min_stock como SS/ROP
              const showMax = policy === 'A' || policy === 'B'  // B usa max_stock como stock objetivo (S)
              const showSS  = true   // Stock Seguridad siempre visible (base de cualquier política)
              const showT   = policy === 'B'

              const isOverridden = !!p.stock_policy_override && p.stock_policy_override !== p.abc_class

              return (
                <tr key={p.id}>
                  {/* PRODUCTO */}
                  <td>
                    <div style={{ fontWeight: 600, fontSize: '0.83rem', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 6 }}>
                      {p.name}
                    </div>
                    <div style={{ fontSize: '0.63rem', color: '#94a3b8', marginTop: 1 }}>{p.default_code}</div>
                  </td>

                  {/* ABC — clase del motor de clasificación (coloreado por política efectiva) */}
                  <td style={{ textAlign: 'center' }}>
                    <span style={{ background: abcStyle.bg, color: abcStyle.color, border: `1px solid ${abcStyle.border}`, padding: '3px 9px', borderRadius: 6, fontSize: '0.72rem', fontWeight: 700 }}>
                      {p.abc_class || '—'}
                    </span>
                  </td>

                  {/* POLÍTICA efectiva */}
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: isOverridden ? '#f97316' : 'var(--primary)' }}>{policy}</div>
                    <div style={{ fontSize: '0.6rem', color: '#94a3b8', marginTop: 1 }}>{POLICY_LABEL[policy] || '—'}</div>
                    {isOverridden && (
                      <div style={{ fontSize: '0.55rem', color: '#f97316', marginTop: 1 }}>override manual</div>
                    )}
                  </td>

                  {/* STOCK ACTUAL — con indicador tránsito */}
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ fontWeight: 700 }}>{fmt(p.current_stock)}</div>
                    {pending > 0 && (
                      <div
                        title={`Pendiente de recepción en Odoo: ${pending.toFixed(0)} uds. Una vez validado, este importe pasará al stock real.`}
                        style={{ fontSize: '0.62rem', color: '#f97316', fontWeight: 700, cursor: 'help', marginTop: 2 }}>
                        +{pending.toFixed(0)} ⏳
                      </div>
                    )}
                  </td>

                  {/* LOTE ECONÓMICO (EOQ) — A y B */}
                  <td style={{ textAlign: 'center', color: 'var(--primary)', fontWeight: 600 }}>
                    {showEOQ ? fmt(p.eoq) : '—'}
                  </td>

                  {/* STOCK MÍNIMO / ROP — solo A */}
                  <td style={{ textAlign: 'center' }}>
                    {showMin ? fmt(p.min_stock) : '—'}
                  </td>

                  {/* STOCK MÁXIMO — solo A */}
                  <td style={{ textAlign: 'center' }}>
                    {showMax ? fmt(p.max_stock) : '—'}
                  </td>

                  {/* STOCK SEGURIDAD — siempre */}
                  <td style={{ textAlign: 'center', fontSize: '0.82rem' }}>
                    {showSS ? fmt(p.safety_stock, 1) : '—'}
                  </td>

                  {/* DEMANDA DIARIA */}
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ fontWeight: 600, color: 'var(--primary)', fontSize: '0.85rem' }}>
                      {sf(p.daily_demand).toFixed(2)}
                    </div>
                    <div style={{ fontSize: '0.6rem', color: '#94a3b8' }}>uds/día</div>
                  </td>

                  {/* LEAD TIME */}
                  <td style={{ textAlign: 'center', fontSize: '0.82rem', color: '#64748b' }}>
                    {lt > 0 ? `${lt}d` : '—'}
                  </td>

                  {/* T REVISIÓN — solo B */}
                  <td style={{ textAlign: 'center', fontSize: '0.82rem', color: '#64748b' }}>
                    {showT ? (sf(p.review_period) > 0 ? `${sf(p.review_period)}d` : '—') : '—'}
                  </td>

                  {/* ESTADO */}
                  <td style={{ textAlign: 'center' }}>
                    <span style={{ background: statusStyle.bg, color: statusStyle.color, padding: '3px 10px', borderRadius: 20, fontSize: '0.68rem', fontWeight: 700 }}>
                      {statusStyle.label}
                    </span>
                  </td>

                  {/* COMPONENTES */}
                  <td style={{ textAlign: 'center' }}>
                    <button
                      id={`btn-components-${p.id}`}
                      className="btn btn-ghost btn-sm"
                      title="Ver componentes del BOM"
                      onClick={() => setViewingComponents(p)}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        color: 'var(--primary)', fontSize: '0.72rem', fontWeight: 600,
                        padding: '4px 10px',
                        border: '1px solid #bfdbfe', borderRadius: 8,
                        background: '#eff6ff',
                        transition: 'all 0.15s',
                        cursor: 'pointer',
                      }}
                    >
                      <Layers size={12} />
                      Ver
                    </button>
                  </td>

                  {/* ACCIONES */}
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <button className="btn btn-ghost btn-sm" title="Configurar producto" onClick={() => setViewingProduct(p)}>
                        <Settings size={13} />
                      </button>
                      <button className="btn btn-primary btn-sm" onClick={() => setOrderingProduct(p)}>
                        <ShoppingBag size={13} /> PEDIR
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {viewingProduct && (
        <ProductDetailModal
          product={viewingProduct}
          token={token}
          onClose={() => setViewingProduct(null)}
          onSave={handleProductSaved}
        />
      )}

      {orderingProduct && (
        <OrderModal
          product={orderingProduct}
          token={token}
          onClose={() => setOrderingProduct(null)}
          onSuccess={() => { setOrderingProduct(null); load() }}
        />
      )}

      {viewingComponents && (
        <ComponentsModal
          product={viewingComponents}
          token={token}
          onClose={() => setViewingComponents(null)}
        />
      )}
    </div>
  )
}
