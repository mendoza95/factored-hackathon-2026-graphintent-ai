// src/components/ChatBox.tsx

import React, { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api/chat";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "./ChatMessage";
import type { Transaction } from "../types/transaction";
import { DisputeModal } from "./DisputeModal";
import { DisputeDetailsModal } from "./DisputeDetailsModal";
import { createDispute } from "../api/dispute";

export const ChatBox: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      sender: "assistant",
      text: "¡Hola! ¿En qué puedo ayudarte con tu cuenta o disputas de transacciones hoy?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Modal de disputas
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Modal de detalles de reclamo
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [disputeDetails, setDisputeDetails] = useState<{
    referenceId: string;
    reason: string;
    status: string;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleOpenDispute = (tx: Transaction) => {
    setSelectedTransaction(tx);
    setIsModalOpen(true);
  };

  const handleViewDisputeDetails = (tx: Transaction) => {
    setSelectedTransaction(tx);
    setIsDetailsModalOpen(true);
  };

  const handleSubmitDispute = async (disputeData: {
    transactionId: string;
    reason: string;
    details: string;
  }) => {
    try {
      const result = await createDispute({
        transaction_id: disputeData.transactionId,
        reason: disputeData.reason,
        details: disputeData.details,
      });

      // Marca la transacción disputada en los mensajes del chat
      setMessages((prevMessages) =>
        prevMessages.map((msg) => {
          if (msg.contextData?.selectable_options) {
            const updatedOptions = msg.contextData.selectable_options.map((opt: any) => {
              const currentId = String(opt.transaction_data?.id || opt.value || opt.id);
              if (currentId === String(disputeData.transactionId)) {
                return {
                  ...opt,
                  already_disputed: true,
                  transaction_data: {
                    ...opt.transaction_data,
                    status: "disputed",
                    already_disputed: true,
                  },
                };
              }
              return opt;
            });
            return {
              ...msg,
              contextData: {
                ...msg.contextData,
                selectable_options: updatedOptions,
              },
            };
          }
          return msg;
        })
      );

      setDisputeDetails({
        referenceId: result.dispute_id || "DISP-SUCCESS",
        reason: disputeData.reason || "unauthorized",
        status: "En Revisión",
      });

      setIsModalOpen(false);
    } catch (err: any) {
      alert(`Error al enviar la disputa: ${err.message}`);
    }
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
        text: response.message || response.response_message || "Solicitud procesada.",
        intent: response.intent_detected,
        action: response.action,
        confidence: response.confidence,
        contextData: response.context_data,
      };

      // Solo agregamos la respuesta a los mensajes
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: `Error procesando la solicitud: ${err.message}`,
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
          <ChatMessage
            key={msg.id}
            message={msg}
            onOpenDisputeModal={handleOpenDispute}
            onViewDisputeDetails={handleViewDisputeDetails}
          />
        ))}

        {loading && (
          <div style={{ color: "#9ca3af", fontStyle: "italic", fontSize: "0.875rem" }}>
            Analizando intención...
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
          placeholder="Escribe tu mensaje..."
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
          Enviar
        </button>
      </form>

      {/* Modal para crear disputa */}
      <DisputeModal
        transaction={selectedTransaction}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmitDispute={handleSubmitDispute}
      />

      {/* Modal para ver detalles del reclamo */}
      <DisputeDetailsModal
        transaction={selectedTransaction}
        disputeData={disputeDetails}
        isOpen={isDetailsModalOpen}
        onClose={() => setIsDetailsModalOpen(false)}
      />
    </div>
  );
};