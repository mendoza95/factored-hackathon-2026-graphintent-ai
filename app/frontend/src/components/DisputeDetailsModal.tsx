import React from "react";
import type { Transaction } from "../types/transaction";

interface DisputeDetailsModalProps {
  transaction: Transaction | null;
  disputeData: {
    referenceId: string;
    reason: string;
    status: string;
  } | null;
  isOpen: boolean;
  onClose: () => void;
}

export const DisputeDetailsModal: React.FC<DisputeDetailsModalProps> = ({
  transaction,
  disputeData,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !transaction) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: "#ffffff",
          borderRadius: "8px",
          width: "100%",
          maxWidth: "400px",
          padding: "1.5rem",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
          <h3 style={{ margin: 0, color: "#111827" }}>Detalles del Reclamo</h3>
          <button
            onClick={onClose}
            style={{ border: "none", background: "none", cursor: "pointer", fontSize: "1.2rem" }}
          >
            ×
          </button>
        </div>

        <div style={{ backgroundColor: "#f9fafb", padding: "0.75rem", borderRadius: "6px", marginBottom: "1rem" }}>
          <div style={{ fontWeight: "bold", color: "#111827" }}>{transaction.merchant}</div>
          <div style={{ color: "#4b5563", fontSize: "0.875rem" }}>
            ${transaction.amount.toFixed(2)} {transaction.currency} • {transaction.date}
          </div>
        </div>

        <div style={{ fontSize: "0.9rem", color: "#374151", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <div><strong>ID de Referencia:</strong> {disputeData?.referenceId || "DISP-SUCCESS"}</div>
          <div><strong>Motivo:</strong> {disputeData?.reason || "unauthorized"}</div>
          <div><strong>Estado:</strong> {disputeData?.status || "En Revisión"}</div>
        </div>

        <div style={{ marginTop: "1.5rem", display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "4px",
              border: "none",
              backgroundColor: "#2563eb",
              color: "#ffffff",
              cursor: "pointer",
            }}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};