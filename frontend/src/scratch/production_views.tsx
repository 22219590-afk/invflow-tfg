
// ── MPSView ───────────────────────────────────────────────────────────────────
function MPSView({ token, devMode }: any) {
  const [products, setProducts] = useState<Product[]>([])
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [mpsData, setMpsData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiFetch('/products', token).then(setProducts).catch(console.error)
  }, [token])

  const calculateMPS = () => {
    if (!selectedProduct) return
    setLoading(true)
    apiFetch(`/production/mps/${selectedProduct.odoo_id}`, token)
      .then(data => { setMpsData(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  return (
    <div className="animate-in">
      <div className="view-header">
        <div>
          <h2 className="view-title">Plan Maestro de Producción (MPS)</h2>
          <p className="view-subtitle">Optimización de producción y niveles de inventario</p>
        </div>
        <button className="btn btn-primary" onClick={calculateMPS} disabled={!selectedProduct || loading}>
          {loading ? <RefreshCw className="rotate-slow" size={16} /> : <Play size={16} />} 
          <span style={{marginLeft: 8}}>Calcular Plan Óptimo</span>
        </button>
      </div>

      <div className="sim-layout" style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 24, marginTop: 24 }}>
        <div className="panel" style={{ background: 'white', padding: 20, borderRadius: 16, border: '1px solid var(--border)' }}>
          <h4 style={{ marginBottom: 16, fontSize: '0.9rem', color: 'var(--gray-500)' }}>Seleccionar Producto Terminado</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '60vh', overflowY: 'auto' }}>
            {products.map(p => (
              <button 
                key={p.id} 
                className={`nav-item ${selectedProduct?.id === p.id ? 'active' : ''}`}
                style={{ textAlign: 'left', padding: '10px 14px', borderRadius: 10, fontSize: '0.85rem' }}
                onClick={() => setSelectedProduct(p)}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>

        <div className="panel" style={{ background: 'white', padding: 24, borderRadius: 16, border: '1px solid var(--border)' }}>
          {!mpsData ? (
            <div style={{ textAlign: 'center', padding: 100, color: 'var(--gray-400)' }}>
              <Layers size={48} style={{ opacity: 0.2, marginBottom: 16 }} />
              <p>Selecciona un producto y lanza el cálculo para ver el MPS</p>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 32, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{selectedProduct?.name}</h3>
                  <span className="badge badge-info" style={{marginTop: 8}}>Coste Total Plan: {mpsData.total_cost}€</span>
                </div>
              </div>

              <div style={{ height: 250, marginBottom: 40 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={mpsData.plan}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="period_start" tickFormatter={d => new Date(d).toLocaleDateString('es-ES', {month:'short'})} axisLine={false} tickLine={false} tick={{fontSize: 11}} />
                    <YAxis axisLine={false} tickLine={false} tick={{fontSize: 11}} />
                    <Tooltip />
                    <Bar dataKey="planned_qty" fill="#3b82f6" name="Prod. Planificada" radius={[4, 4, 0, 0]} />
                    <Line type="monotone" dataKey="projected_inventory" stroke="#10b981" strokeWidth={2} name="Stock Proyectado" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <table className="data-table">
                <thead>
                  <tr>
                    <th>PERIODO (MES)</th>
                    <th>PROD. PLANIFICADA</th>
                    <th>STOCK PROYECTADO</th>
                    <th>COSTE PROD.</th>
                    <th>COSTE ALMACÉN</th>
                  </tr>
                </thead>
                <tbody>
                  {mpsData.plan.map((r: any, i: number) => (
                    <tr key={i}>
                      <td style={{fontWeight: 600}}>{new Date(r.period_start).toLocaleDateString('es-ES', {month:'long', year:'numeric'})}</td>
                      <td style={{color: 'var(--primary)', fontWeight: 700}}>{r.planned_qty}</td>
                      <td>{r.projected_inventory}</td>
                      <td style={{color: 'var(--gray-400)'}}>{r.cost_production}€</td>
                      <td style={{color: 'var(--gray-400)'}}>{r.cost_holding}€</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── ProductionMRPView ──────────────────────────────────────────────────────────
function ProductionMRPView({ token }: any) {
  const [products, setProducts] = useState<Product[]>([])
  const [selectedParent, setSelectedParent] = useState<Product | null>(null)
  const [mrpResults, setMrpResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiFetch('/products', token).then(setProducts).catch(console.error)
  }, [token])

  const explodeMRP = () => {
    if (!selectedParent) return
    setLoading(true)
    apiFetch(`/production/mrp/${selectedParent.odoo_id}`, token)
      .then(data => { setMrpResults(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  return (
    <div className="animate-in">
      <div className="view-header">
        <div>
          <h2 className="view-title">MRP – Planificación de Materiales</h2>
          <p className="view-subtitle">Cálculo de necesidades netas por explosión de BOM</p>
        </div>
        <button className="btn btn-primary" onClick={explodeMRP} disabled={!selectedParent || loading}>
          <Activity size={16} /> 
          <span style={{marginLeft: 8}}>Explosionar BOM</span>
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 24, marginTop: 24 }}>
        <div className="panel" style={{ background: 'white', padding: 20, borderRadius: 16, border: '1px solid var(--border)' }}>
          <h4 style={{ marginBottom: 16, fontSize: '0.9rem', color: 'var(--gray-500)' }}>Producto con MPS Activo</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {products.map(p => (
              <button 
                key={p.id} 
                className={`nav-item ${selectedParent?.id === p.id ? 'active' : ''}`}
                style={{ textAlign: 'left', padding: '10px 14px', borderRadius: 10 }}
                onClick={() => setSelectedParent(p)}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>

        <div className="panel" style={{ background: 'white', padding: 24, borderRadius: 16, border: '1px solid var(--border)' }}>
          {mrpResults.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 100, color: 'var(--gray-400)' }}>
              <Activity size={48} style={{ opacity: 0.2, marginBottom: 16 }} />
              <p>Lanza la explosión para ver los requerimientos de componentes</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>
              {mrpResults.map((res, i) => (
                <div key={i}>
                  <h4 style={{ marginBottom: 16, color: 'var(--gray-800)', borderLeft: '4px solid var(--primary)', paddingLeft: 12 }}>
                    Componente: {res.component_name}
                  </h4>
                  <div style={{overflowX: 'auto'}}>
                    <table className="data-table" style={{fontSize: '0.75rem'}}>
                      <thead>
                        <tr>
                          <th>FECHA</th>
                          <th>NEC. BRUTAS</th>
                          <th>REC. PROGRAMADAS</th>
                          <th>STOCK PROYECTADO</th>
                          <th>NEC. NETAS</th>
                          <th>LANZAMIENTO ORD.</th>
                        </tr>
                      </thead>
                      <tbody>
                        {res.mrp.map((row: any, j: number) => (
                          <tr key={j}>
                            <td>{new Date(row.date).toLocaleDateString()}</td>
                            <td style={{fontWeight: 700}}>{row.gross_requirement}</td>
                            <td style={{color: 'var(--primary)'}}>{row.scheduled_receipt}</td>
                            <td style={{background: '#f8fafc'}}>{row.projected_available}</td>
                            <td style={{color: 'var(--danger)', fontWeight: 800}}>{row.net_requirement}</td>
                            <td style={{background: 'rgba(59, 130, 246, 0.05)', color: 'var(--primary)', fontWeight: 700}}>{row.planned_order_release}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
