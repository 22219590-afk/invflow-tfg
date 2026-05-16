# ESPECIFICACIONES TÉCNICAS DE MÓDULOS — INVFLOW

Este documento detalla la lógica interna, los datos de entrada (Inputs), los resultados generados (Outputs) y las fórmulas de cálculo para cada módulo del sistema.

---

## 1. MÓDULO: DASHBOARD (CUADRO DE MANDO)

### Objetivo
Proporcionar una visión holística y en tiempo real del estado de la cadena de suministro y la salud del inventario.

- **Inputs**:
    - `StockQuant`: Niveles actuales de stock por producto.
    - `ForecastResult`: Previsiones de demanda futura.
    - `Product`: Parámetros de seguridad (SS, ROP).
- **Outputs**:
    - **Nivel de Servicio**: % de productos cuya disponibilidad actual > 0.
    - **Valor de Almacén**: $\sum (Stock \cdot Coste\_Estándar)$.
    - **Alertas Críticas**: Lista de productos donde $Stock \leq ROP$.
- **Lógica de Cálculo**:
    - El dashboard realiza agregaciones SQL en tiempo real para calcular promedios de error (MAPE) y coberturas de stock (Stock / Demanda Media Diaria).

---

## 2. MÓDULO: PLAN DIARIO (LOGÍSTICA)

### Objetivo
Gestión operativa del inventario mediante políticas de reposición automatizadas.

- **Inputs**:
    - Histórico de movimientos (365 días).
    - Parámetros de configuración: Coste de pedido ($S$), Coste de mantenimiento ($H$).
- **Outputs**:
    - **Clasificación ABC**:
        - **A**: 80% del valor acumulado (20% productos).
        - **B**: 15% del valor acumulado (30% productos).
        - **C**: 5% del valor acumulado (50% productos).
    - **Recomendación de Pedido**: Cantidad EOQ si $Stock \leq Punto\_Pedido$.
- **Cálculos Clave**:
    - **EOQ**: $\sqrt{2DS/H}$.
    - **SS (Stock Seguridad)**: $Z \cdot \sigma \cdot \sqrt{L}$.
    - **Punto de Pedido**: $(Demanda\_Media \cdot Lead\_Time) + SS$.

---

## 3. MÓDULO: PREVISIÓN (FORECASTING)

### Objetivo
Predecir la demanda futura con la máxima precisión estadística.

- **Inputs**:
    - Serie temporal de consumos (`StockMove` tipo 'out') agrupada por semana/mes.
- **Outputs**:
    - Proyección a 12 meses.
    - Métrica de error (MAPE).
    - Modelo óptimo seleccionado.
- **Pipeline de Cálculo**:
    1. **Pre-procesamiento**: Eliminación de outliers y relleno de huecos (Zero-filling).
    2. **Backtesting**: El sistema entrena 3 modelos (ARIMA, Holt-Winters, Suavizado Simple).
    3. **Selección**: Se elige el modelo con el menor **MAPE** en el conjunto de test.
    4. **Proyección**: Se aplica el modelo ganador sobre toda la serie para generar el futuro.

---

## 4. MÓDULO: PLAN MAESTRO (MPS)

### Objetivo
Optimizar la producción y capacidad a nivel mensual para minimizar costes totales.

- **Inputs**:
    - Forecast de demanda mensual (12 meses).
    - Capacidad de recursos (unidades/trabajador).
    - Costes de inventario, contratación y despido.
- **Outputs**:
    - **P_t**: Unidades a producir por mes.
    - **W_t**: Plantilla de trabajadores necesaria.
    - **I_t**: Inventario proyectado al final de cada mes.
- **Lógica (Simplex / Optimización Lineal)**:
    - **Función Objetivo**: $Min \sum (Costes\_Producción + Costes\_Mantenimiento + Costes\_RRHH)$.
    - **Restricción de Balance**: El stock final del mes $t$ debe ser igual al inicial + producción - demanda.

---

## 5. MÓDULO: MRP (REQUERIMIENTOS)

### Objetivo
Sincronizar la disponibilidad de materiales con el plan de producción.

- **Inputs**:
    - Resultados del MPS (Necesidades Brutas de Nivel 0).
    - **BOM (Lista de Materiales)**: Relación padre-hijo y cantidades.
    - Lead Times de compra/fabricación.
- **Outputs**:
    - **Necesidades Netas**: Cantidad real a adquirir tras descontar stock.
    - **Plan de Lanzamiento**: Fecha y cantidad exacta para emitir el pedido.
- **Algoritmo de Explosión**:
    1. Se calculan las **Necesidades Brutas** del producto terminado.
    2. Se realiza el **Neteo**: $Neto = Bruto - Stock - Rec\_Programadas$.
    3. **Desfase (Time-Phasing)**: La orden de compra se sitúa en $T - Lead\_Time$.
    4. Si el producto tiene componentes en la BOM, el **Plan de Lanzamiento** del padre se convierte en la **Necesidad Bruta** de los hijos.

---

## 6. MÓDULO: SIMULACIÓN

### Objetivo
Evaluar escenarios "What-If" sin afectar los datos reales de producción.

- **Inputs**:
    - Copia del estado actual del sistema (Sandbox).
    - Parámetros variables (ej: incremento del 20% en lead times).
- **Outputs**:
    - Comparativa de costes y niveles de servicio entre el escenario Base y el Simulado.
- **Lógica**:
    - Ejecución paralela de los motores de MPS y MRP sobre un esquema de datos temporal en memoria o tablas de simulación.
