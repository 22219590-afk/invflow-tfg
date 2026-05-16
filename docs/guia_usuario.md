# Guía de Usuario - InvFlow

Bienvenido a **InvFlow**, tu herramienta para la optimización inteligente de inventarios con integración Odoo. Esta guía te ayudará a configurar y operar el sistema de forma eficiente.

## 1. Inicio de Sesión
El sistema requiere autenticación. Por defecto, puedes usar las credenciales de administrador:
- **Usuario:** `admin`
- **Contraseña:** `admin`

*Nota: Se recomienda cambiar la contraseña o crear nuevos usuarios desde el panel de "Usuarios" tras el primer acceso.*

## 2. Configuración de Odoo
Para que la herramienta funcione, debe estar conectada a tu instancia de Odoo:
1. Dirígete a la pestaña **Configuración** en la barra lateral.
2. Introduce los datos de tu instancia:
   - **URL de Odoo:** (ej. `https://tu-empresa.odoo.com`)
   - **Base de Datos:** Nombre de la base de datos de Odoo.
   - **Usuario y Contraseña / API Key:** Credenciales con permisos de lectura en `stock.quant` y `stock.move`.
3. Haz clic en **"Save Connection"**. El sistema verificará la conexión y verás un indicador verde indicando "Connected".

## 3. Sincronización de Datos
Una vez configurado Odoo, debes traer los datos al sistema:
1. Ve a la pestaña **Inventory**.
2. Haz clic en el botón **"Sync with Odoo"**.
3. El sistema descargará automáticamente los productos, niveles de stock y el histórico de movimientos de los últimos meses.
4. Al finalizar, la tabla de inventario se actualizará con los valores reales del ERP.

## 4. Análisis del Inventario
En la vista **Inventory**, encontrarás herramientas para el análisis diario:
- **Filtros por Clase:** Puedes filtrar productos por importancia económica (A, B, C) o variabilidad (X, Y, Z).
- **Control de Estado:** El sistema marca en rojo los productos en **Stockout** (sin stock) y en naranja los que requieren **Reorder** (punto de pedido alcanzado).
- **Busqueda:** Utiliza la barra de búsqueda para localizar productos por nombre o código interno.

## 5. Simulador de Escenarios (What-If)
Esta es la herramienta más potente para la planificación:
1. Navega a **Simulation**.
2. **Selecciona productos:** Usa el botón "Select All" o selecciona individualmente los artículos que quieras analizar.
3. **Ajusta Parámetros:**
   - Usa el deslizador para simular aumentos de demanda (ej. previsión de campaña de navidad +30%).
   - Introduce un valor en "Lead Time Override" si esperas retrasos en las entregas del proveedor.
4. Haz clic en **"Run Simulation"**.
5. Revisa los resultados: El sistema te mostrará cuánto debería ser tu nuevo stock de seguridad y cuánto deberías pedir **ahora mismo** para estar preparado para ese escenario.

## 6. Dashboard Estratégico
La pantalla de inicio te ofrece una visión global de tu almacén:
- **Valor del Inventario:** Cuánto dinero tienes inmovilizado.
- **Fill Rate:** Eficiencia de tu servicio actual.
- **Riesgo de Rotura:** Cuántos productos críticos están cerca del agotamiento.
- **Productos Críticos:** Una lista de los 5 artículos que requieren atención inmediata.
