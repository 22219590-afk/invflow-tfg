import { useState, useEffect } from 'react'
import { 
  AlertTriangle, RefreshCw, Package, DollarSign, TrendingUp, Zap, Activity,
  ArrowUpRight, ArrowDownRight, Minus, Clock
} from 'lucide-react'
import { apiFetch } from '../core/api'

const PERIOD_OPTIONS = [
  { label: 'Última semana', days: 7 },
  { label: 'Último mes', days: 30 },
  { label: 'Trimestre', days: 90 },
  { label: 'Año', days: 365 },
]

function KPICard({ label, value, sub, trend, icon: Icon, good = 'up', tooltip, onClick }: any) {
  const trendValue = parseFloat(trend) || 0
  const isGood = good === 'up' ? trendValue >= 0 : trendValue <= 0
  const isNeutral = trendValue === 0
  
  return (
    <div className="kpi-card-v2 animate-in" onClick={onClick}>
      {tooltip && <div className="kpi-tooltip">{tooltip}</div>}
      <div className="kpi-icon-v2"><Icon size={20} /></div>
      <div className="kpi-label-v2">{label}</div>
      <div className="kpi-value-v2">{value}</div>
      
      <div className="kpi-trend-container">
        <div className={`trend-pill ${isNeutral ? 'neutral' : isGood ? 'positive' : 'negative'}`}>
          {isNeutral ? <Minus size={12} /> : trendValue > 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
          {trendValue > 0 ? '+' : ''}{trendValue}%
        </div>
        <div className="kpi-sub-v2">{sub}</div>
      </div>
    </div>
  )
}

export default function DashboardModule({ token, setView }: { token: string; setView: (v: string) => void }) {
  const [kpis, setKpis] = useState<any>(null)
  const [period, setPeriod] = useState(30)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    apiFetch(`/kpis?period_days=${period}`, token)
      .then(data => {
        setKpis(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [token, period])

  if (loading || !kpis) {
    return (
      <div className="loading-state" style={{ display: 'flex', flexDirection: 'column', gap: '16px', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <RefreshCw className="rotate-slow" size={32} color="#3b82f6" />
        <p style={{ color: '#64748b', fontWeight: 500 }}>Sincronizando indicadores operativos...</p>
      </div>
    )
  }

  const fmtCurrency = (val: number) => {
    if (val >= 1000000) return `${(val / 1000000).toFixed(2)}M€`
    if (val >= 1000) return `${(val / 1000).toFixed(1)}k€`
    return `${val.toFixed(0)}€`
  }

  const clean = (val: any) => (val === undefined || val === null || isNaN(val)) ? 0 : val

  return (
    <div className="animate-in">
      <div className="view-header" style={{ marginBottom: '40px' }}>
        <div>
          <h2 className="view-title">Dashboard Operativo</h2>
          <p className="view-subtitle">Análisis Operativo</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Periodo:</label>
          <select
            className="form-input"
            style={{ width: 'auto', padding: '8px 16px', minWidth: '160px' }}
            value={period}
            onChange={e => setPeriod(Number(e.target.value))}
          >
            {PERIOD_OPTIONS.map(o => <option key={o.days} value={o.days}>{o.label}</option>)}
          </select>
        </div>
      </div>

      <div className="kpi-grid-v2">
        {/* Row 1 */}
        <KPICard 
          label="Valor Inventario" 
          value={fmtCurrency(clean(kpis.total_value))} 
          trend={kpis.total_value_trend}
          sub="vs periodo anterior" 
          icon={DollarSign} 
          tooltip="Valor total del stock actual en almacén"
        />
        <KPICard 
          label="Nivel Servicio" 
          value={`${clean(kpis.service_level ?? kpis.otif_pct)}%`} 
          trend={kpis.service_level_trend ?? kpis.otif_pct_trend}
          sub={`Objetivo: ${kpis.service_level_target ?? 99}% · ${kpis.late_orders ?? 0} retrasos de ${kpis.total_orders ?? 0}`} 
          icon={TrendingUp} 
          tooltip="Nivel de servicio = 1 - (pedidos atrasados / pedidos totales). Objetivo: 99%"
        />
        <KPICard 
          label="Cobertura" 
          value={`${clean(kpis.coverage)} días`} 
          trend={kpis.coverage_trend}
          sub="Días de inventario" 
          icon={Clock} 
          tooltip="Días estimados que durará el stock actual según demanda media"
        />
        <KPICard 
          label="Rotación" 
          value={`${clean(kpis.turnover)}x`} 
          trend={kpis.turnover_trend}
          sub="Ratio eficiencia" 
          icon={Activity} 
          tooltip="Veces que se renueva el stock en el periodo"
        />

        {/* Row 2 */}
        <KPICard 
          label="Riesgo Rotura" 
          value={`${clean(kpis.stockout_pct)}%`} 
          trend={kpis.stockout_pct_trend}
          sub="Artículos sin stock" 
          icon={Zap} 
          good="down"
          tooltip="Porcentaje de SKUs con stock cero"
        />
        <KPICard 
          label="Late Cliente (C)" 
          value={clean(kpis.late_c)} 
          trend={kpis.late_c_trend}
          sub="Retrasos salida" 
          icon={AlertTriangle} 
          good="down"
          tooltip="Pedidos de cliente fuera de fecha comprometida"
          onClick={() => setView('inventory')}
        />
        <KPICard 
          label="Late Prov. (P)" 
          value={clean(kpis.late_p)} 
          trend={kpis.late_p_trend}
          sub="Retrasos entrada" 
          icon={RefreshCw} 
          good="down"
          tooltip="Entregas de proveedor fuera de fecha"
          onClick={() => setView('inventory')}
        />
        <KPICard 
          label="Stock Mínimo" 
          value={clean(kpis.items_below_min)} 
          trend={kpis.items_below_min_trend}
          sub="SKUs en reorden" 
          icon={Package} 
          good="down"
          tooltip="Artículos por debajo del punto de pedido crítico"
          onClick={() => setView('inventory')}
        />
      </div>
    </div>
  )
}
