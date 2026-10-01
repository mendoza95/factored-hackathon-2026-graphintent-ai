import React, { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api/chat";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "./ChatMessage";
import { TransactionCard } from "./TransactionCard";
import type { Transaction } from "../types/transaction";
import { DisputeModal } from "./DisputeModal";

export const ChatBox: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      sender: "assistant",
      text: "Hello! How can I assist you with your account or disputes today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Modal State
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Mock initial transactions for testing
  const [mockTransactions, setMockTransactions] = useState<Transaction[]>([
    {
      id: "TX_1001",
      merchant: "Uber Trip",
      amount: 45.5,
      currency: "USD",
      date: "Oct 01, 2026",
      status: "posted",
    },
    {
      id: "TX_1002",
      merchant: "Unknown Electronics Store",
      amount: 150.0,
      currency: "USD",
      date: "Sep 28, 2026",
      status: "posted",
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleOpenDispute = (tx: Transaction) => {
    setSelectedTransaction(tx);
    setIsModalOpen(true);
  };

  const handleSubmitDispute = async (disputeData: {
    transactionId: string;
    reason: string;
    details: string;
  }) => {
    // 1. Update status locally
    setMockTransactions((prev) =>
      prev.map((tx) =>
        tx.id === disputeData.transactionId ? { ...tx, status: "disputed" } : tx
      )
    );

    // 2. Append confirmation message to chat
    const refId = `DISP-${Math.floor(100000 + Math.random() * 900000)}`;
    const confirmMessage: Message = {
      id: Date.now().toString(),
      sender: "assistant",
      text: `Your dispute claim for transaction ${disputeData.transactionId} has been successfully submitted.\n\n` +
            `• Reference ID: ${refId}\n` +
            `• Reason: ${disputeData.reason}\n` +
            `• Status: Under Review`,
      action: "CONFIRM_DISPUTE",
    };

    setMessages((prev) => [...prev, confirmMessage]);
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input;
    setInput("");

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: userText,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await sendChatMessage({
        session_id: "SESS_FE_MAIN",
        message: userText,
        language: "es",
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text: response.message || "Request processed.",
        intent: response.intent_detected,
        action: response.action,
        confidence: response.confidence,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: `Error processing request: ${err.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "550px",
        width: "100%",
        maxWidth: "600px",
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        backgroundColor: "#ffffff",
        overflow: "hidden",
      }}
    >
      <div style={{ flex: 1, padding: "1rem", overflowY: "auto" }}>
        {messages.map((msg) => (
          <div key={msg.id}>
            <ChatMessage message={msg} />

            {/* Render transaction list when an INITIATE_DISPUTE_WORKFLOW action is triggered */}
            {msg.action === "INITIATE_DISPUTE_WORKFLOW" && (
              <div style={{ margin: "0.5rem 0 1rem 0" }}>
                <div
                  style={{
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    color: "#4b5563",
                    marginBottom: "0.25rem",
                  }}
                >
                  Select a transaction to dispute:
                </div>
                {mockTransactions.map((tx) => (
                  <TransactionCard
                    key={tx.id}
                    transaction={tx}
                    onSelectDispute={handleOpenDispute}
                  />
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ color: "#9ca3af", fontStyle: "italic", fontSize: "0.875rem" }}>
            Analyzing intent...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={handleSend}
        style={{
          display: "flex",
          borderTop: "1px solid #e5e7eb",
          padding: "0.5rem",
          backgroundColor: "#f9fafb",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          style={{
            flex: 1,
            padding: "0.5rem 0.75rem",
            border: "1px solid #d1d5db",
            borderRadius: "6px",
            marginRight: "0.5rem",
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#2563eb",
            color: "#ffffff",
            border: "none",
            borderRadius: "6px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          Send
        </button>
      </form>

      {/* Dispute Modal */}
      <DisputeModal
        transaction={selectedTransaction}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmitDispute={handleSubmitDispute}
      />
    </div>
  );
};