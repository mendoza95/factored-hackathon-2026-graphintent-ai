import React from "react";
import type { Transaction } from "../types/transaction";

interface TransactionCardProps {
  transaction: Transaction;
  optionIndex?: number | string;
  onOpenDispute?: (tx: Transaction) => void;
  onViewDisputeDetails?: (tx: Transaction) => void;
}

export const TransactionCard: React.FC<TransactionCardProps> = ({
  transaction,
  optionIndex,
  onOpenDispute,
  onViewDisputeDetails,
}) => {
  const isDisputed = transaction.already_disputed || transaction.status === "disputed";

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "0.75rem",
        marginBottom: "0.5rem",
        backgroundColor: isDisputed ? "#f9fafb" : "#ffffff",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <div>
        <p style={{ margin: 0, fontWeight: "bold", fontSize: "0.9rem" }}>
          {optionIndex ? `${optionIndex}. ` : ""}{transaction.merchant}
        </p>
        <p style={{ margin: 0, color: "#6b7280", fontSize: "0.8rem" }}>
          Monto: ${transaction.amount} {transaction.currency} | Fecha: {transaction.date}
        </p>
        {isDisputed && (
          <span style={{ fontSize: "0.75rem", color: "#d97706", fontWeight: 600 }}>
            Disputa en proceso
          </span>
        )}
      </div>

      <div>
        {isDisputed ? (
          /* SI YA ESTÁ DISPUTADA: Habilitado únicamente el botón de ver detalles */
          <button
            type="button"
            onClick={() => onViewDisputeDetails && onViewDisputeDetails(transaction)}
            style={{
              padding: "0.4rem 0.8rem",
              backgroundColor: "#dbeafe",
              color: "#1d4ed8",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "0.8rem",
              fontWeight: 500,
            }}
          >
            Ver Detalles
          </button>
        ) : (
          /* SI NO ESTÁ DISPUTADA: Se muestra el botón para disputar */
          <button
            type="button"
            onClick={() => onOpenDispute && onOpenDispute(transaction)}
            style={{
              padding: "0.4rem 0.8rem",
              backgroundColor: "#ef4444",
              color: "#ffffff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "0.8rem",
              fontWeight: 500,
            }}
          >
            Disputar
          </button>
        )}
      </div>
    </div>
  );
};