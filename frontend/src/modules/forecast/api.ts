/**
 * Forecast API — Isolated API client for the forecast module.
 * Only talks to /v1/forecast/* endpoints.
 * No shared state with other modules.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function authHeaders(token: string): HeadersInit {
  return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
}

async function apiFetch<T>(url: string, token: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: { ...authHeaders(token), ...(options?.headers || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface ForecastProduct {
  odoo_id: number;
  name: string;
  default_code: string;
  abc_class: string;
  forecast_model: string;
  forecast_mape: number;
  demand_pattern: string;
  trend_type: string;
  daily_demand: number;
  seasonality_strength: number;
  volatility_index: number;
  has_forecast: boolean;
}

export interface ChartPoint {
  date: string;
  real: number | null;
  forecast: number | null;
  quantity?: number;
  type?: string;
}

export interface ForecastMetrics {
  mae: number;
  mape: number;
  rmse: number;
  mean: number;
  median: number;
  std_dev: number;
  p25: number;
  p75: number;
  outliers_count: number;
}

export interface ForecastDetail {
  product_id: number;
  product_name: string;
  product_code: string;
  abc_class: string;
  forecast_model: string;
  forecast_mape: number;
  demand_pattern: string;
  trend_type: string;
  seasonality_strength: number;
  volatility_index: number;
  daily_demand: number;
  chart_data: ChartPoint[];
  forecast_results: { date: string; quantity: number; type: string }[];
  historical: { date: string; quantity: number; type: string }[];
  metrics: ForecastMetrics | null;
  has_sufficient_data: boolean;
  message?: string;
  generated_at: string;
}

export interface ModelComparison {
  model: string;
  mae: number | null;
  mape: number | null;
  rmse: number | null;
  is_winner: boolean;
  error?: string;
}

export interface ModelComparisonResult {
  product_id: number;
  product_name: string;
  selected_model: string;
  test_weeks: number;
  train_weeks: number;
  models: ModelComparison[];
}

export const forecastApi = {
  getProducts: (token: string, search?: string, abc_class?: string): Promise<ForecastProduct[]> => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (abc_class) params.set('abc_class', abc_class);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return apiFetch<ForecastProduct[]>(`/v1/forecast/products${qs}`, token);
  },

  getDetail: (token: string, productId: number, granularity = 'weekly'): Promise<ForecastDetail> => {
    return apiFetch<ForecastDetail>(`/v1/forecast/${productId}?granularity=${granularity}`, token);
  },

  runAll: (token: string): Promise<{ message: string; summary: any }> => {
    return apiFetch(`/v1/forecast/run`, token, { method: 'POST' });
  },

  runSingle: (token: string, productId: number): Promise<ForecastDetail> => {
    return apiFetch<ForecastDetail>(`/v1/forecast/run/${productId}`, token, { method: 'POST' });
  },

  getModelComparison: (token: string, productId: number): Promise<ModelComparisonResult> => {
    return apiFetch<ModelComparisonResult>(`/v1/forecast/${productId}/comparison`, token);
  },
};
