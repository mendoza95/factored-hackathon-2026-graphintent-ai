// src/components/ChatMessage.tsx

import React from "react";
import { TransactionCard } from "./TransactionCard";
import { AccountSummaryCard } from "./AccountSummaryCard";
import type { Transaction } from "../types/transaction";
import type { AccountSummary } from "../types/account";

export interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  intent?: string;
  action?: string;
  confidence?: number;
  contextData?: {
    transactions?: any[];
    selectable_options?: any[];
    account_summary?: AccountSummary; // <-- Agregado
  };
}

interface ChatMessageProps {
  message: Message;
  onOpenDisputeModal?: (tx: Transaction) => void;
  onViewDisputeDetails?: (tx: Transaction) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onOpenDisputeModal,
  onViewDisputeDetails,
}) => {
  const isUser = message.sender === "user";
  const options = message.contextData?.selectable_options;
  const accountSummary = message.contextData?.account_summary; // <-- Extraer resumen

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start",
        margin: "0.75rem 0",
      }}
    >
      <div
        style={{
          maxWidth: "85%",
          padding: "0.75rem 1rem",
          borderRadius: "12px",
          backgroundColor: isUser ? "#2563eb" : "#f3f4f6",
          color: isUser ? "#ffffff" : "#1f2937",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{message.text}</p>
      </div>

      {/* Renderizar tarjeta de Resumen de Cuenta */}
      {!isUser && accountSummary && (
        <div style={{ width: "85%", marginTop: "0.5rem" }}>
          <AccountSummaryCard summary={accountSummary} />
        </div>
      )}

      {/* Renderizar tarjetas de Transacciones seleccionables */}
      {!isUser && options && options.length > 0 && (
        <div style={{ width: "85%", marginTop: "0.5rem" }}>
          {options.map((option, index) => {
            const isAlreadyDisputed = Boolean(
              option.already_disputed || option.transaction_data?.already_disputed
            );

            const tx: Transaction = {
              id: String(option.transaction_data?.id || option.value || option.id),
              merchant: option.transaction_data?.merchant || "Transacción",
              amount: Number(option.transaction_data?.amount || 0),
              currency: option.transaction_data?.currency || "USD",
              date: option.transaction_data?.timestamp || option.transaction_data?.date || "Reciente",
              status: isAlreadyDisputed ? "disputed" : (option.transaction_data?.status || "posted"),
              already_disputed: isAlreadyDisputed,
            };

            return (
              <TransactionCard
                key={option.id || index}
                transaction={tx}
                optionIndex={index + 1}
                onOpenDispute={onOpenDisputeModal}
                onViewDisputeDetails={onViewDisputeDetails}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};