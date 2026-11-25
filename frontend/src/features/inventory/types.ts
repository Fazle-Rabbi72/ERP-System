export type MovementType = "in" | "out" | "adjustment";

export interface WarehouseItem {
  id: string;
  code: string;
  name: string;
  location: string;
  is_active: boolean;
  created_at: string;
}

export interface ProductItem {
  id: string;
  sku: string;
  name: string;
  unit: string;
  unit_cost: string;
  sale_price: string;
  reorder_level: string;
  is_active: boolean;
  description: string;
  created_at: string;
}

export interface StockSummaryItem {
  product_id: string;
  sku: string;
  product_name: string;
  unit: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  on_hand: string;
  reorder_level: string;
  unit_cost: string;
  stock_value: string;
  is_low_stock: boolean;
}

export interface StockSummaryResponse {
  items: StockSummaryItem[];
  total_valuation: string;
  low_stock_count: number;
}
