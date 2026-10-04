import { apiClient } from "./client";

export const getTransactions = async () => {
  const response = await apiClient.get("/transactions");
  return response.data;
};

export const createDispute = async (disputeData: {
  transaction_id: string;
  reason: string;
  details?: string;
}) => {
  const response = await apiClient.post("/disputes", disputeData);
  return response.data;
};