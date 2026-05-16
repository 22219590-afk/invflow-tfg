# FUNDAMENTOS MATEMÁTICOS Y LÓGICA DE NEGOCIO — INVFLOW

## 1. POLÍTICAS DE INVENTARIO (PLAN DIARIO)

### 1.1 Lote Económico de Pedido (EOQ / Wilson)
Utilizado para minimizar la suma de costes de pedido y costes de mantenimiento.
$$EOQ = \sqrt{\frac{2 \cdot D \cdot S}{H}}$$
- **D**: Demanda anual.
- **S**: Coste de emisión de pedido.
- **H**: Coste de mantenimiento anual por unidad.

### 1.2 Punto de Pedido (ROP)
Nivel de stock que dispara un nuevo pedido considerando el consumo durante el tiempo de espera.
$$ROP = (d \cdot L) + SS$$
- **d**: Demanda diaria media.
- **L**: Lead Time (tiempo de suministro) en días.
- **SS**: Stock de Seguridad.

### 1.3 Stock de Seguridad (SS)
Calculado para cubrir la variabilidad de la demanda con un nivel de servicio deseado.
$$SS = Z \cdot \sigma_d \cdot \sqrt{L}$$
- **Z**: Coeficiente de nivel de servicio (ej: 1.645 para 95%).
- **$\sigma_d$**: Desviación típica de la demanda diaria.

---

## 2. FORECASTING (PREVISIÓN)

### 2.1 Suavizado Exponencial de Holt-Winters
Para series con tendencia y estacionalidad.
- **Nivel ($L_t$)**: $L_t = \alpha(Y_t - S_{t-m}) + (1-\alpha)(L_{t-1} + T_{t-1})$
- **Tendencia ($T_t$)**: $T_t = \beta(L_t - L_{t-1}) + (1-\beta)T_{t-1}$
- **Estacionalidad ($S_t$)**: $S_t = \gamma(Y_t - L_t) + (1-\gamma)S_{t-m}$

### 2.2 Métricas de Error
- **MAPE**: Mean Absolute Percentage Error.
$$MAPE = \frac{100\%}{n} \sum_{t=1}^{n} \left| \frac{A_t - F_t}{A_t} \right|$$

---

## 3. MPS (PLAN MAESTRO)

### 3.1 Modelo de Programación Lineal
**Función Objetivo (Minimizar Coste Total):**
$$Min \sum_{t=1}^{12} (C_p \cdot P_t + C_i \cdot I_t + C_w \cdot W_t + C_h \cdot H_t + C_f \cdot F_t)$$

**Restricciones de Balance de Inventario:**
$$I_{t-1} + P_t - I_t = D_t$$

**Restricciones de Fuerza Laboral:**
$$W_t = W_{t-1} + H_t - F_t$$
$$P_t \leq W_t \cdot K$$

Donde:
- **$P_t$**: Producción.
- **$I_t$**: Inventario final.
- **$W_t$**: Trabajadores.
- **$H_t, F_t$**: Contrataciones y despidos.

---

## 4. MRP (REQUERIMIENTOS)

### 4.1 Explosión de Necesidades
Para cada componente $j$ de un producto $i$:
$$NB_{j,t} = \sum_{i} (Plan\_Lanzamiento_{i,t} \cdot Qty_{i,j})$$
$$NN_{j,t} = Max(0, NB_{j,t} - Stock\_Disp_{j,t-1})$$
$$Plan\_Lanzamiento_{j,t-L_j} = NN_{j,t}$$
