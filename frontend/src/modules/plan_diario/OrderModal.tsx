import { useState, useEffect } from 'react'
import { X, ShoppingBag, CheckCircle, AlertTriangle } from 'lucide-react'
import { apiFetch } from '../core/api'
import { Product } from '../core/types'

type OrderStatus = 'idle' | 'loading' | 'success' | 'error'

export default function OrderModal({ product, token, onClose, onSuccess }: {
  product: Product; token: string; onClose: () => void; onSuccess: (qty: number) => void
}) {
  const [partners, setPartners] = useState<any[]>([])
  const [selectedPartner, setSelectedPartner] = useState('')
  const [orderQty, setOrderQty] = useState(Math.ceil(product.recommended_qty || product.eoq || 10))
  const [status, setStatus] = useState<OrderStatus>('idle')
  const [rfqRef, setRfqRef] = useState<string>('')
  const [loadingPartners, setLoadingPartners] = useState(true)

  useEffect(() => {
    apiFetch('/odoo/partners', token)
      .then(parts => {
        setPartners(parts)
        if (parts.length > 0) setSelectedPartner(parts[0].id.toString())
        setLoadingPartners(false)
      })
      .catch(() => setLoadingPartners(false))
  }, [token])

  async function handleOrder() {
    if (!selectedPartner || orderQty <= 0) return
    setStatus('loading')
    try {
      const result = await apiFetch('/purchase-orders', token, {
        method: 'POST',
        body: JSON.stringify({
          partner_odoo_id: Number(selectedPartner),
          product_odoo_id: product.odoo_id,
          quantity: orderQty,
          price_unit: product.standard_price || 0,
        })
      })
      setRfqRef(result?.name || result?.id || 'RFQ generada')
      setStatus('success')
      setTimeout(() => onSuccess(orderQty), 2500)
    } catch (e: any) {
      setStatus('error')
    }
  }

  const sf = (v: any) => (v === null || v === undefined || isNaN(Number(v))) ? 0 : Number(v)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card animate-in-up" style={{ maxWidth: 460, width: '95vw' }} onClick={e => e.stopPropagation()}>
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 className="modal-title">Generar Pedido de Compra</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}><X size={20} /></button>
        </div>

        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Product Info */}
          <div style={{ background: '#f8fafc', borderRadius: 10, padding: '14px 16px', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Artículo</div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0f172a', marginTop: 4 }}>{product.name}</div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{product.default_code}</div>
            <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: '0.75rem', color: '#64748b' }}>
              <span>Stock: <strong>{sf(product.current_stock).toFixed(0)}</strong></span>
              <span>ROP: <strong>{sf(product.min_stock).toFixed(0)}</strong></span>
              <span>EOQ: <strong>{sf(product.eoq).toFixed(0)}</strong></span>
            </div>
          </div>

          {/* Success State */}
          {status === 'success' ? (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <CheckCircle size={48} color="#10b981" style={{ marginBottom: 12 }} />
              <div style={{ fontWeight: 700, fontSize: '1rem', color: '#0f172a' }}>Pedido Generado en Odoo</div>
              <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: 8 }}>Referencia: <strong>{rfqRef}</strong></div>
              <div style={{ fontSize: '0.75rem', color: '#f97316', marginTop: 8, fontWeight: 600 }}>
                ⏳ Stock pendiente de recepción: +{orderQty} uds
              </div>
            </div>
          ) : status === 'error' ? (
            <div style={{ background: '#fef2f2', borderRadius: 10, padding: 16, textAlign: 'center', border: '1px solid #fecaca' }}>
              <AlertTriangle size={24} color="#ef4444" style={{ marginBottom: 8 }} />
              <div style={{ fontWeight: 700, color: '#b91c1c', fontSize: '0.85rem' }}>Error al crear el pedido</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 4 }}>Verifica la conexión con Odoo en Configuración</div>
              <button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={() => setStatus('idle')}>Reintentar</button>
            </div>
          ) : (
            <>
              {/* Partner Select */}
              <div className="form-group">
                <label className="form-label">Proveedor</label>
                {loadingPartners ? (
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Cargando proveedores...</div>
                ) : partners.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: '#ef4444' }}>No hay proveedores en Odoo. Configura la conexión primero.</div>
                ) : (
                  <select className="form-input" value={selectedPartner} onChange={e => setSelectedPartner(e.target.value)}>
                    {partners.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                )}
              </div>

              {/* Qty */}
              <div className="form-group">
                <label className="form-label">
                  Cantidad a pedir
                  <span style={{ fontWeight: 400, color: '#94a3b8', marginLeft: 8, fontSize: '0.72rem' }}>
                    (recomendado: {sf(product.recommended_qty).toFixed(0)} uds)
                  </span>
                </label>
                <input type="number" className="form-input" min={1} value={orderQty} onChange={e => setOrderQty(Number(e.target.value))} />
              </div>

              {/* Pending stock info */}
              <div style={{ background: '#fff7ed', borderRadius: 8, padding: '10px 14px', border: '1px solid #fed7aa', fontSize: '0.75rem', color: '#92400e' }}>
                <strong>ℹ️ Stock pendiente recepción:</strong> Una vez confirmado, la cantidad quedará registrada como stock en tránsito (color naranja) hasta su recepción física en Odoo.
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 12 }}>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={onClose}>Cancelar</button>
                <button className="btn btn-primary" style={{ flex: 2 }} onClick={handleOrder}
                  disabled={status === 'loading' || !selectedPartner || orderQty <= 0}>
                  <ShoppingBag size={16} />
                  {status === 'loading' ? 'Generando RFQ...' : 'Confirmar Pedido'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
