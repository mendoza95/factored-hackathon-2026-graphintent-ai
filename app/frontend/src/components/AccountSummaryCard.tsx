// src/components/AccountSummaryCard.tsx

import React from "react";
import type { AccountSummary } from "../types/account";

interface AccountSummaryCardProps {
  summary: AccountSummary;
}

export const AccountSummaryCard: React.FC<AccountSummaryCardProps> = ({ summary }) => {
  const customerName = summary.customer?.first_name
    ? `${summary.customer.first_name} ${summary.customer.last_name || ""}`.trim()
    : "Cliente";

  return (
    <div
      style={{
        border: "1px solid #d1d5db",
        borderRadius: "10px",
        padding: "0.85rem 1rem",
        marginBottom: "0.5rem",
        backgroundColor: "#ffffff",
        boxShadow: "0 2px 4px rgba(0, 0, 0, 0.05)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid #f3f4f6",
          paddingBottom: "0.5rem",
          marginBottom: "0.6rem",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "#111827" }}>
          Resumen Financiero
        </span>
        <span style={{ fontSize: "0.75rem", color: "#6b7280", backgroundColor: "#f3f4f6", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
          {customerName}
        </span>
      </div>

      <div style={{ marginBottom: "0.6rem" }}>
        <p style={{ margin: 0, fontSize: "0.75rem", color: "#6b7280" }}>
          Balance Total Estimado
        </p>
        <p style={{ margin: "0.1rem 0 0 0", fontWeight: 700, fontSize: "1.15rem", color: "#1d4ed8" }}>
          ${summary.total_balance_local.toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN
        </p>
        <p style={{ margin: 0, fontSize: "0.75rem", color: "#9ca3af" }}>
          ≈ ${summary.total_balance_usd.toLocaleString("en-US", { minimumFractionDigits: 2 })} USD
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: "0.5rem",
          paddingTop: "0.5rem",
          borderTop: "1px solid #f3f4f6",
          textAlign: "center",
        }}
      >
        <div>
          <p style={{ margin: 0, fontSize: "0.7rem", color: "#6b7280" }}>Productos</p>
          <p style={{ margin: 0, fontWeight: 600, fontSize: "0.85rem", color: "#374151" }}>
            {summary.products_count}
          </p>
        </div>
        <div>
          <p style={{ margin: 0, fontSize: "0.7rem", color: "#6b7280" }}>Movimientos</p>
          <p style={{ margin: 0, fontWeight: 600, fontSize: "0.85rem", color: "#374151" }}>
            {summary.recent_tx_count}
          </p>
        </div>
        <div>
          <p style={{ margin: 0, fontSize: "0.7rem", color: "#6b7280" }}>Reclamos</p>
          <p
            style={{
              margin: 0,
              fontWeight: 600,
              fontSize: "0.85rem",
              color: summary.open_complaints_count > 0 ? "#dc2626" : "#059669",
            }}
          >
            {summary.open_complaints_count}
          </p>
        </div>
      </div>
    </div>
  );
};