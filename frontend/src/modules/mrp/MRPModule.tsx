import { useState, useEffect } from 'react'
import { RefreshCw, Layers, Package, Calendar, AlertTriangle, ChevronRight, FileText, Download, Network, Database } from 'lucide-react'
import { apiFetch } from '../core/api'

export default function MRPModule({ token }: { token: string }) {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [solving, setSolving] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState<any>(null)
  const [bomTree, setBomTree] = useState<any>(null)
  const [view, setView] = useState<'grid' | 'bom'>('grid')

  useEffect(() => {
    fetchMRP()
  }, [])

  const fetchMRP = async (forceSelect?: boolean) => {
    setLoading(true)
    try {
      const res = await apiFetch('/v1/mrp/view', token)
      const validData = Array.isArray(res) ? res : []
      setData(validData)
      if (validData.length > 0 && (forceSelect || !selectedProduct)) {
        // Find if current selection still exists
        const current = selectedProduct ? validData.find(p => p.product_id === selectedProduct.product_id) : null
        setSelectedProduct(current || validData[0])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSolve = async () => {
    setSolving(true)
    try {
      await apiFetch('/v1/mrp/solve', token, { method: 'POST' })
      await fetchMRP(true)
    } catch (e) {
      console.error(e)
    } finally {
      setSolving(false)
    }
  }

  const fetchBOM = async (pid: number) => {
    try {
      const res = await apiFetch(`/v1/mrp/bom/${pid}`, token)
      setBomTree(res)
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    if (selectedProduct && view === 'bom') {
      fetchBOM(selectedProduct.product_id)
    }
  }, [selectedProduct, view])

  if (loading && data.length === 0) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'60vh' }}>
        <RefreshCw className="rotate-slow" size={24} color="var(--primary)" />
      </div>
    )
  }

  if (!loading && data.length === 0) {
    return (
      <div className="animate-in" style={{ padding: '0 4px', maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>Material Requirements Planning (MRP)</h2>
          <button className="btn btn-primary" onClick={handleSolve} disabled={solving} style={{ fontSize:'0.75rem', padding:'6px 16px' }}>
            <RefreshCw className={solving ? 'rotate-slow' : ''} size={14} />
            {solving ? 'Ejecutando Explosion...' : 'Ejecutar MRP'}
          </button>
        </div>
        <div style={{ background:'white', borderRadius:12, border:'2px dashed var(--gray-200)', padding:'80px 40px', textAlign:'center' }}>
          <div style={{ background:'var(--primary-lighter)', width:64, height:64, borderRadius:32, display:'flex', alignItems:'center', justifyContent:'center', margin:'0 auto 24px' }}>
            <Layers size={32} color="var(--primary)" />
          </div>
          <h3 style={{ fontSize:'1.1rem', fontWeight:800, color:'var(--gray-800)', marginBottom:8 }}>Sin Datos de Planificación</h3>
          <p style={{ color:'var(--gray-500)', maxWidth:500, margin:'0 auto 24px', fontSize:'0.85rem', lineHeight:1.6 }}>
            El módulo MRP requiere dos entradas fundamentales para funcionar:<br/>
            1. <b>Plan Maestro (MPS)</b> calculado previamente.<br/>
            2. <b>Listas de Materiales (BOM)</b> sincronizadas desde Odoo.
          </p>
          <div style={{ display:'flex', gap:12, justifyContent:'center' }}>
            <button className="btn btn-ghost" style={{ fontSize:'0.75rem', border:'1px solid var(--gray-200)' }}>Revisar BOMs</button>
            <button className="btn btn-primary" onClick={handleSolve} style={{ fontSize:'0.75rem' }}>Calcular Necesidades</button>
          </div>
        </div>
      </div>
    )
  }

  const fmt = (val: number) => Math.round(val).toLocaleString()

  return (
    <div className="animate-in" style={{ padding: '0 4px', maxWidth: '1400px', margin: '0 auto' }}>
      
      {/* PROFESSIONAL COMPACT HEADER */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: 20 }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:6, color:'var(--gray-400)', fontWeight:700, fontSize:'0.65rem', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:2 }}>
            <Database size={12} /> Planificación de Requerimientos
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--gray-900)', margin: 0 }}>Material Requirements Planning (MRP)</h2>
        </div>
        <div style={{ display:'flex', gap:8 }}>
          <div style={{ display:'flex', background:'var(--gray-100)', padding:'3px', borderRadius:'6px', marginRight: 12 }}>
            <button onClick={() => setView('grid')} style={{ padding:'4px 12px', borderRadius:'4px', fontSize:'0.7rem', fontWeight:800, border:'none', background: view==='grid' ? 'white' : 'transparent', color: view==='grid' ? 'var(--primary)' : 'var(--gray-500)', boxShadow: view==='grid' ? 'var(--shadow-sm)' : 'none' }}>GRID MRP</button>
            <button onClick={() => setView('bom')} style={{ padding:'4px 12px', borderRadius:'4px', fontSize:'0.7rem', fontWeight:800, border:'none', background: view==='bom' ? 'white' : 'transparent', color: view==='bom' ? 'var(--primary)' : 'var(--gray-500)', boxShadow: view==='bom' ? 'var(--shadow-sm)' : 'none' }}>BOM TREE</button>
          </div>
          <button className="btn btn-primary" onClick={handleSolve} disabled={solving} style={{ fontSize:'0.75rem', padding:'6px 16px' }}>
            <RefreshCw className={solving ? 'rotate-slow' : ''} size={14} />
            {solving ? 'Calculando Explosion...' : 'Ejecutar MRP'}
          </button>
        </div>
      </div>

      <div style={{ display:'flex', gap:20 }}>
        
        {/* PRODUCT LIST SIDEBAR */}
        <div style={{ width: '280px', flexShrink: 0, background:'white', borderRadius:8, border:'1px solid var(--gray-200)', overflow:'hidden' }}>
          <div style={{ padding:'12px 16px', background:'var(--gray-50)', borderBottom:'1px solid var(--gray-200)', fontSize:'0.75rem', fontWeight:800 }}>Materiales / Componentes</div>
          <div style={{ maxHeight:'70vh', overflowY:'auto' }}>
            {data.map(p => (
              <div 
                key={p.product_id} 
                onClick={() => setSelectedProduct(p)}
                style={{ padding:'12px 16px', borderBottom:'1px solid var(--gray-50)', cursor:'pointer', background: selectedProduct?.product_id === p.product_id ? 'var(--primary-lighter)' : 'transparent', borderLeft: `3px solid ${selectedProduct?.product_id === p.product_id ? 'var(--primary)' : 'transparent'}` }}
              >
                <div style={{ fontSize:'0.65rem', color:'var(--gray-400)', fontWeight:700 }}>{p.sku}</div>
                <div style={{ fontSize:'0.8rem', fontWeight:700, color: selectedProduct?.product_id === p.product_id ? 'var(--primary)' : 'var(--gray-800)' }}>{p.name}</div>
              </div>
            ))}
          </div>
        </div>

        {/* MAIN ANALYSIS AREA */}
        <div style={{ flex:1 }}>
          {view === 'grid' && selectedProduct && (
            <div className="animate-in">
              {/* MRP SUB-HEADER */}
              <div style={{ background:'white', padding:'16px 20px', borderRadius:8, border:'1px solid var(--gray-200)', marginBottom:16, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <div>
                  <h3 style={{ margin:0, fontSize:'1rem', fontWeight:800 }}>{selectedProduct.name}</h3>
                  <div style={{ display:'flex', gap:12, marginTop:4, fontSize:'0.7rem', color:'var(--gray-500)', fontWeight:600 }}>
                    <span>Lead Time: <b>{selectedProduct.lead_time} días</b></span>
                    <span>Stock Seguridad: <b>{selectedProduct.safety_stock} un</b></span>
                    <span>Tipo: <b>Aprovisionamiento LFL</b></span>
                  </div>
                </div>
                <div style={{ textAlign:'right' }}>
                  <span className="badge-abc abc-a">Nivel 0</span>
                </div>
              </div>

              {/* THE MRP GRID */}
              <div style={{ background: 'white', borderRadius: 8, border: '1px solid var(--gray-200)', overflow: 'hidden' }}>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
                    <thead>
                      <tr style={{ background: 'var(--gray-100)' }}>
                        <th style={{ width: 220, padding: '10px 16px', textAlign: 'left', fontSize: '0.65rem', fontWeight: 800, color: 'var(--gray-600)', textTransform: 'uppercase', borderBottom: '1px solid var(--gray-200)' }}>Cálculo MRP / Fecha</th>
                        {selectedProduct.periods.map((per: any, idx: number) => (
                          <th key={idx} style={{ padding: '10px 8px', textAlign: 'center', fontSize: '0.65rem', fontWeight: 800, color: 'var(--gray-700)', borderBottom: '1px solid var(--gray-200)', borderLeft: '1px solid var(--gray-200)' }}>
                            {new Date(per.date).toLocaleDateString('es-ES', { month:'short', day:'numeric' })}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { label: 'Necesidad Bruta', key: 'gross', weight: 600, color: 'var(--gray-800)' },
                        { label: 'Rec. Programadas', key: 'scheduled', weight: 500, color: 'var(--success)' },
                        { label: 'Disp. Proyectado', key: 'projected', weight: 600, color: 'var(--gray-500)', bg: '#fcfcfc' },
                        { label: 'Necesidad Neta', key: 'net', weight: 800, color: 'var(--danger)' },
                        { label: 'Recepción Planif.', key: 'net', weight: 700, color: 'var(--primary)' },
                        { label: 'Liberación Orden', key: 'release', weight: 900, color: 'var(--info)', bg: 'var(--info-light)' },
                      ].map((row, ridx) => (
                        <tr key={ridx} style={{ borderBottom: '1px solid var(--gray-50)', background: row.bg || 'transparent' }}>
                          <td style={{ padding: '10px 16px', fontSize: '0.72rem', fontWeight: row.weight, color: row.color }}>{row.label}</td>
                          {selectedProduct.periods.map((per: any, idx: number) => (
                            <td key={idx} style={{ padding: '10px 8px', textAlign: 'center', fontSize: '0.72rem', fontWeight: row.weight, color: row.color, borderLeft: '1px solid var(--gray-50)' }}>
                              {per[row.key] > 0 ? fmt(per[row.key]) : '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {view === 'bom' && bomTree && (
            <div className="animate-in" style={{ background:'white', borderRadius:8, border:'1px solid var(--gray-200)', padding:32 }}>
              <h3 style={{ fontSize:'1rem', fontWeight:800, marginBottom:24 }}>Explosión de Materiales (BOM Tree)</h3>
              <div style={{ marginLeft:0 }}>
                <BOMNode node={bomTree} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function BOMNode({ node, level = 0 }: { node: any, level?: number }) {
  if (!node) return null
  return (
    <div style={{ marginLeft: level * 32, marginBottom: 8 }}>
      <div style={{ display:'flex', alignItems:'center', gap:8, padding:'8px 12px', border:'1px solid var(--gray-100)', borderRadius:6, background: level === 0 ? 'var(--primary-lighter)' : 'white' }}>
        <Network size={14} color="var(--primary)" />
        <span style={{ fontSize:'0.75rem', fontWeight:800, color:'var(--gray-800)' }}>{node.sku}</span>
        <span style={{ fontSize:'0.8rem', fontWeight:600, color:'var(--gray-600)' }}>{node.name}</span>
        <span style={{ fontSize:'0.7rem', color:'var(--primary)', fontWeight:800, marginLeft:'auto' }}>x{node.qty} un</span>
        <div style={{ fontSize:'0.6rem', background:'var(--gray-100)', padding:'2px 6px', borderRadius:4, fontWeight:700 }}>LT: {node.lead_time}d</div>
      </div>
      {node.children && node.children.map((c: any, i: number) => (
        <div key={i} style={{ position:'relative', paddingTop:8 }}>
          <div style={{ position:'absolute', left:-16, top:0, bottom: '50%', width:16, borderLeft:'1px solid var(--gray-200)', borderBottom:'1px solid var(--gray-200)', borderBottomLeftRadius:8 }}></div>
          <BOMNode node={c} level={level + 1} />
        </div>
      ))}
    </div>
  )
}
