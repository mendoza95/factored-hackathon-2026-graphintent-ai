import React from "react";
import type { Transaction } from "../types/transaction";

interface TransactionCardProps {
  transaction: Transaction;
  onSelectDispute: (transaction: Transaction) => void;
  isDisabled?: boolean;
}

export const TransactionCard: React.FC<TransactionCardProps> = ({
  transaction,
  onSelectDispute,
  isDisabled = false,
}) => {
  const isDisputed = transaction.status === "disputed";

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "0.875rem 1rem",
        margin: "0.5rem 0",
        backgroundColor: "#ffffff",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
      }}
    >
      <div>
        <div style={{ fontWeight: 600, color: "#111827", fontSize: "0.95rem" }}>
          {transaction.merchant}
        </div>
        <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "2px" }}>
          {transaction.date} • <span style={{ textTransform: "capitalize" }}>{transaction.status}</span>
        </div>
      </div>

      <div style={{ textAlign: "right" }}>
        <div style={{ fontWeight: "bold", fontSize: "1rem", color: "#111827" }}>
          ${transaction.amount.toFixed(2)} {transaction.currency}
        </div>
        <button
          onClick={() => onSelectDispute(transaction)}
          disabled={isDisabled || isDisputed}
          style={{
            marginTop: "0.35rem",
            padding: "0.25rem 0.6rem",
            fontSize: "0.75rem",
            borderRadius: "4px",
            border: "none",
            backgroundColor: isDisputed ? "#9ca3af" : "#dc2626",
            color: "#ffffff",
            cursor: isDisabled || isDisputed ? "not-allowed" : "pointer",
          }}
        >
          {isDisputed ? "Disputed" : "Dispute Charge"}
        </button>
      </div>
    </div>
  );
};