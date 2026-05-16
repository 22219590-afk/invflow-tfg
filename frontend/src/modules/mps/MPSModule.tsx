import { useState, useEffect } from 'react'
import {
  RefreshCw, TrendingUp, Users, Package, AlertTriangle,
  Download, BarChart3, FileText, CheckCircle2
} from 'lucide-react'
import { apiFetch } from '../core/api'

// ─── Types ────────────────────────────────────────────────────────────────────

type MonthDetail = {
  month_index: number
  month_name: string
  year: number
  demand: number
  real_demand: number | null
  deviation_pct: number | null
  production: number
  inventory: number
  workers: number
  hires: number
  fires: number
  capacity_utilization: number
  shortfall: number
}

type MPSData = {
  id: number
  name: string
  created_at: string
  total_cost: number
  breakdown: {
    production: number
    storage: number
    hiring: number
    firing: number
  }
  months: MonthDetail[]
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt   = (v: number | null | undefined) => Math.round(v ?? 0).toLocaleString('es-ES')
const fmtC  = (v: number | null | undefined) =>
  new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(v ?? 0)
const fmtPct = (v: number | null | undefined) => `${(v ?? 0).toFixed(1)}%`

function CapBar({ pct }: { pct: number }) {
  const color = pct > 95 ? '#ef4444' : pct > 80 ? '#f97316' : '#22c55e'
  return (
    <div style={{ width: '100%', background: '#f1f5f9', borderRadius: 4, height: 6, margin: '4px 0 0' }}>
      <div style={{ width: `${Math.min(pct, 100)}%`, background: color, height: 6, borderRadius: 4, transition: 'width 0.4s' }} />
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function MPSModule({ token }: { token: string }) {
  const [data, setData]     = useState<MPSData | null>(null)
  const [loading, setLoading] = useState(true)
  const [solving, setSolving] = useState(false)
  const [error, setError]   = useState<string | null>(null)

  useEffect(() => { fetchLatest() }, [])

  const fetchLatest = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch('/v1/mps/latest', token)
      setData(res)
    } catch (e: any) {
      setError(e.message || 'Error al cargar el plan maestro')
    } finally {
      setLoading(false)
    }
  }

  const handleSolve = async () => {
    setSolving(true)
    setError(null)
    try {
      await apiFetch('/v1/mps/solve', token, { method: 'POST' })
      await fetchLatest()
    } catch (e: any) {
      setError(e.message || 'Error al ejecutar la optimización')
    } finally {
      setSolving(false)
    }
  }

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (loading && !data) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', flexDirection: 'column', gap: 12 }}>
        <RefreshCw className="rotate-slow" size={28} color="var(--primary)" />
        <span style={{ fontSize: '0.85rem', color: '#64748b' }}>Cargando Plan Maestro...</span>
      </div>
    )
  }

  const months   = data?.months ?? []
  const breakdown = data?.breakdown ?? { production: 0, storage: 0, hiring: 0, firing: 0 }

  // ── Aggregate KPIs ──────────────────────────────────────────────────────────
  const totalProduction = months.reduce((a, m) => a + m.production, 0)
  const avgWorkers      = months.length ? months.reduce((a, m) => a + m.workers, 0) / months.length : 0
  const avgCapUtil      = months.length ? months.reduce((a, m) => a + (m.capacity_utilization ?? 0), 0) / months.length : 0
  const totalShortfall  = months.reduce((a, m) => a + (m.shortfall ?? 0), 0)
  const lastWorkers     = months.length ? months[months.length - 1].workers : 0

  return (
    <div className="animate-in" style={{ padding: '0 4px', maxWidth: '1440px', margin: '0 auto' }}>

      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--gray-400)', fontWeight: 700, fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>
            <FileText size={12} /> Planificación Agregada {data?.months?.[0]?.year ?? new Date().getFullYear()}
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>
            Master Production Schedule (MPS)
          </h2>
          {data?.created_at && (
            <div style={{ fontSize: '0.65rem', color: '#94a3b8', marginTop: 3 }}>
              Última optimización: {new Date(data.created_at).toLocaleString('es-ES')}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {error && (
            <span style={{ fontSize: '0.72rem', color: '#ef4444', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, padding: '4px 10px' }}>
              {error}
            </span>
          )}
          <button
            className="btn btn-primary"
            onClick={handleSolve}
            disabled={solving}
            style={{ fontSize: '0.78rem', padding: '8px 18px' }}
            id="mps-solve-btn"
          >
            <RefreshCw className={solving ? 'rotate-slow' : ''} size={14} />
            {solving ? 'Calculando PL...' : 'Ejecutar Optimización'}
          </button>
        </div>
      </div>

      {/* ── KPI RIBBON ──────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 20 }}>
        {[
          {
            label: 'Coste Total Optimizado',
            val: fmtC(data?.total_cost),
            sub: 'Producción + Mano de obra',
            color: 'var(--primary)',
            icon: <BarChart3 size={16} />,
          },
          {
            label: 'Producción Total',
            val: fmt(totalProduction) + ' uds',
            sub: 'Plan 12 meses',
            color: '#0891b2',
            icon: <Package size={16} />,
          },
          {
            label: 'Carga de Planta',
            val: fmtPct(avgCapUtil),
            sub: 'Utilización media',
            color: avgCapUtil > 95 ? '#ef4444' : avgCapUtil > 80 ? '#f97316' : '#22c55e',
            icon: <TrendingUp size={16} />,
          },
          {
            label: 'Operarios Fin de Año',
            val: Math.round(lastWorkers).toString(),
            sub: `Media: ${Math.round(avgWorkers)} op.`,
            color: '#7c3aed',
            icon: <Users size={16} />,
          },
          {
            label: 'Demanda No Cubierta',
            val: fmt(totalShortfall) + ' uds',
            sub: totalShortfall === 0 ? '✓ Plan factible' : '⚠ Revisar capacidad',
            color: totalShortfall === 0 ? '#22c55e' : '#ef4444',
            icon: totalShortfall === 0 ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />,
          },
        ].map((k, i) => (
          <div key={i} style={{ background: 'white', border: '1px solid var(--gray-200)', borderRadius: 10, padding: '14px 16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--gray-500)', textTransform: 'uppercase' }}>{k.label}</div>
              <div style={{ color: k.color, opacity: 0.7 }}>{k.icon}</div>
            </div>
            <div style={{ fontSize: '1.15rem', fontWeight: 900, color: k.color }}>{k.val}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--gray-400)', marginTop: 3 }}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* ── COST BREAKDOWN ──────────────────────────────────────────────────── */}
      <div style={{ background: 'white', border: '1px solid var(--gray-200)', borderRadius: 10, padding: '14px 20px', marginBottom: 20, display: 'flex', gap: 32, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--gray-500)', textTransform: 'uppercase' }}>Desglose de costes:</span>
        {[
          { label: 'Producción', val: breakdown.production, color: 'var(--primary)' },
          { label: 'Almacenamiento', val: breakdown.storage, color: '#0891b2' },
          { label: 'Contrataciones', val: breakdown.hiring, color: '#22c55e' },
          { label: 'Bajas', val: breakdown.firing, color: '#ef4444' },
        ].map(b => (
          <div key={b.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--gray-500)' }}>{b.label}:</span>
            <span style={{ fontSize: '0.88rem', fontWeight: 800, color: b.color }}>{fmtC(b.val)}</span>
          </div>
        ))}
      </div>

      {/* ── MAIN TABLE ──────────────────────────────────────────────────────── */}
      <div style={{ background: 'white', borderRadius: 10, border: '1px solid var(--gray-200)', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
        {/* Table header bar */}
        <div style={{ padding: '10px 16px', background: 'var(--gray-50)', borderBottom: '1px solid var(--gray-200)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--gray-700)' }}>
            Planificación Mensual — Optimización PL (PuLP/CBC)
          </span>
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.65rem', color: 'var(--gray-500)' }}>
              <div style={{ width: 8, height: 8, background: '#dbeafe', borderRadius: 2, border: '1px solid #93c5fd' }} /> Planificado LP
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.65rem', color: 'var(--gray-500)' }}>
              <div style={{ width: 8, height: 8, background: '#f0fdf4', borderRadius: 2, border: '1px solid #86efac' }} /> Real (pasado)
            </div>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
            <colgroup>
              <col style={{ width: 200 }} />
              {months.map((_, i) => <col key={i} style={{ width: 90 }} />)}
            </colgroup>
            <thead>
              <tr style={{ background: 'var(--gray-100)' }}>
                <th style={{ padding: '8px 16px', textAlign: 'left', fontSize: '0.65rem', fontWeight: 800, color: 'var(--gray-600)', textTransform: 'uppercase', borderBottom: '2px solid var(--gray-200)' }}>
                  Concepto / Mes
                </th>
                {months.map(m => (
                  <th key={m.month_index} style={{ padding: '8px', textAlign: 'center', fontSize: '0.7rem', fontWeight: 800, color: 'var(--gray-800)', borderBottom: '2px solid var(--gray-200)', borderLeft: '1px solid var(--gray-200)' }}>
                    {m.month_name.substring(0, 3).toUpperCase()}
                    <div style={{ fontSize: '0.55rem', fontWeight: 500, color: '#94a3b8', marginTop: 1 }}>
                      {m.is_past ? 'Real' : 'Plan'}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>

              {/* DEMANDA PREVISTA */}
              <Row label="Demanda Prevista" months={months} val={m => fmt(m.demand)} unit="uds" style={{ background: '#fafafa' }} />

              {/* DEMANDA REAL (only past) */}
              <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                <td style={{ padding: '8px 16px', paddingLeft: 28, fontSize: '0.7rem', color: 'var(--gray-500)' }}>
                  ↳ Real confirmada
                </td>
                {months.map(m => (
                  <td key={m.month_index} style={{ padding: '8px', textAlign: 'center', fontSize: '0.7rem', color: '#64748b', borderLeft: '1px solid var(--gray-100)', background: m.is_past ? '#f0fdf4' : 'transparent' }}>
                    {m.real_demand != null ? fmt(m.real_demand) : '—'}
                    {m.deviation_pct != null && (
                      <div style={{ fontSize: '0.58rem', color: Math.abs(m.deviation_pct) > 10 ? '#ef4444' : '#94a3b8' }}>
                        {m.deviation_pct > 0 ? '+' : ''}{m.deviation_pct.toFixed(1)}%
                      </div>
                    )}
                  </td>
                ))}
              </tr>

              {/* PRODUCCIÓN */}
              <tr style={{ borderBottom: '1px solid #bfdbfe', background: '#eff6ff' }}>
                <td style={{ padding: '10px 16px', fontSize: '0.78rem', fontWeight: 800, color: 'var(--primary)' }}>
                  PRODUCCIÓN PLANIFICADA
                </td>
                {months.map(m => (
                  <td key={m.month_index} style={{ padding: '10px 8px', textAlign: 'center', fontSize: '0.82rem', fontWeight: 900, color: 'var(--primary)', borderLeft: '1px solid #bfdbfe' }}>
                    {fmt(m.production)}
                    <div style={{ fontSize: '0.58rem', color: '#93c5fd', fontWeight: 500 }}>uds</div>
                  </td>
                ))}
              </tr>

              {/* SHORTFALL */}
              {totalShortfall > 0 && (
                <tr style={{ borderBottom: '1px solid #fecaca', background: '#fef2f2' }}>
                  <td style={{ padding: '8px 16px', paddingLeft: 28, fontSize: '0.7rem', color: '#b91c1c', fontWeight: 600 }}>
                    ↳ Demanda no cubierta
                  </td>
                  {months.map(m => (
                    <td key={m.month_index} style={{ padding: '8px', textAlign: 'center', fontSize: '0.72rem', fontWeight: 700, color: (m.shortfall ?? 0) > 0 ? '#b91c1c' : '#94a3b8', borderLeft: '1px solid #fecaca' }}>
                      {(m.shortfall ?? 0) > 0 ? fmt(m.shortfall) : '—'}
                    </td>
                  ))}
                </tr>
              )}

              {/* INVENTARIO FINAL */}
              <Row label="Stock Final Proyectado" months={months}
                val={m => fmt(m.inventory)} unit="uds"
                cellStyle={m => ({ background: m.inventory < 100 ? '#fef2f2' : 'transparent', color: m.inventory < 100 ? '#b91c1c' : '#374151' })}
              />

              {/* SEPARADOR */}
              <tr><td colSpan={months.length + 1} style={{ height: 2, background: 'var(--gray-200)' }} /></tr>

              {/* OPERARIOS */}
              <tr style={{ background: 'var(--gray-50)', borderBottom: '1px solid var(--gray-200)' }}>
                <td style={{ padding: '10px 16px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--gray-800)' }}>
                  Operarios Activos
                </td>
                {months.map(m => (
                  <td key={m.month_index} style={{ padding: '10px 8px', textAlign: 'center', fontSize: '0.75rem', fontWeight: 700, color: 'var(--gray-900)', borderLeft: '1px solid var(--gray-200)' }}>
                    {Math.round(m.workers)}
                    {m.hires > 0 && <div style={{ fontSize: '0.6rem', color: '#22c55e', fontWeight: 700 }}>+{Math.round(m.hires)}</div>}
                    {m.fires > 0 && <div style={{ fontSize: '0.6rem', color: '#ef4444', fontWeight: 700 }}>-{Math.round(m.fires)}</div>}
                  </td>
                ))}
              </tr>

              {/* UTILIZACIÓN */}
              <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                <td style={{ padding: '10px 16px', fontSize: '0.72rem', color: 'var(--gray-600)' }}>
                  Carga de Planta
                </td>
                {months.map(m => {
                  const pct = m.capacity_utilization ?? 0
                  const col = pct > 95 ? '#ef4444' : pct > 80 ? '#f97316' : '#22c55e'
                  return (
                    <td key={m.month_index} style={{ padding: '8px', textAlign: 'center', borderLeft: '1px solid var(--gray-100)' }}>
                      <div style={{ fontSize: '0.72rem', fontWeight: 700, color: col }}>{fmtPct(pct)}</div>
                      <CapBar pct={pct} />
                    </td>
                  )
                })}
              </tr>

            </tbody>
          </table>
        </div>

        {/* FOOTER */}
        <div style={{ padding: '12px 16px', background: 'var(--gray-50)', borderTop: '1px solid var(--gray-200)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>
            Modelo: Programación Lineal (PuLP/CBC) · Variables: Producción, Inventario, Operarios, Contrataciones, Bajas, Déficit
          </div>
          <div style={{ display: 'flex', gap: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--gray-400)', textTransform: 'uppercase' }}>Coste Mano de Obra:</span>
              <span style={{ fontSize: '0.88rem', fontWeight: 800, color: 'var(--gray-800)' }}>{fmtC(breakdown.hiring + breakdown.firing)}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--gray-400)', textTransform: 'uppercase' }}>Coste Stock:</span>
              <span style={{ fontSize: '0.88rem', fontWeight: 800, color: '#0891b2' }}>{fmtC(breakdown.storage)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Row helper ───────────────────────────────────────────────────────────────

function Row({ label, months, val, unit, style, cellStyle }: {
  label: string
  months: MonthDetail[]
  val: (m: MonthDetail) => string
  unit?: string
  style?: React.CSSProperties
  cellStyle?: (m: MonthDetail) => React.CSSProperties
}) {
  return (
    <tr style={{ borderBottom: '1px solid var(--gray-100)', ...style }}>
      <td style={{ padding: '10px 16px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--gray-700)' }}>
        {label}
      </td>
      {months.map(m => (
        <td key={m.month_index} style={{ padding: '10px 8px', textAlign: 'center', fontSize: '0.75rem', color: '#4b5563', borderLeft: '1px solid var(--gray-100)', ...(cellStyle ? cellStyle(m) : {}) }}>
          {val(m)}
          {unit && <div style={{ fontSize: '0.58rem', color: '#94a3b8' }}>{unit}</div>}
        </td>
      ))}
    </tr>
  )
}
