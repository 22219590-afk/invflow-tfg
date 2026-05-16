# DICCIONARIO DE DATOS Y ESQUEMA — INVFLOW

## 1. TABLAS PRINCIPALES

### 1.1 Product (Producto)
Almacena la información maestra de los SKUs sincronizados de Odoo.
- `odoo_id`: ID original en el ERP (Clave primaria lógica).
- `name`: Nombre descriptivo.
- `default_code`: SKU / Referencia interna.
- `abc_class`: Categoría A, B o C según valor/movimiento.
- `daily_demand`: Media de consumo diario calculada.
- `safety_stock`: Stock de seguridad calculado o manual.
- `forecast_model`: Último modelo estadístico óptimo detectado.

### 1.2 BOM (Lista de Materiales)
Define la estructura de explosión para el MRP.
- `parent_id`: ID del producto padre.
- `child_id`: ID del componente.
- `quantity`: Cantidad necesaria por unidad de padre.

### 1.3 StockMove (Movimiento de Stock)
Historial de entradas y salidas para el motor de Forecast.
- `date`: Fecha del movimiento.
- `product_id`: Vínculo al producto.
- `product_uom_qty`: Cantidad movida.
- `move_type`: 'in' (entrada/producción) o 'out' (venta/salida).

### 1.4 ProductionPlan (MPS)
Resultados de la optimización del Plan Maestro.
- `period_start`: Mes de inicio.
- `planned_qty`: Cantidad a producir óptima.
- `projected_inventory`: Stock proyectado al final del periodo.
- `planned_workers`: Plantilla necesaria.

### 1.5 MRPRequirement (Necesidades Materiales)
Resultados de la explosión del MRP.
- `product_id`: Componente afectado.
- `date`: Fecha de la necesidad.
- `gross_requirement`: Necesidad bruta total.
- `net_requirement`: Necesidad neta tras descontar stock.
- `planned_order_release`: Cantidad y fecha recomendada de compra/lanzamiento.

---

## 2. CONFIGURACIÓN DEL SISTEMA (AppConfig)
Tabla clave-valor para parámetros globales:
- `odoo_url`: Dirección del ERP.
- `odoo_api_key`: Credencial de acceso.
- `horizon_mps`: Meses de planificación (def: 12).
- `service_level`: Nivel de servicio objetivo (ej: 0.95).
