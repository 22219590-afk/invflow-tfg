/**
 * Forecast UI Components — Isolated presentational components.
 * No API calls, no business logic. Pure display.
 */
import React from 'react';
import { TrendingUp, TrendingDown, Minus, Activity, AlertCircle, Gauge } from 'lucide-react';
import type { ForecastProduct, ForecastDetail, ForecastMetrics, ModelComparisonResult } from './api';

// ─── KPI Metric Card ──────────────────────────────────────────────────────────

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  sub?: string;
  color?: string;
  icon?: React.ReactNode;
}

export function MetricCard({ label, value, unit, sub, color = 'var(--primary)', icon }: MetricCardProps) {
  return (
    <div className="kpi-card-v3" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ background: 'var(--app-bg)', padding: '8px', borderRadius: '8px', color }}>
          {icon}
        </div>
      </div>
      <p style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
        {label}
      </p>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
        <span style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--gray-900)', lineHeight: 1 }}>
          {value ?? '—'}
        </span>
        {unit && <span style={{ fontSize: '0.7rem', color: 'var(--gray-500)', fontWeight: 600 }}>{unit}</span>}
      </div>
      {sub && <p style={{ fontSize: '0.68rem', color: 'var(--gray-400)', marginTop: '4px' }}>{sub}</p>}
    </div>
  );
}

// ─── Product List Item ────────────────────────────────────────────────────────

interface ProductListItemProps {
  product: ForecastProduct;
  isSelected: boolean;
  onClick: () => void;
}

export function ProductListItem({ product, isSelected, onClick }: ProductListItemProps) {
  const patternColor =
    product.demand_pattern === 'Estable' ? 'var(--success)' :
    product.demand_pattern === 'Estacional' ? 'var(--info)' :
    product.demand_pattern === 'Volátil' ? 'var(--warning)' :
    product.demand_pattern === 'Intermitente' ? 'var(--danger)' : 'var(--gray-500)';

  return (
    <div
      onClick={onClick}
      style={{
        padding: '14px 18px',
        borderBottom: '1px solid var(--gray-200)',
        cursor: 'pointer',
        background: isSelected ? 'white' : 'transparent',
        borderLeft: `4px solid ${isSelected ? 'var(--primary)' : 'transparent'}`,
        transition: 'all 0.15s ease',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <span style={{ fontSize: '0.72rem', fontFamily: 'monospace', color: 'var(--gray-500)', fontWeight: 700 }}>
          {product.default_code || 'SIN SKU'}
        </span>
        <ABCBadge cls={product.abc_class} />
      </div>
      <p style={{
        fontSize: '0.88rem', fontWeight: 700, color: 'var(--gray-900)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {product.name}
      </p>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: patternColor,
          background: `${patternColor}15`, padding: '2px 8px', borderRadius: '99px' }}>
          {product.demand_pattern}
        </span>
        <TrendIndicator trend={product.trend_type} size="sm" />
        {product.forecast_mape > 0 && (
          <span style={{ fontSize: '0.7rem', color: 'var(--gray-500)', marginLeft: 'auto' }}>
            MAPE: <strong style={{ color: product.forecast_mape < 20 ? 'var(--success)' : product.forecast_mape < 35 ? 'var(--warning)' : 'var(--danger)' }}>
              {product.forecast_mape.toFixed(1)}%
            </strong>
          </span>
        )}
      </div>
    </div>
  );
}

// ─── ABC Badge ────────────────────────────────────────────────────────────────

export function ABCBadge({ cls }: { cls: string }) {
  return (
    <span className={`badge-abc abc-${(cls || 'c').toLowerCase()}`}>
      {cls || 'C'}
    </span>
  );
}

// ─── Trend Indicator ──────────────────────────────────────────────────────────

interface TrendProps { trend: string; size?: 'sm' | 'md' }

export function TrendIndicator({ trend, size = 'md' }: TrendProps) {
  const iconSize = size === 'sm' ? 12 : 16;
  const color = trend === 'Increasing' ? 'var(--success)' : trend === 'Decreasing' ? 'var(--danger)' : 'var(--gray-500)';
  const label = trend === 'Increasing' ? 'Creciente' : trend === 'Decreasing' ? 'Decreciente' : 'Estable';
  const Icon = trend === 'Increasing' ? TrendingUp : trend === 'Decreasing' ? TrendingDown : Minus;
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color, fontSize: size === 'sm' ? '0.7rem' : '0.8rem', fontWeight: 700 }}>
      <Icon size={iconSize} />
      {label}
    </span>
  );
}

// ─── Stat Row ─────────────────────────────────────────────────────────────────

export function StatRow({ label, value, highlight = false }: { label: string; value?: string | number; highlight?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--gray-100)' }}>
      <span style={{ fontSize: '0.83rem', color: 'var(--gray-600)' }}>{label}</span>
      <span style={{ fontSize: '0.83rem', fontFamily: 'monospace', fontWeight: 700, color: highlight ? 'var(--warning)' : 'var(--gray-900)' }}>
        {value ?? '—'}
      </span>
    </div>
  );
}

// ─── MAPE Score Badge ─────────────────────────────────────────────────────────

export function MapeScore({ mape }: { mape: number }) {
  const color = mape < 15 ? 'var(--success)' : mape < 30 ? 'var(--warning)' : 'var(--danger)';
  const label = mape < 15 ? 'Excelente' : mape < 30 ? 'Aceptable' : 'Mejorable';
  return (
    <div style={{ textAlign: 'right' }}>
      <p style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Error Modelo (MAPE)
      </p>
      <p style={{ fontSize: '2.8rem', fontWeight: 900, color, lineHeight: 1, marginTop: '4px' }}>
        {mape.toFixed(1)}%
      </p>
      <span style={{ fontSize: '0.7rem', color, fontWeight: 700 }}>{label}</span>
    </div>
  );
}

// ─── Insufficient Data State ──────────────────────────────────────────────────

export function InsufficientDataState({ message }: { message?: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '60px 40px', background: 'white', borderRadius: 'var(--radius-lg)',
      border: '2px dashed var(--gray-200)', textAlign: 'center',
      color: 'var(--gray-500)', gap: '16px',
    }}>
      <AlertCircle size={48} style={{ opacity: 0.3 }} />
      <p style={{ fontSize: '1rem', fontWeight: 700 }}>Datos insuficientes para forecasting fiable</p>
      <p style={{ fontSize: '0.85rem', maxWidth: '320px', lineHeight: 1.6 }}>
        {message || 'Se necesitan al menos 4 semanas de historial de ventas. Sincroniza los datos de Odoo y recalcula el forecast.'}
      </p>
    </div>
  );
}

// ─── Model Comparison Table ───────────────────────────────────────────────────

export function ModelComparisonTable({ data }: { data: ModelComparisonResult }) {
  return (
    <div>
      <div style={{ marginBottom: '12px' }}>
        <p style={{ fontSize: '0.75rem', color: 'var(--gray-500)', fontWeight: 600 }}>
          Entrenamiento: {data.train_weeks} semanas · Test: {data.test_weeks} semanas (holdout 20%)
        </p>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table" style={{ fontSize: '0.85rem' }}>
          <thead>
            <tr>
              <th>Modelo</th>
              <th style={{ textAlign: 'right' }}>MAE</th>
              <th style={{ textAlign: 'right' }}>MAPE (%)</th>
              <th style={{ textAlign: 'right' }}>RMSE</th>
              <th style={{ textAlign: 'center' }}>Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.models.map((m) => (
              <tr key={m.model} style={{ background: m.is_winner ? 'rgba(16,185,129,0.05)' : undefined }}>
                <td style={{ fontWeight: m.is_winner ? 800 : 600, color: m.is_winner ? 'var(--success)' : 'var(--gray-700)' }}>
                  {m.model}
                </td>
                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                  {m.mae !== null ? m.mae.toFixed(2) : <span style={{ color: 'var(--gray-300)' }}>—</span>}
                </td>
                <td style={{ textAlign: 'right', fontFamily: 'monospace', color: m.mape !== null && m.mape < 20 ? 'var(--success)' : m.mape !== null && m.mape < 35 ? 'var(--warning)' : 'var(--danger)' }}>
                  {m.mape !== null ? `${m.mape.toFixed(2)}%` : <span style={{ color: 'var(--gray-300)' }}>—</span>}
                </td>
                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                  {m.rmse !== null ? m.rmse.toFixed(2) : <span style={{ color: 'var(--gray-300)' }}>—</span>}
                </td>
                <td style={{ textAlign: 'center' }}>
                  {m.is_winner
                    ? <span style={{ background: 'var(--success-light)', color: 'var(--success)', padding: '3px 10px', borderRadius: '99px', fontSize: '0.72rem', fontWeight: 800 }}>✓ GANADOR</span>
                    : m.error
                    ? <span style={{ color: 'var(--danger)', fontSize: '0.72rem' }}>Error</span>
                    : <span style={{ color: 'var(--gray-400)', fontSize: '0.72rem' }}>—</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
