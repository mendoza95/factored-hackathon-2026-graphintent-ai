// src/components/LoginForm.tsx
import React, { useState } from "react";
import { apiClient } from "../api/client";

interface LoginFormProps {
  onSuccess: (token: string) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const [documentType, setDocumentType] = useState<string>("CC");
  const [documentNumber, setDocumentNumber] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Intentando iniciar sesión con:", { documentType, documentNumber });

    if (!documentNumber.trim()) {
      setError("Ingresa un número de documento válido.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post("/auth/login", {
        document_type: documentType,
        document_number: documentNumber,
      });

      console.log("Respuesta exitosa del servidor:", response.data);
      onSuccess(response.data.access_token);
    } catch (err: any) {
      console.error("Detalle completo del error al iniciar sesión:", err);

      if (err.response) {
        // El servidor respondió con un status fuera del rango 2xx
        console.error("Status del error:", err.response.status);
        console.error("Datos de la respuesta:", err.response.data);

        const detail = err.response.data?.detail;
        if (typeof detail === "string") {
          setError(detail);
        } else if (Array.isArray(detail)) {
          // Errores de validación de Pydantic (FastAPI)
          const msg = detail.map((d: any) => d.msg).join(", ");
          setError(`Error de validación: ${msg}`);
        } else {
          setError(`Error ${err.response.status}: Revisa los datos ingresados.`);
        }
      } else if (err.request) {
        // La petición fue enviada pero no se recibió respuesta
        console.error("No se recibió respuesta del servidor:", err.request);
        setError("No se pudo conectar con el servidor. Revisa tu conexión.");
      } else {
        // Ocurrió un error al configurar la petición
        console.error("Error de configuración/petición:", err.message);
        setError(`Error inesperado: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        border: "1px solid #ccc",
        borderRadius: "8px",
        padding: "2rem",
        backgroundColor: "#f9f9f9",
        marginTop: "1rem",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Iniciar Sesión</h3>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>
            Tipo de Documento:
          </label>
          <select
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ccc" }}
          >
            <option value="CC">Cédula de Ciudadanía (CC)</option>
            <option value="CE">Cédula de Extranjería (CE)</option>
            <option value="PASAPORTE">Pasaporte</option>
            <option value="NIT">NIT</option>
          </select>
        </div>

        <div>
          <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: "bold" }}>
            Número de Documento:
          </label>
          <input
            type="text"
            value={documentNumber}
            onChange={(e) => setDocumentNumber(e.target.value)}
            placeholder="Ej: 1234567890"
            style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #ccc" }}
          />
        </div>

        {error && <div style={{ color: "red", fontSize: "0.9rem" }}>{error}</div>}

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "0.75rem",
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: "bold",
          }}
        >
          {loading ? "Verificando..." : "Ingresar"}
        </button>
      </form>
    </div>
  );
};