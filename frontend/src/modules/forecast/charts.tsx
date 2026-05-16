/**
 * Forecast Charts — Isolated chart components for the forecasting module.
 * Uses Recharts. No external state dependencies.
 */
import React from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import type { ChartPoint, ModelComparison } from './api';

const CHART_COLORS = {
  real: '#326896',
  forecast: '#10b981',
  grid: '#e2e8f0',
  axis: '#94a3b8',
};

interface ForecastChartProps {
  data: ChartPoint[];
  height?: number;
}

export function ForecastAreaChart({ data, height = 360 }: ForecastChartProps) {
  if (!data || data.length === 0) {
    return (
      <div style={{
        height, display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: '2px dashed var(--gray-200)', borderRadius: 'var(--radius-md)',
        color: 'var(--gray-400)', fontWeight: 600, fontSize: '0.9rem',
      }}>
        Sin datos históricos suficientes para proyección
      </div>
    );
  }

  // Separate real from forecast for tooltip distinction
  const today = new Date().toISOString().slice(0, 10);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{
        background: 'var(--gray-900)', borderRadius: '10px', padding: '12px 16px',
        color: 'white', fontSize: '0.82rem', fontWeight: 600,
        boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
      }}>
        <p style={{ marginBottom: '8px', color: 'var(--gray-400)', fontSize: '0.75rem' }}>{label}</p>
        {payload.map((entry: any) => (
          entry.value !== null && (
            <p key={entry.dataKey} style={{ color: entry.color, margin: '2px 0' }}>
              {entry.name}: <strong>{Number(entry.value).toFixed(1)}</strong> un
            </p>
          )
        ))}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gradReal" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.real} stopOpacity={0.25} />
            <stop offset="95%" stopColor={CHART_COLORS.real} stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="gradForecast" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.forecast} stopOpacity={0.2} />
            <stop offset="95%" stopColor={CHART_COLORS.forecast} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
        <XAxis
          dataKey="date"
          stroke={CHART_COLORS.axis}
          fontSize={11}
          tickLine={false}
          axisLine={false}
          interval={Math.floor(data.length / 8)}
          tickFormatter={(v) => {
            try { return new Date(v).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' }); }
            catch { return v; }
          }}
        />
        <YAxis stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} axisLine={false} width={50} />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value) => <span style={{ fontSize: '0.8rem', color: 'var(--gray-600)', fontWeight: 600 }}>{value}</span>}
        />
        <Area
          type="monotone"
          dataKey="real"
          name="Demanda Real"
          stroke={CHART_COLORS.real}
          strokeWidth={2.5}
          fill="url(#gradReal)"
          dot={false}
          activeDot={{ r: 5, fill: CHART_COLORS.real }}
          connectNulls={false}
        />
        <Area
          type="monotone"
          dataKey="forecast"
          name="Previsión"
          stroke={CHART_COLORS.forecast}
          strokeWidth={2.5}
          fill="url(#gradForecast)"
          strokeDasharray="6 3"
          dot={false}
          activeDot={{ r: 5, fill: CHART_COLORS.forecast }}
          connectNulls={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

interface ModelComparisonChartProps {
  models: ModelComparison[];
  height?: number;
}

export function ModelComparisonChart({ models, height = 220 }: ModelComparisonChartProps) {
  const validModels = models.filter(m => m.mape !== null);
  if (!validModels.length) return null;

  const data = validModels.map(m => ({
    name: m.model.replace('Exponential-Smoothing', 'SES'),
    MAPE: Number(m.mape?.toFixed(2)),
    fill: m.is_winner ? 'var(--success)' : 'var(--primary-light)',
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
        <XAxis dataKey="name" stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} axisLine={false} />
        <YAxis stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} axisLine={false} unit="%" />
        <Tooltip
          formatter={(v: any) => [`${Number(v).toFixed(2)}%`, 'MAPE']}
          contentStyle={{ background: 'var(--gray-900)', border: 'none', borderRadius: '8px', color: 'white', fontSize: '0.82rem' }}
        />
        <Bar dataKey="MAPE" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <rect key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
