import { useState } from "react";
import axios from "axios";
import GoogleSignIn from "./components/GoogleSignButton";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function LoginPage({ onLoginSuccess }) {
  const [mode, setMode] = useState("login");
  const [role, setRole] = useState("patient");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    phone: "",
    specialization: "",
    hospital: "",
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError("");
  };

  const handleSubmit = async () => {
    if (!form.email || !form.password) {
      setError("Email and password are required");
      return;
    }
    if (mode === "signup" && !form.name) {
      setError("Name is required");
      return;
    }

    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/signup";
      const payload =
        mode === "login"
          ? { email: form.email, password: form.password, role }
          : { ...form, role };

      const res = await axios.post(`${API_BASE}${endpoint}`, payload);

      localStorage.setItem("token", res.data.token);
      localStorage.setItem("role", res.data.role);
      localStorage.setItem("name", res.data.name);
      localStorage.setItem("email", res.data.email);

      onLoginSuccess(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.shell}>
      <div style={S.container}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={S.title}>Medicate-IT</h1>
          <p
            style={{
              color: "#475569",
              fontFamily: "monospace",
              fontSize: 13,
              letterSpacing: 2,
            }}
          >
            Rapido but for MEDICAL Treatment!
          </p>
        </div>

        <div style={S.card}>
          {/* Role Toggle */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                color: "#334155",
                fontFamily: "monospace",
                fontSize: 12,
                letterSpacing: 1,
                marginBottom: 8,
              }}
            >
              I AM A
            </div>
            <div
              style={{
                display: "flex",
                borderRadius: 8,
                overflow: "hidden",
                border: "1px solid #1e293b",
              }}
            >
              {["patient", "doctor"].map((r) => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  style={{
                    flex: 1,
                    padding: "10px",
                    border: "none",
                    cursor: "pointer",
                    fontFamily: "monospace",
                    fontSize: 14,
                    fontWeight: 700,
                    letterSpacing: 1,
                    textTransform: "uppercase",
                    transition: "all 0.2s",
                    background: role === r ? "#0ea5e9" : "#0f172a",
                    color: role === r ? "#020617" : "#475569",
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* Mode Toggle */}
          <div style={{ display: "flex", gap: 24, marginBottom: 20 }}>
            {["login", "signup"].map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontFamily: "monospace",
                  fontSize: 14,
                  fontWeight: 700,
                  letterSpacing: 1,
                  textTransform: "uppercase",
                  paddingBottom: 4,
                  transition: "all 0.2s",
                  color: mode === m ? "#0ea5e9" : "#334155",
                  borderBottom:
                    mode === m ? "2px solid #0ea5e9" : "2px solid transparent",
                }}
              >
                {m}
              </button>
            ))}
          </div>

          {/* Form Fields */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {mode === "signup" && (
              <input
                name="name"
                placeholder="Full Name"
                value={form.name}
                onChange={handleChange}
                style={S.input}
              />
            )}

            <input
              name="email"
              type="email"
              placeholder="Email Address"
              value={form.email}
              onChange={handleChange}
              style={S.input}
            />

            <input
              name="password"
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={handleChange}
              style={S.input}
            />

            {mode === "signup" && (
              <input
                name="phone"
                placeholder="Phone Number (optional)"
                value={form.phone}
                onChange={handleChange}
                style={S.input}
              />
            )}

            {mode === "signup" && role === "doctor" && (
              <>
                <input
                  name="specialization"
                  placeholder="Specialization (e.g. Cardiologist)"
                  value={form.specialization}
                  onChange={handleChange}
                  style={S.input}
                />
                <input
                  name="hospital"
                  placeholder="Hospital / Clinic Name"
                  value={form.hospital}
                  onChange={handleChange}
                  style={S.input}
                />
              </>
            )}
          </div>

          {/* Error */}
          {error && (
            <div
              style={{
                background: "#1a0a0a",
                border: "1px solid #7f1d1d",
                borderRadius: 8,
                padding: "10px 14px",
                marginTop: 12,
              }}
            >
              <p
                style={{
                  color: "#fca5a5",
                  fontSize: 14,
                  margin: 0,
                  fontFamily: "monospace",
                }}
              >
                ⚠ {error}
              </p>
            </div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={loading}
            style={{
              ...S.primaryBtn,
              marginTop: 16,
              opacity: loading ? 0.6 : 1,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Login"
                : "Create Account"}
          </button>

          {/* Footer hint */}
          <p
            style={{
              color: "#334155",
              fontSize: 13,
              textAlign: "center",
              fontFamily: "monospace",
              marginTop: 12,
              marginBottom: 0,
            }}
          >
            {mode === "login"
              ? "No account? Click SIGNUP above."
              : "Already registered? Click LOGIN above."}
          </p>
        <GoogleSignIn onLoginSuccess={onLoginSuccess}/>
        </div>
      </div>
    </div>
  );
}

const S = {
  shell: {
    minHeight: "100vh",
    background: "#020617",
    color: "#e2e8f0",
    fontFamily: "Georgia,'Times New Roman',serif",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "24px 16px",
  },
  container: {
    width: "100%",
    maxWidth: 420,
  },
  title: {
    fontFamily: "'Courier New',Courier,monospace",
    color: "#e2e8f0",
    fontWeight: 800,
    letterSpacing: 2,
    margin: "0 0 6px 0",
    fontSize: "clamp(24px, 6vw, 32px)",
  },
  card: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: 14,
    padding: "24px",
  },
  input: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 8,
    border: "1px solid #1e293b",
    background: "#020617",
    color: "#e2e8f0",
    fontSize: 15,
    fontFamily: "monospace",
    outline: "none",
    boxSizing: "border-box",
    transition: "border-color 0.2s",
  },
  primaryBtn: {
    width: "100%",
    padding: "14px 20px",
    background: "linear-gradient(135deg,#0ea5e9,#6366f1)",
    color: "white",
    border: "none",
    borderRadius: 10,
    fontSize: 15,
    fontFamily: "'Courier New',monospace",
    fontWeight: 700,
    letterSpacing: 1,
    transition: "all 0.2s",
    boxSizing: "border-box",
  },
};
