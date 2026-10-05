// src/types/account.ts

export interface CustomerInfo {
  first_name?: string;
  last_name?: string;
  customer_id?: string;
}

export interface AccountSummary {
  customer?: CustomerInfo;
  total_balance_local: number;
  total_balance_usd: number;
  products_count: number;
  recent_tx_count: number;
  open_complaints_count: number;
}