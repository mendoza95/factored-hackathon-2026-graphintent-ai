export interface Transaction {
  id: string;
  merchant: string;
  amount: number;
  currency: string;
  date: string;
  status: "posted" | "pending" | "disputed";
  category?: string;
}