export type Product = {
  id: number; odoo_id: number; name: string; default_code: string;
  current_stock: number; abc_class: string; xyz_class?: string; status: string;
  stock_policy_override?: string | null;
  daily_demand?: number; lead_time_days?: number; target_service_level?: number;
  manual_daily_demand?: number; manual_demand_std_dev?: number;
  eoq?: number; num_orders_year?: number;
  min_stock?: number; max_stock?: number; target_stock_level?: number;
  safety_stock?: number; safety_stock_continuous?: number; safety_stock_periodic?: number;
  review_period?: number; last_order_date?: string; recommended_qty?: number;
  cost_order?: number; cost_holding?: number; cost_total?: number;
  reserved_quantity?: number; incoming_qty?: number; location_name?: string;
  category_name?: string; image_url?: string; description?: string; standard_price?: number;
  z_value?: number; annual_demand?: number; demand_std_dev?: number;
}

export type AppUser = { id: number; username: string; role: string; is_active: boolean }
