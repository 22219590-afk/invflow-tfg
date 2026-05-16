# MANUAL FUNCIONAL DEL USUARIO — INVFLOW ERP

## 1. FLUJO DE TRABAJO INTEGRADO
InvFlow sigue un flujo circular de planificación industrial. Los datos fluyen desde la demanda histórica hasta la ejecución de compras.

### El Círculo de Planificación:
1.  **Sincronización**: Los datos de Odoo se importan para tener una base real de inventario y movimientos.
2.  **Previsión (Forecast)**: El sistema calcula cuánto se va a vender.
3.  **Plan Diario**: Se establecen niveles de stock óptimos y políticas de reposición.
4.  **Plan Maestro (MPS)**: Se optimiza la producción mensual y la plantilla.
5.  **Requerimientos (MRP)**: Se explotan las listas de materiales para saber qué comprar y cuándo.

---

## 2. MÓDULOS DEL SISTEMA: ENTRADAS Y SALIDAS

### 2.1 Dashboard Ejecutivo
- **Entradas**: Stock actual de Odoo, Previsiones calculadas, Alertas de sistema.
- **Salidas**: KPIs de rendimiento (Nivel de Servicio, Valor Almacén), Gráficos de tendencias, Alertas de prioridad.

### 2.2 Plan Diario (Inventario)
- **Entradas**: Historial de movimientos (ventas), Lead Times de proveedores.
- **Salidas**: Clasificación ABC, Cantidad de pedido sugerida (EOQ), Sugerencia de compra directa a Odoo.

### 2.3 Previsión (Forecast)
- **Entradas**: Serie histórica de salidas de almacén.
- **Salidas**: Pronóstico de demanda a 12 meses, nivel de precisión (MAPE).

### 2.4 Plan Maestro (MPS)
- **Entradas**: Forecast consolidado, Capacidad de planta, Costes de personal.
- **Salidas**: Plan de producción mensual, Proyección de inventario, Plan de contrataciones.

### 2.5 MRP (Material Requirements Planning)
- **Entradas**: Plan Maestro (MPS), Listas de Materiales (BOM), Lead Times de componentes.
- **Salidas**: Necesidades netas de materiales, Cronograma de lanzamientos de compra/fabricación.

---

## 3. GESTIÓN DE ALERTAS Y EXCEPCIONES
El sistema utiliza un código de colores industrial:
- **Rojo (Crítico)**: Rotura de stock inminente o retraso en pedido crítico.
- **Amarillo (Aviso)**: Stock por debajo del nivel de seguridad.
- **Verde (Óptimo)**: Niveles dentro de los parámetros de la política.

---

## 4. INTEGRACIÓN CON ODOO
Para sincronizar los datos:
1.  Vaya a **Configuración**.
2.  Verifique las credenciales de su instancia de Odoo.
3.  Pulse **"Sincronizar Datos ERP"**.
4.  El sistema actualizará Productos, BOMs, Movimientos y Almacenes de forma automática.
