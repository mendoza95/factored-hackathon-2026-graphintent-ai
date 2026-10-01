import React from "react";

export interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  intent?: string;
  action?: string;
  confidence?: number;
}

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        margin: "0.75rem 0",
      }}
    >
      <div
        style={{
          maxWidth: "75%",
          padding: "0.75rem 1rem",
          borderRadius: "12px",
          backgroundColor: isUser ? "#2563eb" : "#f3f4f6",
          color: isUser ? "#ffffff" : "#1f2937",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{message.text}</p>
        
        {!isUser && message.intent && (
          <div
            style={{
              marginTop: "0.5rem",
              paddingTop: "0.5rem",
              borderTop: "1px solid #e5e7eb",
              fontSize: "0.75rem",
              color: "#6b7280",
              display: "flex",
              gap: "0.5rem",
              flexWrap: "wrap",
            }}
          >
            <span><strong>Intent:</strong> {message.intent}</span>
            {message.confidence !== undefined && (
              <span><strong>Conf:</strong> {(message.confidence * 100).toFixed(0)}%</span>
            )}
            {message.action && <span><strong>Action:</strong> {message.action}</span>}
          </div>
        )}
      </div>
    </div>
  );
};