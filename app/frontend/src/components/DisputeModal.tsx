import React, { useState } from "react";
import type { Transaction } from "../types/transaction";

interface DisputeModalProps {
  transaction: Transaction | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmitDispute: (disputeData: {
    transactionId: string;
    reason: string;
    details: string;
  }) => Promise<void>;
}

export const DisputeModal: React.FC<DisputeModalProps> = ({
  transaction,
  isOpen,
  onClose,
  onSubmitDispute,
}) => {
  const [reason, setReason] = useState("unauthorized");
  const [details, setDetails] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !transaction) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmitDispute({
        transactionId: transaction.id,
        reason,
        details,
      });
      onClose();
    } catch (err) {
      console.error("Failed to submit dispute:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

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
          maxWidth: "480px",
          padding: "1.5rem",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
          <h3 style={{ margin: 0, color: "#111827" }}>Confirm Dispute Claim</h3>
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

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.25rem" }}>
              Dispute Reason
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              style={{
                width: "100%",
                padding: "0.5rem",
                borderRadius: "4px",
                border: "1px solid #d1d5db",
              }}
            >
              <option value="unauthorized">Unauthorized transaction</option>
              <option value="incorrect_amount">Incorrect charged amount</option>
              <option value="duplicate">Duplicate transaction</option>
              <option value="goods_not_received">Goods/Services not received</option>
            </select>
          </div>

          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.25rem" }}>
              Additional Details (Optional)
            </label>
            <textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              rows={3}
              placeholder="Provide extra details about this transaction..."
              style={{
                width: "100%",
                padding: "0.5rem",
                borderRadius: "4px",
                border: "1px solid #d1d5db",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                padding: "0.5rem 1rem",
                borderRadius: "4px",
                border: "1px solid #d1d5db",
                backgroundColor: "#ffffff",
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: "0.5rem 1rem",
                borderRadius: "4px",
                border: "none",
                backgroundColor: "#dc2626",
                color: "#ffffff",
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              {isSubmitting ? "Submitting..." : "Submit Dispute"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};