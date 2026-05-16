import React from 'react'

export default function ForecastModule({ token }: { token: string }) {
  return (
    <div className="view-container animate-in-up">
      <div className="view-header">
        <div>
          <h2 className="view-title">Previsión de Demanda</h2>
          <p className="view-subtitle">Análisis predictivo y modelos de forecasting estadístico</p>
        </div>
      </div>
      
      <div className="kpi-card-v3" style={{ padding: '40px', textAlign: 'center' }}>
        <p style={{ color: '#64748b' }}>Módulo de Previsión en desarrollo. Aquí se visualizarán las series temporales y proyecciones ARIMA/Prophet.</p>
      </div>
    </div>
  )
}
