# Lógica de Gestión de Inventarios - InvFlow

Este documento detalla los algoritmos y metodologías matemáticas implementadas en el motor analítico de **InvFlow** para la optimización de stocks y la toma de decisiones.

## 1. Clasificación ABC (Basada en Valor de Consumo)

Se utiliza el **Principio de Pareto** para categorizar los productos según su importancia económica:

- **Algoritmo:**
  1. Se calcula el Valor de Consumo Anual (VCA) para cada producto: `VCA = Demanda Anual * Coste Estándar`.
  2. Se ordenan los productos de mayor a menor VCA.
  3. Se calcula el porcentaje acumulado del valor total.
- **Categorías:**
  - **Clase A:** Productos que representan el ~80% del valor total (generalmente el 20% de los artículos). Requieren control estricto.
  - **Clase B:** Productos con valor intermedio (~15%).
  - **Clase C:** Productos de bajo valor (~5%) pero gran volumen de referencias.

## 2. Clasificación XYZ (Variabilidad de la Demanda)

Complementa al ABC midiendo la previsibilidad del consumo mediante el Coeficiente de Variación (CV):

- **Fórmula:** `CV = Desviación Estándar de la Demanda / Demanda Promedio`
- **Categorías:**
  - **X:** Baja variabilidad (demanda constante). Fácil de predecir.
  - **Y:** Variabilidad moderada o estacionalidad.
  - **Z:** Alta variabilidad o consumo esporádico. Difícil de predecir.

## 3. Política de Stock y Nivel de Servicio

InvFlow calcula dinámicamente los puntos de pedido basándose en el **Nivel de Servicio** deseado (por defecto 95%):

### Stock de Seguridad (Safety Stock - SS)
Utiliza la fórmula basada en la incertidumbre de la demanda durante el plazo de entrega (Lead Time):
`SS = Z * σd * √LT`
Donde:
- `Z`: Factor de seguridad (1.645 para 95% de nivel de servicio).
- `σd`: Desviación estándar de la demanda diaria.
- `LT`: Tiempo de entrega del proveedor en días.

### Punto de Pedido (Min Stock)
Es el nivel de inventario que dispara una orden de reposición:
`Min = (Demanda Diaria * LT) + SS`

### Stock Máximo (Max Stock)
Basado en el modelo de revisión continua o pedido óptimo:
`Max = Min + Lote Óptimo (EOQ)`
*(Nota: El sistema utiliza actualmente una simplificación del lote óptimo basada en el consumo mensual para evitar sobrestock en Clase C).*

## 4. Motor de Simulación "What-If"

La simulación permite proyectar escenarios sin alterar los datos maestros de producción:

1. **Delta de Demanda (%):** Incrementa o decrementa la `Demanda Diaria` promedio en base a una tendencia esperada.
2. **Override de Lead Time:** Modifica el `LT` para simular retrasos en la cadena de suministro.
3. **Cálculo de Resultados:**
   - Recalcula los nuevos `SS`, `Min` y `Max` con los parámetros simulados.
   - Determina el `Status de Simulación` (OK, Reorder, Stockout) comparando el stock físico actual contra los nuevos umbrales proyectados.
   - Sugiere la **Cantidad a Pedir** necesaria para alcanzar el nuevo `Max` teórico.

## 5. KPIs de Rendimiento (Dashboard)

- **Inventory Turnover (Rotación):** `Ventas Totales Anuales / Valor Promedio de Inventario`. Indica cuántas veces se renueva el stock al año.
- **Fill Rate:** Porcentaje de productos cuyo stock actual cubre satisfactoriamente el punto de pedido (Min).
- **Valor Total del Inventario:** Suma de `Stock Actual * Coste Estándar` de todas las referencias.
