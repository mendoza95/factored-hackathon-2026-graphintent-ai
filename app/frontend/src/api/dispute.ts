import { apiClient } from "./client";

export const getTransactions = async () => {
  const response = await apiClient.get("/transactions");
  return response.data;
};

export const createDispute = async (disputeData: {
  transaction_id: string;
  reason: string;
  details?: string;
  session_id?: string;
}) => {
  const response = await apiClient.post("/disputes", {
    session_id: "SESS_FE_MAIN",
    ...disputeData,
  });
  return response.data;
};