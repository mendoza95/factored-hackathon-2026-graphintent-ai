// src/App.tsx
import { useAuth } from "./context/AuthContext";
import { ChatBox } from "./components/ChatBox";
import { LoginForm } from "./components/LoginForm";

export function App() {
  const { isAuthenticated, login, logout } = useAuth();

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: "800px", margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
        }}
      >
        <h2>Financial Dispute Assistant</h2>
        {isAuthenticated && <button onClick={logout}>Cerrar Sesión</button>}
      </header>

      {isAuthenticated ? (
        <ChatBox />
      ) : (
        <LoginForm onSuccess={(token) => login(token)} />
      )}
    </div>
  );
}

export default App;