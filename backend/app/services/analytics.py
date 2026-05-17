import math
import random
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.models.models import Product, StockMove, StockQuant, AppConfig

# Fallback Z-score lookup
# Tabla Z exacta según requerimiento industrial
Z_SCORES = {
    "99.99": 3.72,
    "99.87": 3.01,
    "99.0": 2.33,
    "97.0": 1.88,
    "95.0": 1.65,
    "90.0": 1.28,
    "85.0": 1.04,
}

def get_z_value(service_level: float) -> float:
    """Implementación de la función get_z_value con equivalencia exacta."""
    # Intentar match directo
    sl_str = f"{service_level:.2f}" if service_level < 99.9 else f"{service_level}"
    # Redondeo simple para buscar en la tabla si no hay match exacto
    if service_level >= 99.99: return 3.72
    if service_level >= 99.87: return 3.01
    if service_level >= 99.0: return 2.33
    if service_level >= 97.0: return 1.88
    if service_level >= 95.0: return 1.65
    if service_level >= 90.0: return 1.28
    if service_level >= 85.0: return 1.04
    return 1.65 # Default 95%

def get_z_score(service_level: Optional[float], default_val: str) -> float:
    """Calculate Z-score using scipy or fallback map."""
    try:
        from scipy.stats import norm
        sl = float(service_level) if service_level is not None else float(default_val)
        # Fix potential user typos like 9895 instead of 98.95
        if sl > 100:
            # Maybe they missed a decimal point
            while sl > 100:
                sl = sl / 10.0
        if sl >= 100: sl = 99.99
        if sl <= 0: sl = 50.0
        
        z = float(norm.ppf(sl / 100.0))
        if math.isnan(z) or math.isinf(z):
            raise ValueError("NaN/Inf Z-score")
        return z
    except Exception:
        # Fallback to Z_SCORES map
        # Check if the float string exists directly, else default
        key = str(service_level) if service_level else str(default_val)
        return Z_SCORES.get(key, Z_SCORES.get(str(int(float(key))), 1.645))

DEFAULT_CONFIG = {
    "service_level_a": "95",
    "service_level_b": "90",
    "service_level_c": "85",
    "review_period_b_days": "14",
    "abc_threshold_a": "0.80",
    "abc_threshold_b": "0.95",
    "lead_time_default_days": "7",
    "ordering_cost": "50.0",
    "holding_rate": "0.15",
    "working_days_per_year": "240",
}


def _get_config(session: Session) -> Dict[str, str]:
    from app.models.models import AppConfig
    rows = session.exec(select(AppConfig)).all()
    cfg = dict(DEFAULT_CONFIG)
    for r in rows:
        cfg[r.key] = r.value
    return cfg


def get_status(current_stock: float, min_stock: float, max_stock: float) -> str:
    if current_stock <= 0:
        return "Stockout"
    elif current_stock < min_stock:
        return "Reorder"
    elif current_stock > max_stock:
        return "Overstock"
    return "OK"


def compute_policy(
    abc_class: str,
    daily_demand: float,
    demand_std_dev: float,
    lead_time: int,
    cfg: Dict[str, str],
    product_service_level: Optional[float] = None,
    standard_price: float = 0.0,
    current_stock: float = 0.0,
    annual_consumption: float = 0.0,
) -> Dict[str, float]:
    """
    RECONSTRUCCIÓN POLÍTICA CLASE A:
    - d = D_anual / 240
    - SS = Z * sigma * sqrt(LT)
    - MIN = (d * LT) + SS (Punto de Pedido)
    - MAX = MIN + EOQ
    - H = S
    """
    L = max(lead_time, 1)
    d = daily_demand
    sigma = demand_std_dev
    
    working_days = int(cfg.get("working_days_per_year", 240))
    S = float(cfg.get("ordering_cost", 50.0))
    D_annual = annual_consumption
    
    # 1. Z-Score (Default 99.0% según req)
    sl = product_service_level if product_service_level is not None else 99.0
    z = get_z_value(sl)

    # 2. EOQ (Solo A y B)
    if abc_class in ["A", "B"]:
        H = S 
        eoq_raw = np.sqrt((2 * S * D_annual) / H) if D_annual > 0 else 0.0
        eoq = float(np.ceil(eoq_raw))
    else:
        eoq = 0.0
    
    # 3. Stock de Seguridad (SS)
    # SS = Z * sigma * sqrt(LT)
    ss = np.ceil(z * sigma * np.sqrt(L))
    
    # 4. Punto de Pedido (MIN)
    # MIN = (d * LT) + SS
    rop = np.ceil(d * L) + ss
    
    # 5. Lógica por Clase
    if abc_class == "A":
        max_stock = rop + eoq
    elif abc_class == "B":
        # REGLA CLASE B: REVISIÓN PERIÓDICA (T, S)
        V_anual = D_annual
        Co = S
        Ch = S # SEGÚN REQUERIMIENTO: Ch = Co
        
        # Sigma fallback para B: 1 si es 0
        sigma_b = sigma if sigma > 0 else 1.0
        
        # Periodo de Revisión (R en años) = sqrt((2 * Co) / (V_anual * Ch))
        # Si Ch = Co -> sqrt(2 / V_anual)
        r_years = np.sqrt(2 / V_anual) if V_anual > 0 else 0.0
        r_days = max(int(round(r_years * working_days)), 1)
        
        # Stock de seguridad (SS) = Z * sigma * sqrt(L + R_dias)
        ss = np.ceil(z * sigma_b * np.sqrt(L + r_days))
        
        # Stock máximo (S) = SS + D * (L + R_dias)
        target_s = ss + np.ceil(d * (L + r_days))
        
        max_stock = target_s
        rop = ss 
        t_days = r_days
        sigma = sigma_b # Para trazabilidad
    else: # C: Bajo Demanda
        max_stock = 0.0
        ss = ss # Mantener ss_cont
        t_days = 0
    
    # 6. Recomendación
    if abc_class == "A":
        rec_qty = eoq if current_stock <= rop else 0.0
    elif abc_class == "B":
        rec_qty = max(max_stock - current_stock, 0.0)
    else:
        rec_qty = max(ss * 2 - current_stock, 0.0) if current_stock < ss else 0.0

    # 7. Costes Financieros (Auditables)
    raw_cp = (D_annual / eoq * S) if eoq > 0 else 0.0
    raw_ca = (eoq / 2 * S) if eoq > 0 else 0.0
    ct_total = raw_cp + raw_ca

    return {
        "eoq": eoq,
        "reorder_point": float(rop),
        "safety_stock": float(ss),
        "min_stock": float(rop),
        "max_stock": float(max_stock),
        "recommended_qty": float(np.ceil(rec_qty)),
        "z_value": z,
        "sigma": sigma,
        "d_diaria": d,
        "d_anual": D_annual,
        "lt": L,
        "num_orders_year": float(round(D_annual / eoq, 2)) if eoq > 0 else 0.0,
        "cost_order": float(round(raw_cp, 2)),
        "cost_holding": float(round(raw_ca, 2)),
        "cost_total": float(round(ct_total, 2)),
        "review_period": t_days if abc_class == "B" else 0,
        "target_stock_level": max_stock if abc_class in ["A", "B"] else 0.0
    }


class AnalyticsService:
    def __init__(self, session: Session):
        self.session = session

    def calculate_product_policy(self, product: Product, cfg: Optional[Dict[str, str]] = None):
        """Update a single product's stock policy results."""
        if not cfg:
            cfg = _get_config(self.session)
        
        # Determine daily demand and std_dev (use manual overrides if set)
        if product.manual_daily_demand is not None:
            d = product.manual_daily_demand
            sigma = product.manual_demand_std_dev or 0.0
        else:
            d = product.daily_demand or 0.0
            sigma = product.demand_std_dev or 0.0
            
        product.daily_demand = d
        product.demand_std_dev = sigma
        product.cv = (sigma / d) if d > 0 else 0.0
        
        # 1. Calcular Demanda Real desde SaleOrderLine (Últimos 12 meses o actual)
        from app.models.models import SaleOrderLine
        from sqlalchemy import func
        
        # Rango: últimos 365 días
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        cutoff = max(datetime(2025, 1, 1), one_year_ago)
        
        sales = self.session.exec(
            select(SaleOrderLine)
            .where(SaleOrderLine.product_id == product.odoo_id)
            .where(SaleOrderLine.state.in_(["sale", "done"]))
            .where(SaleOrderLine.date >= cutoff)
        ).all()

        total_qty = sum(s.product_uom_qty for s in sales)
        
        # d = D_anual / 240
        d_diaria = total_qty / 240.0
        
        # Calcular Sigma (Desviación Típica Real Diaria)
        if len(sales) > 5:
            # Agrupar por día para obtener demanda diaria real
            daily_series = {}
            curr = cutoff
            while curr <= now:
                daily_series[curr.date()] = 0.0
                curr += timedelta(days=1)
            
            for s in sales:
                dt = s.date.date()
                daily_series[dt] = daily_series.get(dt, 0.0) + s.product_uom_qty
            
            sigma_real = np.std(list(daily_series.values()))
        else:
            # Fallback solicitado: 9 si no hay histórico
            sigma_real = 9.0

        product.daily_demand = d_diaria
        product.demand_std_dev = sigma_real
        product.cv = (sigma_real / d_diaria) if d_diaria > 0 else 0.0

        current_stock = sum(q.quantity for q in product.quants)
        L = product.lead_time_days if product.lead_time_days else int(cfg.get("lead_time_default_days", 7))
        
        eff_policy = product.stock_policy_override or product.abc_class or "C"
        
        policy = compute_policy(
            eff_policy, d_diaria, sigma_real, L, cfg, 
            product_service_level=product.target_service_level,
            standard_price=product.standard_price,
            current_stock=current_stock,
            annual_consumption=total_qty
        )
        
        product.safety_stock = policy["safety_stock"]
        product.min_stock = policy["min_stock"]
        product.max_stock = policy["max_stock"]
        product.eoq = policy["eoq"]
        product.recommended_qty = policy["recommended_qty"]
        product.z_value = policy["z_value"]
        product.annual_demand = policy["d_anual"]
        product.num_orders_year = policy["num_orders_year"]
        product.cost_order = policy["cost_order"]
        product.cost_holding = policy["cost_holding"]
        product.cost_total = policy["cost_total"]
        product.review_period = policy["review_period"]
        product.target_stock_level = policy["target_stock_level"]
        
        # Debug console para auditoría (Requerimiento 10)
        print(f"\n[AUDITORÍA POLÍTICA] Producto: {product.name} ({product.default_code})")
        print(f" - Política Anterior: {product.stock_policy_override or 'N/A'} -> Nueva: {eff_policy}")
        print(f" - Parámetros: d={d_diaria:.2f}, σ={sigma_real:.2f}, Z={policy['z_value']}, L={L}")
        print(f" - Resultados: SS={policy['safety_stock']}, MIN={policy['min_stock']}, MAX={policy['max_stock']}, EOQ={policy['eoq']}")
        print(f" - Stock: Actual={current_stock}, Pendiente={product.incoming_qty}")
        print("-" * 60)

    def calculate_abc_xyz(self):
        """
        RECONSTRUCCIÓN COMPLETA: Cálculo ABC basado en Ventas Reales (sale.order.line).
        - Fuente: SaleOrderLine (confirmadas/hechas)
        - Periodo: 2025-2026
        - Impacto Económico: Σ(precio_subtotal)
        - Excluye: stock.move, datos sintéticos, borradores.
        """
        cfg = _get_config(self.session)
        products = self.session.exec(select(Product)).all()
        if not products: return

        # Filtro Temporal: Año actual (2026) y Año anterior (2025)
        cutoff_date = datetime(2025, 1, 1)
        
        # 1. Obtener líneas de venta reales (Solo confirmadas/hechas)
        from app.models.models import SaleOrderLine
        sales = self.session.exec(
            select(SaleOrderLine)
            .where(SaleOrderLine.state.in_(["sale", "done"]))
            .where(SaleOrderLine.date >= cutoff_date)
        ).all()

        # 2. Agrupar por producto y calcular impacto económico
        product_stats = []
        for p in products:
            p_sales = [s for s in sales if s.product_id == p.odoo_id]
            # Cambio solicitado: Cantidad × Precio Unitario (ignorar descuentos/subtotales de Odoo)
            total_value = sum(s.product_uom_qty * s.price_unit for s in p_sales)
            total_qty = sum(s.product_uom_qty for s in p_sales)
            num_orders = len(set(s.order_id for s in p_sales))
            
            min_date = min(s.date for s in p_sales) if p_sales else None
            max_date = max(s.date for s in p_sales) if p_sales else None

            product_stats.append({
                "odoo_id": p.odoo_id,
                "name": p.name,
                "value": total_value,
                "qty": total_qty,
                "orders": num_orders,
                "min_date": min_date.strftime("%Y-%m-%d") if min_date else "-",
                "max_date": max_date.strftime("%Y-%m-%d") if max_date else "-"
            })

        df_abc = pd.DataFrame(product_stats)
        if df_abc.empty or df_abc["value"].sum() == 0:
            print("ABC Debug: No se encontraron ventas reales en el periodo 2025-2026.")
            return

        # 3. Clasificación Pareto (80/15/5) - Orden DESCENDENTE
        df_abc = df_abc.sort_values("value", ascending=False).reset_index(drop=True)
        total_revenue = df_abc["value"].sum()
        
        df_abc["pct"] = df_abc["value"] / total_revenue
        df_abc["cum_pct"] = df_abc["pct"].cumsum()

        thr_a = float(cfg.get("abc_threshold_a", 0.80))
        thr_b = float(cfg.get("abc_threshold_b", 0.95))

        # DEBUG OBLIGATORIO (Validación Excel/Odoo)
        print("\n" + "="*120)
        print(" RECONSTRUCCIÓN ABC: INFORME DE VENTAS REALES (sale.order.line 2025-2026)")
        print("-" * 120)
        print(f"{'PRODUCTO':<40} | {'VENTAS €':>12} | {'%':>7} | {'ACUM':>7} | {'CLASE'} | {'PEDIDOS'} | {'RANGO FECHAS'}")
        print("-" * 120)

        abc_map = {}
        for idx, row in df_abc.iterrows():
            # Lógica estricta de Pareto: El acumulado JAMÁS debe superar el umbral
            # (Excepto para el primer producto si ya supera el 80%)
            cum = row["cum_pct"]
            if cum <= thr_a or idx == 0:
                clase = "A"
            elif cum <= thr_b:
                clase = "B"
            else:
                clase = "C"
            
            abc_map[row["odoo_id"]] = clase
            
            print(f"{row['name'][:40]:<40} | {row['value']:>12.2f} | {row['pct']*100:>6.1f}% | {row['cum_pct']*100:>6.1f}% | {clase:^5} | {row['orders']:>7.0f} | {row['min_date']} a {row['max_date']}")

        print("-" * 120)
        print(f"TOTAL VENTAS PERIODO: {total_revenue:,.2f} €")
        print("="*120 + "\n")

        # 4. Actualizar clasificación y políticas
        for p in products:
            new_abc = abc_map.get(p.odoo_id)
            if new_abc:
                p.abc_class = new_abc
            elif not p.abc_class:
                p.abc_class = "C" # Default only if nothing existed
            
            # XYZ se mantiene basado en CV histórico (calculado por ForecastEngine)
            cv = p.cv or 0.0
            if cv < 0.2: p.xyz_class = "X"
            elif cv < 0.5: p.xyz_class = "Y"
            else: p.xyz_class = "Z"
            
            self.calculate_product_policy(p, cfg)

        self.session.commit()




    def simulate_scenario(
        self,
        product_ids: List[int],
        demand_delta_pct: float = 0.0,
        lead_time_override: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Stateless simulation — returns new policy values without writing to DB."""
        cfg = _get_config(self.session)
        results = []

        for pid in product_ids:
            p = self.session.exec(select(Product).where(Product.odoo_id == pid)).first()
            if not p:
                continue

            sim_demand = p.daily_demand * (1 + demand_delta_pct / 100.0)
            sim_std = p.demand_std_dev * (1 + abs(demand_delta_pct) / 100.0)
            sim_lead = lead_time_override if lead_time_override is not None else p.lead_time_days

            policy = compute_policy(
                p.abc_class or "C", sim_demand, sim_std, sim_lead, cfg,
                product_service_level=p.target_service_level
            )
            current_stock = sum(q.quantity for q in p.quants)
            # TFG Audit Fix: Map policy keys correctly for get_status
            new_status = get_status(current_stock, policy["reorder_point"], policy["target_stock_level"])

            results.append({
                "product_id": p.odoo_id,
                "name": p.name,
                "abc_class": p.abc_class,
                "current_stock": current_stock,
                "sim_daily_demand": round(sim_demand, 4),
                "new_min_stock": policy["reorder_point"],
                "new_max_stock": policy["target_stock_level"],
                "new_safety_stock": policy["safety_stock_continuous"],
                "new_recommended_qty": policy["recommended_qty"],
                "new_status": new_status,
                "original_status": get_status(current_stock, p.min_stock, p.max_stock),
            })

        return results



    def sync_product_stock_from_odoo(self, product: Product):
        """Fetch fresh stock levels for a single product from Odoo (Immediate Update)."""
        from app.services.odoo_connector import OdooConnector
        from app.models.models import StockQuant
        from sqlalchemy import delete
        
        try:
            connector = OdooConnector.from_config(self.session)
            connector.login()
            
            # 1. Fetch product data (qty_available, virtual_available)
            odoo_p = connector.models.execute_kw(
                connector.db, connector.uid, connector.password, 
                'product.product', 'read', [[product.odoo_id], ['qty_available', 'virtual_available']]
            )
            if not odoo_p: return
            
            p_data = odoo_p[0]
            hand = float(p_data.get('qty_available', 0.0))
            virt = float(p_data.get('virtual_available', 0.0))
            
            # 2. Update incoming_qty (Combining PO lines and Shipments)
            pending_map = connector.get_pending_purchases()
            incoming_shipments = connector.get_incoming_shipments()
            
            po_pending = pending_map.get(product.odoo_id, 0.0)
            shipment_pending = incoming_shipments.get(product.odoo_id, 0.0)
            pending = max(po_pending, shipment_pending)
            
            if pending <= 0:
                pending = max(0.0, virt - hand)
            
            # LOG DE TRANSICIÓN STOCK (Requerimiento 9)
            print(f"[STOCK-AUDIT] Producto: {product.name} | Odoo Hand: {hand} | Odoo Virt: {virt} | Calculado Pending: {pending}")
            if product.incoming_qty > 0 and pending == 0:
                print(f"[STOCK-AUDIT] RECEPCIÓN DETECTADA: Cantidad {product.incoming_qty} ya disponible en stock real.")
            
            product.incoming_qty = pending
            product.reserved_quantity = max(0.0, hand - virt)
            
            # 3. Update StockQuants (Internal stock)
            # Clear old quants for this product
            self.session.exec(delete(StockQuant).where(StockQuant.product_id == product.odoo_id))
            
            # Fetch fresh quants from Odoo
            domain = [('product_id', '=', product.odoo_id), ('quantity', '>', 0)]
            odoo_quants = connector.models.execute_kw(
                connector.db, connector.uid, connector.password, 
                'stock.quant', 'search_read', [domain, ['location_id', 'quantity']]
            )
            
            for q in odoo_quants:
                self.session.add(StockQuant(
                    odoo_id=q['id'],
                    product_id=product.odoo_id,
                    location_id=q['location_id'][0] if isinstance(q['location_id'], list) else q['location_id'],
                    quantity=q['quantity']
                ))
            
            self.session.commit()
            print(f"[STOCK] Sync individual completado para {product.name}. Stock actual: {hand}")
            
        except Exception as e:
            print(f"[STOCK] Error en sync individual: {e}")
            self.session.rollback()

    def get_kpis(self, period_days: int = 30) -> Dict[str, Any]:
        from app.models.models import SaleOrderLine

        products = self.session.exec(select(Product)).all()
        quants   = self.session.exec(select(StockQuant)).all()
        moves    = self.session.exec(select(StockMove)).all()

        # ── Stock map (product.odoo_id → total qty) ───────────────────────────
        stock_map: Dict[int, float] = {}
        for q in quants:
            stock_map[q.product_id] = stock_map.get(q.product_id, 0) + q.quantity

        # ── 1. INVENTORY VALUE — identical to Odoo: Σ(qty × standard_price) ──
        # Odoo → Informes → Stock → Valor de inventario uses:
        #   stock.valuation.layer: qty_remaining * unit_cost
        # which for FIFO/AVCO at company level equals Σ(qty_on_hand × standard_price).
        # We replicate this exactly using stock_quant.quantity × product.standard_price.
        total_value = sum(
            stock_map.get(p.odoo_id, 0.0) * max(p.standard_price or 0.0, 0.0)
            for p in products
        )

        # ── 2. Below min stock ────────────────────────────────────────────────
        below_min      = [p for p in products if stock_map.get(p.odoo_id, 0) < p.min_stock]
        items_below_min = len(below_min)

        # ── 3. Stockout risk ──────────────────────────────────────────────────
        stockouts    = [p for p in products if stock_map.get(p.odoo_id, 0) <= 0]
        stockout_pct = (len(stockouts) / len(products) * 100) if products else 0.0

        # ── 4. SERVICE LEVEL — 1 - (late_orders / total_orders) ───────────────
        # Formula: Nivel servicio = 1 - (órdenes atrasadas / órdenes totales)
        # Source: SaleOrderLine confirmed or done in the period.
        # "Late" = order has an expected_date and actual delivery is after it.
        # We use StockMove (done, outgoing) linked to the sale to check delivery date.
        now          = datetime.utcnow()
        period_start = now - timedelta(days=period_days)
        prev_period_start = now - timedelta(days=period_days * 2)

        def calc_service_level(start_date, end_date):
            # Count confirmed orders in period
            sale_lines_period = self.session.exec(
                select(SaleOrderLine)
                .where(SaleOrderLine.state.in_(["sale", "done"]))
                .where(SaleOrderLine.date >= start_date)
                .where(SaleOrderLine.date < end_date)
            ).all()

            total_orders = len(sale_lines_period)
            if total_orders == 0:
                return 0.0, 0, 0

            # "Late" = stock move for this order line arrived after expected_date
            # Since we don't have a direct order_line → move link, we use moves in period
            # where move has expected_date and was done AFTER that expected_date.
            late_moves = [
                m for m in moves
                if start_date <= m.date < end_date
                and m.state == "done"
                and m.move_type == "out"
                and m.expected_date is not None
                and m.date > m.expected_date
            ]
            late_orders = len(late_moves)
            svc = max(0.0, (1.0 - late_orders / total_orders) * 100)
            return round(svc, 2), late_orders, total_orders

        svc_level,     late_c, total_orders = calc_service_level(period_start, now)
        prev_svc_level, prev_late, _        = calc_service_level(prev_period_start, period_start)

        SERVICE_LEVEL_TARGET = 99.0  # %

        # ── 5. OTIF (kept for reference, shown as Late Cliente) ───────────────
        def calc_otif_metrics(start_date, end_date):
            l_co = 0; l_po = 0; total_del = 0; on_time_del = 0
            for m in moves:
                if not (start_date <= m.date < end_date): continue
                is_outgoing = m.move_type == "out" and m.state == "done"
                is_incoming = m.move_type == "in"  and m.state == "done"
                if is_outgoing:
                    total_del += 1
                    if m.expected_date and m.date > m.expected_date: l_co += 1
                    else: on_time_del += 1
                elif is_incoming:
                    if m.expected_date and m.date > m.expected_date: l_po += 1
            otif = (on_time_del / total_del * 100) if total_del > 0 else 0.0
            return l_co, l_po, otif

        late_c_otif, late_p, otif_pct      = calc_otif_metrics(period_start, now)
        prev_lc_otif, prev_lp, prev_otif   = calc_otif_metrics(prev_period_start, period_start)

        # ── 6. Turnover ───────────────────────────────────────────────────────
        total_demand_period = sum(
            m.product_uom_qty for m in moves
            if period_start <= m.date < now and m.move_type == "out" and m.state == "done"
        )
        prev_total_demand = sum(
            m.product_uom_qty for m in moves
            if prev_period_start <= m.date < period_start and m.move_type == "out" and m.state == "done"
        )
        avg_stock = max(sum(stock_map.values()), 1.0)
        turnover      = total_demand_period / avg_stock
        prev_turnover = prev_total_demand   / avg_stock

        # ── 7. Previous period inventory (reconstructed) ───────────────────────
        prev_stock_map = dict(stock_map)
        for m in moves:
            if period_start <= m.date < now:
                if m.move_type == "in":
                    prev_stock_map[m.product_id] = prev_stock_map.get(m.product_id, 0.0) - m.product_uom_qty
                elif m.move_type == "out":
                    prev_stock_map[m.product_id] = prev_stock_map.get(m.product_id, 0.0) + m.product_uom_qty

        prev_total_value    = sum(max(prev_stock_map.get(p.odoo_id, 0.0), 0.0) * max(p.standard_price or 0.0, 0.0) for p in products)
        prev_items_below_min = len([p for p in products if prev_stock_map.get(p.odoo_id, 0.0) < p.min_stock])
        prev_stockout_pct   = (len([p for p in products if prev_stock_map.get(p.odoo_id, 0.0) <= 0]) / len(products) * 100) if products else 0.0

        # ── 8. Coverage ───────────────────────────────────────────────────────
        avg_daily_demand = sum(p.daily_demand for p in products)
        coverage      = (sum(stock_map.values()) / avg_daily_demand) if avg_daily_demand > 0 else 0.0
        prev_coverage = (sum(prev_stock_map.values()) / avg_daily_demand) if avg_daily_demand > 0 else 0.0

        # ── Helpers ───────────────────────────────────────────────────────────
        def get_trend(curr, prev):
            if not prev or prev == 0: return 0.0
            return round(((curr - prev) / prev) * 100, 1)

        def clean(val):
            if val is None or math.isnan(val) or math.isinf(val): return 0.0
            return float(round(val, 2))

        return {
            # ── Inventory value (Odoo-identical) ─────────────────────────────
            "total_value":       clean(total_value),
            "total_value_trend": get_trend(total_value, prev_total_value),

            # ── Service level: 1 - (late/total) ─────────────────────────────
            "service_level":        clean(svc_level),
            "service_level_target": SERVICE_LEVEL_TARGET,
            "service_level_trend":  get_trend(svc_level, prev_svc_level),
            "late_orders":          int(late_c),
            "total_orders":         int(total_orders),

            # ── OTIF (kept as reference) ──────────────────────────────────────
            "otif_pct":       clean(otif_pct),
            "otif_pct_trend": get_trend(otif_pct, prev_otif),

            # ── Other KPIs ────────────────────────────────────────────────────
            "items_below_min":       int(items_below_min),
            "items_below_min_trend": get_trend(items_below_min, prev_items_below_min),

            "stockout_pct":       clean(stockout_pct),
            "stockout_pct_trend": get_trend(stockout_pct, prev_stockout_pct),

            "late_c":       int(late_c_otif),
            "late_c_trend": get_trend(late_c_otif, prev_lc_otif),

            "late_p":       int(late_p),
            "late_p_trend": get_trend(late_p, prev_lp),

            "turnover":       clean(turnover),
            "turnover_trend": get_trend(turnover, prev_turnover),

            "coverage":       clean(coverage),
            "coverage_trend": get_trend(coverage, prev_coverage),
        }

    def get_products_enriched_single(self, product_id: int) -> Dict[str, Any]:
        """Return a single product with current stock, status, and all fields."""
        p = self.session.exec(select(Product).where(Product.id == product_id)).first()
        if not p: return {}
        
        quants = self.session.exec(select(StockQuant).where(StockQuant.product_id == p.odoo_id)).all()
        cs = sum(q.quantity for q in quants)
        
        def safe_float(val: Any) -> float:
            if val is None: return 0.0
            try:
                f_val = float(val)
                return 0.0 if (math.isnan(f_val) or math.isinf(f_val)) else f_val
            except (ValueError, TypeError):
                return 0.0

        return {
            "id": p.id,
            "odoo_id": p.odoo_id,
            "name": p.name,
            "default_code": p.default_code,
            "current_stock": round(cs, 2),
            "min_stock": safe_float(p.min_stock),
            "max_stock": safe_float(p.max_stock),
            "target_stock_level": safe_float(p.target_stock_level),
            "safety_stock": safe_float(p.safety_stock),
            "safety_stock_continuous": safe_float(p.safety_stock_continuous),
            "safety_stock_periodic": safe_float(p.safety_stock_periodic),
            "eoq": safe_float(p.eoq),
            "num_orders_year": safe_float(p.num_orders_year),
            "reorder_point": safe_float(p.min_stock),
            "review_period": p.review_period,
            "last_order_date": p.last_order_date.strftime("%Y-%m-%d") if p.last_order_date else None,
            "daily_demand": round(safe_float(p.daily_demand), 4),
            "lead_time_days": p.lead_time_days,
            "abc_class": p.abc_class or "-",
            "xyz_class": p.xyz_class or "-",
            "stock_policy_override": p.stock_policy_override,
            "status": get_status(cs, safe_float(p.min_stock), safe_float(p.max_stock)),
            "recommended_qty": safe_float(p.recommended_qty),
            "list_price": safe_float(p.list_price),
            "standard_price": safe_float(p.standard_price),
            "supplier_id": p.supplier_id,
            "target_service_level": safe_float(p.target_service_level),
            "manual_daily_demand": safe_float(p.manual_daily_demand),
            "manual_demand_std_dev": safe_float(p.manual_demand_std_dev),
            "cost_order": safe_float(p.cost_order),
            "cost_holding": safe_float(p.cost_holding),
            "cost_total": safe_float(p.cost_total),
            "reserved_quantity": safe_float(p.reserved_quantity),
            "incoming_qty": safe_float(p.incoming_qty),
            "projected_stock": round(safe_float(cs + p.incoming_qty - (p.daily_demand * p.lead_time_days)), 2),
            "location_name": p.location_name,
            "category_name": p.category_name,
            "image_url": p.image_url,
            "description": p.description
        }

    def get_products_enriched(self) -> List[Dict[str, Any]]:
        """Return products with current stock, status, and all required frontend fields."""
        products = self.session.exec(select(Product)).all()
        quants = self.session.exec(select(StockQuant)).all()
        stock_map: Dict[int, float] = {}
        for q in quants:
            stock_map[q.product_id] = stock_map.get(q.product_id, 0) + q.quantity

        def safe_float(val: Any) -> float:
            if val is None: return 0.0
            try:
                f_val = float(val)
                return 0.0 if (math.isnan(f_val) or math.isinf(f_val)) else f_val
            except (ValueError, TypeError):
                return 0.0

        result = []
        for p in products:
            cs = stock_map.get(p.odoo_id, 0)
            result.append({
                "id": p.id,
                "odoo_id": p.odoo_id,
                "name": p.name,
                "default_code": p.default_code,
                "current_stock": round(cs, 2),
                "min_stock": safe_float(p.min_stock),
                "max_stock": safe_float(p.max_stock),
                "target_stock_level": safe_float(p.target_stock_level),
                "safety_stock": safe_float(p.safety_stock),
                "safety_stock_continuous": safe_float(p.safety_stock_continuous),
                "safety_stock_periodic": safe_float(p.safety_stock_periodic),
                "eoq": safe_float(p.eoq),
                "num_orders_year": safe_float(p.num_orders_year),
                "reorder_point": safe_float(p.min_stock),
                "review_period": p.review_period,
                "last_order_date": p.last_order_date.strftime("%Y-%m-%d") if p.last_order_date else None,
                "daily_demand": round(safe_float(p.daily_demand), 4),
                "lead_time_days": p.lead_time_days,
                "abc_class": p.abc_class or "-",
                "xyz_class": p.xyz_class or "-",
                "stock_policy_override": p.stock_policy_override,
                "status": get_status(cs, safe_float(p.min_stock), safe_float(p.max_stock)),
                "recommended_qty": safe_float(p.recommended_qty),
                "list_price": safe_float(p.list_price),
                "standard_price": safe_float(p.standard_price),
                "supplier_id": p.supplier_id,
                "target_service_level": safe_float(p.target_service_level),
                "manual_daily_demand": safe_float(p.manual_daily_demand),
                "manual_demand_std_dev": safe_float(p.manual_demand_std_dev),
                "cost_order": safe_float(p.cost_order),
                "cost_holding": safe_float(p.cost_holding),
                "cost_total": safe_float(p.cost_total),
                "reserved_quantity": safe_float(p.reserved_quantity),
                "incoming_qty": safe_float(p.incoming_qty),
                "projected_stock": round(safe_float(cs + p.incoming_qty - (p.daily_demand * p.lead_time_days)), 2),
                "location_name": p.location_name,
                "category_name": p.category_name,
                "image_url": p.image_url,
                "description": p.description
            })
        return result
