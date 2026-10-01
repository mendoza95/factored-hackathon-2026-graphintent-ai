import { apiClient } from "./client";

export interface ChatPayload {
  session_id: string;
  message: string;
  language?: string;
  user_accent?: string;
}

export const sendChatMessage = async (payload: ChatPayload) => {
  const response = await apiClient.post("/chat", payload);
  return response.data;
};