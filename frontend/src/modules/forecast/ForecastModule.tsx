import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { BarChart3, RefreshCw, Search, Layers, ChevronRight, AlertCircle, ShieldCheck, Activity, Info } from 'lucide-react';

const API = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
const auth = (t: string) => ({ Authorization: `Bearer ${t}` });

function safe(v: any, d = 0) { const n = parseFloat(v); return isNaN(n) ? d : n; }
function safeStr(v: any, d = '—') { return v || d; }

export default function ForecastModule({ token }: { token: string }) {
  const [products, setProducts] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState<'chart'|'models'|'stats'>('chart');
  const [search, setSearch] = useState('');
  const [abc, setAbc] = useState('ALL');
  const [msg, setMsg] = useState('');

  useEffect(() => { fetchProducts(); }, []);

  async function fetchProducts() {
    setLoadingList(true);
    try {
      const r = await fetch(`${API}/v1/forecast/products`, { headers: auth(token) });
      const data = await r.json();
      setProducts(Array.isArray(data) ? data : []);
      if (Array.isArray(data) && data.length > 0) selectProduct(data[0]);
    } catch (e: any) { setMsg('Error: ' + e.message); }
    finally { setLoadingList(false); }
  }

  async function selectProduct(p: any) {
    setSelected(p); setDetail(null); setComparison(null); setTab('chart'); setLoadingDetail(true);
    try {
      const r = await fetch(`${API}/v1/forecast/${p.odoo_id}?granularity=monthly`, { headers: auth(token) });
      setDetail(await r.json());
    } catch (e: any) { setMsg('Error Detail: ' + (e as any).message); }
    finally { setLoadingDetail(false); }
  }

  async function loadComparison(p: any) {
    try {
      const r = await fetch(`${API}/v1/forecast/${p.odoo_id}/comparison`, { headers: auth(token) });
      if (r.ok) setComparison(await r.json());
    } catch {}
  }

  async function runForecast() {
    setRunning(true); setMsg('');
    try {
      const r = await fetch(`${API}/v1/forecast/run`, { method: 'POST', headers: auth(token) });
      const d = await r.json();
      setMsg(`✓ ${d.summary?.processed ?? 0} procesados`);
      fetchProducts();
    } catch (e: any) { setMsg('Error: ' + e.message); }
    finally { setRunning(false); }
  }

  const filtered = products.filter(p => {
    const q = search.toLowerCase();
    return (abc === 'ALL' || p.abc_class === abc) &&
      (!q || p.name?.toLowerCase().includes(q) || p.default_code?.toLowerCase().includes(q));
  });

  const MAPE_COLOR = (m: number) => m < 20 ? 'var(--success)' : m < 35 ? 'var(--warning)' : 'var(--danger)';

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden', background:'var(--app-bg)' }}>

      {/* ULTRA-COMPACT HEADER */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'8px 20px', background:'white', borderBottom:'1px solid var(--gray-200)', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <BarChart3 size={18} color="var(--primary)" />
          <h2 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>Análisis de Previsión</h2>
        </div>
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <div style={{ position:'relative' }}>
            <Search size={12} style={{ position:'absolute', left:'10px', top:'50%', transform:'translateY(-50%)', color:'var(--gray-400)' }} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Filtrar SKU..." style={{ paddingLeft:'28px', padding:'6px 10px', borderRadius:'6px', border:'1px solid var(--gray-200)', width:'150px', fontSize:'0.75rem', outline:'none' }} />
          </div>
          <div style={{ display:'flex', background:'var(--gray-100)', padding:'2px', borderRadius:'6px' }}>
            {['ALL','A','B','C'].map(f => (
              <button key={f} onClick={() => setAbc(f)} style={{ padding:'4px 10px', borderRadius:'4px', fontSize:'0.7rem', fontWeight:800, cursor:'pointer', border:'none', background: abc===f ? 'white' : 'transparent', color: abc===f ? 'var(--primary)' : 'var(--gray-500)', boxShadow: abc===f ? '0 1px 2px rgba(0,0,0,0.05)' : 'none' }}>{f}</button>
            ))}
          </div>
          <button onClick={runForecast} disabled={running} className="btn btn-primary" style={{ padding:'6px 12px', fontSize:'0.75rem' }}>
            <RefreshCw size={12} className={running ? 'rotate-slow' : ''} />
            {running ? 'Ejecutando...' : 'Actualizar'}
          </button>
        </div>
      </div>

      <div style={{ display:'flex', flex:1, overflow:'hidden' }}>

        {/* NARROW HIGH-DENSITY SIDEBAR */}
        <div style={{ width:'240px', borderRight:'1px solid var(--gray-200)', background:'white', overflowY:'auto', flexShrink:0 }}>
          {loadingList && <div style={{ padding:'24px', textAlign:'center', color:'var(--gray-400)', fontSize:'0.75rem' }}>Cargando catálogo...</div>}
          {filtered.map(p => {
            const isSel = selected?.odoo_id === p.odoo_id;
            return (
              <div key={p.odoo_id} onClick={() => selectProduct(p)} style={{ padding:'10px 16px', borderBottom:'1px solid var(--gray-50)', cursor:'pointer', background: isSel ? 'var(--gray-50)' : 'transparent', borderLeft:`3px solid ${isSel ? 'var(--primary)' : 'transparent'}`, transition:'all 0.1s' }}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'2px' }}>
                  <span style={{ fontSize:'0.6rem', color: 'var(--gray-400)', fontWeight:800 }}>{safeStr(p.default_code,'—')}</span>
                  <span className={`badge-abc abc-${(p.abc_class||'c').toLowerCase()}`} style={{ scale:'0.8', transformOrigin:'right' }}>{p.abc_class||'C'}</span>
                </div>
                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                  <p style={{ fontSize:'0.8rem', fontWeight:isSel ? 700 : 600, color: isSel ? 'var(--primary)' : 'var(--gray-700)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', margin:0 }}>{p.name}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* COMPACT ANALYTICS WORKSPACE */}
        <div style={{ flex:1, overflowY:'auto', padding:'20px' }}>
          {loadingDetail && <div style={{ height:'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--gray-400)', fontSize:'0.8rem' }}><RefreshCw size={24} className="rotate-slow" /></div>}

          {detail && !loadingDetail && (
            <div style={{ maxWidth:'1000px', margin:'0 auto' }} className="animate-in">
              
              {/* COMPACT PRODUCT INFO */}
              <div style={{ background:'white', borderRadius:8, padding:'16px 20px', border:'1px solid var(--gray-200)', marginBottom:16, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <div>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:4 }}>
                    <span style={{ background:'var(--primary)', color:'white', fontSize:'0.6rem', fontWeight:900, padding:'1px 6px', borderRadius:3 }}>SKU: {safeStr(detail.product_code)}</span>
                    <span style={{ fontSize:'0.65rem', fontWeight:700, color:'var(--success)', display:'flex', alignItems:'center', gap:3 }}><ShieldCheck size={10} /> Optimizado</span>
                  </div>
                  <h1 style={{ fontSize:'1.4rem', fontWeight:800, color:'var(--gray-900)', margin:0 }}>{detail.product_name}</h1>
                  <div style={{ display:'flex', gap:12, marginTop:8 }}>
                    <div style={{ fontSize:'0.75rem' }}><span style={{color:'var(--gray-400)', fontWeight:700}}>MODELO:</span> <span style={{fontWeight:700}}>{detail.forecast_model}</span></div>
                    <div style={{ borderLeft:'1px solid var(--gray-100)', paddingLeft:12, fontSize:'0.75rem' }}><span style={{color:'var(--gray-400)', fontWeight:700}}>PATRÓN:</span> <span style={{fontWeight:700}}>{detail.demand_pattern}</span></div>
                  </div>
                </div>
                <div style={{ textAlign:'right' }}>
                  <p style={{ fontSize:'0.6rem', fontWeight:800, color:'var(--gray-400)', textTransform:'uppercase' }}>Error de Modelo (Backtest)</p>
                  <p style={{ fontSize:'1.8rem', fontWeight:900, color: MAPE_COLOR(safe(comparison?.models.find((m:any)=>m.is_winner)?.mape || detail.forecast_mape)), margin:0 }}>
                    {safe(comparison?.models.find((m:any)=>m.is_winner)?.mape || detail.forecast_mape).toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* ANALYTICS CONTENT */}
              <div style={{ background:'white', borderRadius:8, border:'1px solid var(--gray-200)', overflow:'hidden' }}>
                <div style={{ display:'flex', background:'var(--gray-50)', borderBottom:'1px solid var(--gray-100)' }}>
                  {([['chart','Tendencia',Activity],['models','Algoritmos',Layers],['stats','Análisis Est.',Info]] as any[]).map(([id,label,Icon]) => (
                    <button key={id} onClick={() => { setTab(id); if(id==='models' && !comparison) loadComparison(selected); }}
                      style={{ display:'flex', alignItems:'center', gap:6, padding:'10px 20px', border:'none', cursor:'pointer', fontSize:'0.75rem', fontWeight:700, background: tab===id ? 'white' : 'transparent', color: tab===id ? 'var(--primary)' : 'var(--gray-500)', borderBottom: tab===id ? '2px solid var(--primary)' : '2px solid transparent' }}>
                      <Icon size={14} />{label}
                    </button>
                  ))}
                </div>

                <div style={{ padding:'24px' }}>
                  {tab === 'chart' && (
                    <div className="animate-in">
                      <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={detail.chart_data} margin={{ top:5, right:10, left:0, bottom:0 }}>
                          <defs>
                            <linearGradient id="gR" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--primary)" stopOpacity={0.1}/><stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/></linearGradient>
                            <linearGradient id="gF" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="var(--info)" stopOpacity={0.1}/><stop offset="95%" stopColor="var(--info)" stopOpacity={0}/></linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" vertical={false} />
                          <XAxis dataKey="date_label" stroke="var(--gray-400)" fontSize={10} tickLine={false} axisLine={false} />
                          <YAxis stroke="var(--gray-400)" fontSize={10} tickLine={false} axisLine={false} />
                          <Tooltip contentStyle={{ fontSize:'0.75rem', borderRadius:8, border:'none', boxShadow:'0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                          <Area type="monotone" dataKey="real" name="Real" stroke="var(--primary)" strokeWidth={2} fill="url(#gR)" dot={{ r:2, fill:'var(--primary)' }} connectNulls={true} />
                          <Area type="monotone" dataKey="forecast" name="Forecast" stroke="var(--info)" strokeWidth={2} strokeDasharray="5 5" fill="url(#gF)" dot={false} connectNulls={true} />
                        </AreaChart>
                      </ResponsiveContainer>
                      
                      {/* HIGH-DENSITY KPI RIBBON */}
                      <div style={{ display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:10, marginTop:24 }}>
                        {[
                          { label: 'Demanda Diaria', val: safe(detail.daily_demand).toFixed(1), unit: 'un/día (proyectado)', color: 'var(--gray-800)' },
                          { label: 'Media Histórica', val: safe(detail.metrics?.mean).toFixed(1), unit: 'un/sem (histórico)', color: 'var(--gray-500)' },
                          { label: 'Error Modelo', val: `${safe(comparison?.models.find((m:any)=>m.is_winner)?.mape || detail.forecast_mape).toFixed(1)}%`, unit: 'MAPE (Precisión)', color: MAPE_COLOR(safe(detail.forecast_mape)) },
                          { label: 'Algoritmo', val: detail.forecast_model, unit: 'Modelo Activo', color: 'var(--primary)' },
                          { label: 'Previsión Semanal', val: Math.round(safe(detail.daily_demand) * 7), unit: 'Próx. 7 días', color: 'var(--info)' }
                        ].map((k, i) => (
                          <div key={i} style={{ background:'white', border:'1px solid var(--gray-200)', borderRadius:6, padding:'10px 12px', boxShadow:'var(--shadow-sm)' }}>
                            <div style={{ fontSize: '0.6rem', fontWeight: 800, color: 'var(--gray-400)', textTransform: 'uppercase', marginBottom: 4 }}>{k.label}</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 900, color: k.color }}>{k.val}</div>
                            <div style={{ fontSize: '0.6rem', color: 'var(--gray-500)', marginTop: 2, fontWeight: 600 }}>{k.unit}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {tab === 'models' && (
                    <div className="animate-in">
                      {!comparison && <div style={{ textAlign:'center', padding:'20px', color:'var(--gray-400)' }}><RefreshCw size={20} className="rotate-slow" /></div>}
                      {comparison && (
                        <table className="data-table">
                          <thead>
                            <tr style={{ fontSize:'0.65rem' }}>
                              <th>ALGORITMO</th>
                              <th style={{ textAlign:'right' }}>MAE</th>
                              <th style={{ textAlign:'right' }}>MAPE</th>
                              <th style={{ textAlign:'right' }}>RMSE</th>
                              <th style={{ textAlign:'center' }}>SCORE</th>
                            </tr>
                          </thead>
                          <tbody style={{ fontSize:'0.75rem' }}>
                            {(comparison.models || []).map((m: any) => (
                              <tr key={m.model} style={{ background: m.is_winner ? 'var(--primary-lighter)' : 'transparent' }}>
                                <td style={{ fontWeight: 800, color: m.is_winner ? 'var(--primary-dark)' : 'var(--gray-700)' }}>{m.model}</td>
                                <td style={{ textAlign:'right', fontFamily:'monospace' }}>{safe(m.mae).toFixed(2)}</td>
                                <td style={{ textAlign:'right', fontFamily:'monospace', fontWeight:800, color: MAPE_COLOR(safe(m.mape)) }}>{safe(m.mape).toFixed(1)}%</td>
                                <td style={{ textAlign:'right', fontFamily:'monospace' }}>{safe(m.rmse).toFixed(2)}</td>
                                <td style={{ textAlign:'center' }}>
                                  {m.is_winner ? <span className="badge badge-success" style={{ fontSize:'0.6rem' }}>ÓPTIMO</span> : <span style={{color:'var(--gray-300)'}}>—</span>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}

                  {tab === 'stats' && detail.metrics && (
                    <div className="animate-in" style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
                      <div className="panel" style={{ padding:16, background:'var(--gray-50)' }}>
                        <p style={{ fontSize:'0.65rem', fontWeight:800, color:'var(--gray-400)', textTransform:'uppercase', marginBottom:12 }}>Distribución Central</p>
                        {[
                          ['Media', safe(detail.metrics.mean).toFixed(2)],
                          ['Mediana', safe(detail.metrics.median).toFixed(2)],
                          ['Desv. Estándar', safe(detail.metrics.std_dev).toFixed(2)],
                          ['Percentil 75', safe(detail.metrics.p75).toFixed(2)]
                        ].map(([l, v]) => (
                          <div key={l} style={{ display:'flex', justifyContent:'space-between', padding:'6px 0', borderBottom:'1px solid var(--gray-100)', fontSize:'0.75rem' }}>
                            <span style={{ color:'var(--gray-500)' }}>{l}</span>
                            <span style={{ fontWeight:700 }}>{v}</span>
                          </div>
                        ))}
                      </div>
                      <div className="panel" style={{ padding:16, background:'var(--gray-50)' }}>
                        <p style={{ fontSize:'0.65rem', fontWeight:800, color:'var(--gray-400)', textTransform:'uppercase', marginBottom:12 }}>Métricas de Error (Backtesting)</p>
                        {[
                          ['MAPE Global', `${safe(detail.forecast_mape).toFixed(2)}%`],
                          ['MAE', safe(detail.metrics.mae).toFixed(4)],
                          ['RMSE', safe(detail.metrics.rmse).toFixed(4)],
                          ['Outliers Detectados', detail.metrics.outliers_count || 0]
                        ].map(([l, v]) => (
                          <div key={l} style={{ display:'flex', justifyContent:'space-between', padding:'6px 0', borderBottom:'1px solid var(--gray-100)', fontSize:'0.75rem' }}>
                            <span style={{ color:'var(--gray-500)' }}>{l}</span>
                            <span style={{ fontWeight:700 }}>{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
