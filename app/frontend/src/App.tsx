import { useAuth } from "./context/AuthContext";
import { ChatBox } from "./components/ChatBox";
import { apiClient } from "./api/client";

export function App() {
  const { isAuthenticated, login, logout } = useAuth();

  const handleLogin = async () => {
    try {
      const res = await apiClient.get("/auth/token");
      login(res.data.access_token);
    } catch (err: any) {
      console.error("Login failed:", err);
    }
  };

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
        {isAuthenticated ? (
          <button onClick={logout}>Logout</button>
        ) : (
          <button onClick={handleLogin}>Log In (Test Token)</button>
        )}
      </header>

      {isAuthenticated ? (
        <ChatBox />
      ) : (
        <p>Please log in using the test token button above to access the dispute assistant.</p>
      )}
    </div>
  );
}

export default App;