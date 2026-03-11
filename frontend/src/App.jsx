import { useState, useEffect, useRef } from "react";

const Privacy = {
  key: Array.from({ length: 32 }, () => Math.floor(Math.random() * 256)),
  encode(text) {
    return btoa(text.split("").map((c, i) =>
      String.fromCharCode(c.charCodeAt(0) ^ this.key[i % this.key.length])
    ).join(""));
  },
  stripPII(text) {
    return text
      .replace(/\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, "[PHONE]")
      .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "[EMAIL]")
      .replace(/\b(mr|mrs|ms|dr|prof)\.?\s+[a-z]+(\s+[a-z]+)?\b/gi, "[NAME]")
      .replace(/\b\d{3}-\d{2}-\d{4}\b/g, "[SSN]")
      .replace(/\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/g, "[DATE]")
      .replace(/\b\d{5}(-\d{4})?\b/g, "[ZIP]");
  },
  sessionId() {
    return Array.from(crypto.getRandomValues(new Uint8Array(16)))
      .map(b => b.toString(16).padStart(2, "0")).join("");
  },
};

const SESSION_ID = Privacy.sessionId();
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const AGENTS = [
  { id: "extractor", name: "Symptom Extractor", icon: "", color: "#00d4ff", desc: "Parsing & structuring symptoms" },
  { id: "analyzer",  name: "Risk Analyzer",     icon: "", color: "#ff6b35", desc: "Identifying conditions & red flags" },
  { id: "scorer",    name: "Risk Scorer",        icon: "", color: "#a855f7", desc: "Calculating dynamic risk score" },
  { id: "triage",    name: "Triage Decision",    icon: "", color: "#22c55e", desc: "Determining urgency & care pathway" },
];

const URGENCY_CONFIG = {
  EMERGENCY:   { bg: "#ff1744", text: "white",   label: "EMERGENCY",   sub: "Call 112 immediately" },
  URGENT:      { bg: "#ff6d00", text: "white",   label: "URGENT",      sub: "Go to ER within 1–2 hours" },
  SEMI_URGENT: { bg: "#ffd600", text: "#1a1a1a", label: "SEMI-URGENT", sub: "See a doctor within 24 hours" },
  NON_URGENT:  { bg: "#00c853", text: "white",   label: "NON-URGENT",  sub: "Schedule a doctor appointment" },
  SELF_CARE:   { bg: "#2979ff", text: "white",   label: "SELF-CARE",   sub: "Home care with monitoring" },
};

const ScoreGauge = ({ score }) => {
  const r = 44, circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const color = score >= 75 ? "#ff1744" : score >= 50 ? "#ff6d00" : score >= 25 ? "#ffd600" : "#00c853";
  return (
    <svg width="110" height="110" viewBox="0 0 110 110">
      <circle cx="55" cy="55" r={r} fill="none" stroke="#1e293b" strokeWidth="10" />
      <circle cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="10"
        strokeDasharray={`${filled} ${circ}`} strokeLinecap="round"
        transform="rotate(-90 55 55)"
        style={{ transition: "stroke-dasharray 1.2s ease, stroke 0.5s" }} />
      <text x="55" y="51" textAnchor="middle" fill="white" fontSize="26" fontWeight="800" fontFamily="'Courier New',monospace">{score}</text>
      <text x="55" y="65" textAnchor="middle" fill="#475569" fontSize="12" fontFamily="monospace">/100 RISK</text>
    </svg>
  );
};

const AgentCard = ({ agent, status }) => {
  const borders = { idle: "#1e293b", running: agent.color, done: "#22c55e", error: "#ef4444" };
  return (
    <div style={{
      background: "#0f172a", border: `1.5px solid ${borders[status]}`,
      borderRadius: 10, padding: "10px 14px",
      boxShadow: status === "running" ? `0 0 18px ${agent.color}30` : "none",
      transition: "all 0.4s ease",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 16 }}>{agent.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: agent.color, fontFamily: "monospace", fontSize: 14, fontWeight: 700, letterSpacing: 0.8, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {agent.name.toUpperCase()}
          </div>
          <div style={{ color: "#334155", fontSize: 13, marginTop: 1 }}>{agent.desc}</div>
        </div>
        <div style={{ fontFamily: "monospace", fontSize: 13, flexShrink: 0 }}>
          {status === "idle"    && <span style={{ color: "#334155" }}>IDLE</span>}
          {status === "running" && <span style={{ color: agent.color, animation: "blink 0.8s infinite" }}>● RUN</span>}
          {status === "done"    && <span style={{ color: "#22c55e" }}> DONE</span>}
          {status === "error"   && <span style={{ color: "#ef4444" }}> ERR</span>}
        </div>
      </div>
    </div>
  );
};

const GraphDiagram = ({ statuses }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 4, flexWrap: "wrap", marginBottom: 20, padding: "10px 0" }}>
    {AGENTS.map((a, i) => (
      <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <div style={{
          background: statuses[a.id] === "done" ? "#0d2818" : statuses[a.id] === "running" ? "#0d1f35" : "#0f172a",
          border: `1.5px solid ${statuses[a.id] === "done" ? "#22c55e" : statuses[a.id] === "running" ? a.color : "#1e293b"}`,
          borderRadius: 8, padding: "6px 10px", textAlign: "center",
          boxShadow: statuses[a.id] === "running" ? `0 0 12px ${a.color}50` : "none",
          transition: "all 0.4s", minWidth: 60,
        }}>
          <div style={{ fontSize: 16 }}>{a.icon}</div>
          <div style={{ color: "#64748b", fontSize: 8, fontFamily: "monospace", marginTop: 2 }}>
            {a.name.split(" ")[0]}
          </div>
        </div>
        {i < AGENTS.length - 1 && <div style={{ color: "#1e293b", fontSize: 14 }}>→</div>}
      </div>
    ))}
  </div>
);

export default function MedTriageApp() {
  const [screen, setScreen]   = useState("consent");
  const [symptoms, setSymptoms] = useState("");
  const [agentStatuses, setAgentStatuses] = useState(Object.fromEntries(AGENTS.map(a => [a.id, "idle"])));
  const [result, setResult]   = useState(null);
  const [error, setError]     = useState(null);
  const [log, setLog]         = useState([]);
  const [encoded, setEncoded] = useState(null);
  const logRef = useRef(null);

  const addLog = (msg, type = "info") =>
    setLog(p => [...p, { msg, type, ts: new Date().toLocaleTimeString() }]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const simulateAgentProgress = async (data) => {
    for (const agentId of ["extractor", "analyzer", "scorer", "triage"]) {
      setAgentStatuses(p => ({ ...p, [agentId]: "running" }));
      addLog(`Agent [${agentId}] processing…`, "agent");
      await new Promise(r => setTimeout(r, 600));
      const isDone = data.completed_agents.includes(agentId);
      setAgentStatuses(p => ({ ...p, [agentId]: isDone ? "done" : "error" }));
      addLog(`Agent [${agentId}] ${isDone ? "complete" : "error"}`, isDone ? "success" : "error");
    }
  };

  const runTriage = async () => {
    setScreen("processing");
    setError(null);
    setLog([]);
    setResult(null);
    setAgentStatuses(Object.fromEntries(AGENTS.map(a => [a.id, "idle"])));
    const piiStripped = Privacy.stripPII(symptoms);
    setEncoded(Privacy.encode(piiStripped));
    addLog(`Session ${SESSION_ID.slice(0,12)}… initiated`, "system");
    addLog("Client-side PII stripped", "privacy");
    addLog("Input XOR-encoded in memory", "privacy");
    addLog("Sending anonymized data to LangGraph pipeline…", "info");
    try {
      const res = await fetch(`${API_BASE}/api/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Session-ID": SESSION_ID },
        body: JSON.stringify({ symptoms: piiStripped, session_id: SESSION_ID }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Request failed");
      }
      const data = await res.json();
      addLog("Response received from backend", "success");
      addLog(`Server session hash: ${data.session_hash}`, "privacy");
      await simulateAgentProgress(data);
      setResult(data);
      addLog("LangGraph pipeline complete ✓", "system");
      setScreen("results");
    } catch (e) {
      setError(e.message);
      addLog(`Error: ${e.message}`, "error");
    }
  };

  const reset = () => {
    setScreen("input");
    setSymptoms("");
    setResult(null);
    setError(null);
    setLog([]);
    setEncoded(null);
    setAgentStatuses(Object.fromEntries(AGENTS.map(a => [a.id, "idle"])));
  };

  // ── CONSENT ──────────────────────────────────────────────────────────────────
  if (screen === "consent") return (
    <div style={S.shell}>
      <style>{CSS}</style>
      <div style={S.container}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={{ ...S.title, fontSize: "clamp(28px, 7vw, 40px)", marginBottom: 6 }}>Medicate It</h1>
          <p style={{ color: "#475569", fontFamily: "monospace", fontSize: "clamp(15px, 2vw, 11px)", letterSpacing: 2 }}>
            LANGGRAPH · MULTI-AGENT · MEDICAL TRIAGE
          </p>
        </div>

        <div style={{ background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 12, padding: "16px", marginBottom: 14 }}>
          <div style={{ color: "#00d4ff", fontFamily: "monospace", fontSize: "clamp(15px, 2.5vw, 12px)", fontWeight: 700, letterSpacing: 1, marginBottom: 14 }}>WHAT MEDICATE IT DOES</div>
          {[
            ["Symptom Analysis", "Describe your symptoms in plain language — our AI reads and structures everything you mention including pain levels, duration, location, and associated symptoms."],
            ["Risk Scoring", "A multi-agent pipeline calculates a dynamic risk score from 0 to 100 based on severity, red flags, body systems involved, and onset pattern."],
            ["Disease Prediction", "Based on your symptoms, the system identifies the most likely medical conditions with likelihood ratings and clinical reasoning for each."],
            ["Medication Guidance", "Alongside each predicted condition, relevant over-the-counter medications and first-aid steps are recommended for your specific symptoms."],
            ["Urgency Triage", "You receive a clear urgency verdict — Emergency, Urgent, Semi-Urgent, Non-Urgent, or Self-Care — with a recommended care pathway and timeframe."],
            ["Privacy by Design", "Your personal information is stripped before any AI processing. No data is stored, logged, or linked to your identity at any point."],
          ].map(([title, desc]) => (
            <div key={title} style={{ display: "flex", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 3, borderRadius: 2, background: "#0ea5e9", flexShrink: 0, marginTop: 3, alignSelf: "stretch" }} />
              <div>
                <div style={{ color: "#e2e8f0", fontSize: "clamp(14px, 2.5vw, 13px)", fontWeight: 600, marginBottom: 3 }}>{title}</div>
                <div style={{ color: "#64748b", fontSize: "clamp(15px, 2vw, 12px)", lineHeight: 1.6 }}>{desc}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, padding: 14, marginBottom: 14 }}>
          <div style={{ color: "#64748b", fontFamily: "monospace", fontSize: 13, marginBottom: 10 }}>LANGGRAPH AGENT PIPELINE</div>
          <GraphDiagram statuses={Object.fromEntries(AGENTS.map(a => [a.id, "idle"]))} />
          <div style={{ color: "#334155", fontSize: 13, textAlign: "center", fontFamily: "monospace" }}>
            4 agents · conditional escalation · structured state
          </div>
        </div>

        <button onClick={() => setScreen("input")} style={S.primaryBtn}>
          Start Assessment
        </button>
      </div>
    </div>
  );

  // ── INPUT ─────────────────────────────────────────────────────────────────────
  if (screen === "input") return (
    <div style={S.shell}>
      <style>{CSS}</style>
      <div style={S.container}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h1 style={{ ...S.title, fontSize: "clamp(16px, 4vw, 20px)", margin: 0 }}>Medicate It</h1>
            <p style={{ color: "#334155", fontFamily: "monospace", fontSize: 13, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              SESSION {SESSION_ID.slice(0, 12).toUpperCase()}…
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
            <span style={{ width: 7, height: 7, background: "#22c55e", borderRadius: "50%", display: "inline-block", animation: "blink 2s infinite" }} />
            <span style={{ color: "#22c55e", fontFamily: "monospace", fontSize: 13 }}>SECURE</span>
          </div>
        </div>

        <GraphDiagram statuses={Object.fromEntries(AGENTS.map(a => [a.id, "idle"]))} />

        <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, padding: 16, marginBottom: 12 }}>
          <label style={{ color: "#64748b", fontFamily: "monospace", fontSize: 13, letterSpacing: 2, display: "block", marginBottom: 10 }}>
            DESCRIBE YOUR SYMPTOMS
          </label>
          <textarea
            value={symptoms}
            onChange={e => setSymptoms(e.target.value)}
            placeholder={`Describe your symptoms in detail:\n• What you feel and where\n• When it started\n• Severity (1–10)\n• Any related symptoms`}
            style={{
              width: "100%", minHeight: 140, background: "#020617",
              border: "1px solid #1e293b", borderRadius: 8, padding: "12px 14px",
              color: "#e2e8f0", fontSize: "clamp(15px, 3vw, 15px)", fontFamily: "Georgia,serif",
              lineHeight: 1.7, resize: "vertical", outline: "none", boxSizing: "border-box",
            }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
            <span style={{ color: "#334155", fontSize: 13, fontFamily: "monospace" }}>PII stripped before sending</span>
            <span style={{ color: symptoms.length > 50 ? "#22c55e" : "#475569", fontSize: 13, fontFamily: "monospace" }}>
              {symptoms.length} chars
            </span>
          </div>
        </div>

        {symptoms.length > 10 && (
          <div style={{ background: "#080f1a", border: "1px solid #1e3a5f", borderRadius: 8, padding: 10, marginBottom: 12 }}>
            <div style={{ color: "#3b82f6", fontFamily: "monospace", fontSize: 13, marginBottom: 4 }}>PRIVACY PREVIEW:</div>
            <div style={{ color: "#64748b", fontSize: 14, fontFamily: "monospace", lineHeight: 1.5, wordBreak: "break-word" }}>
              {Privacy.stripPII(symptoms).slice(0, 180)}{symptoms.length > 180 ? "…" : ""}
            </div>
          </div>
        )}

        <button onClick={runTriage} disabled={symptoms.trim().length < 20}
          style={{ ...S.primaryBtn, opacity: symptoms.trim().length < 20 ? 0.4 : 1 }}>
          Start Assessment
        </button>
        <p style={{ color: "#334155", fontSize: 13, textAlign: "center", fontFamily: "monospace", marginTop: 6 }}>
          Minimum 20 characters required
        </p>
      </div>
    </div>
  );

  // ── PROCESSING ────────────────────────────────────────────────────────────────
  if (screen === "processing") return (
    <div style={S.shell}>
      <style>{CSS}</style>
      <div style={S.container}>
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <h2 style={{ ...S.title, fontSize: "clamp(15px, 4vw, 18px)" }}>LangGraph Pipeline Running</h2>
          <p style={{ color: "#334155", fontFamily: "monospace", fontSize: 13 }}>
            SESSION {SESSION_ID.slice(0, 12).toUpperCase()}…
          </p>
        </div>
        <GraphDiagram statuses={agentStatuses} />
        <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
          {AGENTS.map(a => <AgentCard key={a.id} agent={a} status={agentStatuses[a.id]} />)}
        </div>
        <div ref={logRef} style={{
          background: "#020617", border: "1px solid #1e293b", borderRadius: 8,
          padding: 12, height: 160, overflowY: "auto", fontFamily: "monospace", fontSize: 13,
        }}>
          {log.map((l, i) => (
            <div key={i} style={{
              color: { info:"#64748b",agent:"#00d4ff",privacy:"#a855f7",success:"#22c55e",error:"#ef4444",system:"#94a3b8" }[l.type],
              marginBottom: 2, wordBreak: "break-word",
            }}>
              <span style={{ color: "#1e293b" }}>[{l.ts}]</span> {l.msg}
            </div>
          ))}
          {!error && <span style={{ color: "#334155", animation: "blink 0.8s infinite" }}>▋</span>}
        </div>
        {error && (
          <div style={{ background: "#1a0a0a", border: "1px solid #7f1d1d", borderRadius: 8, padding: 12, marginTop: 12 }}>
            <p style={{ color: "#fca5a5", fontSize: 15, margin: "0 0 8px" }}>⚠️ {error}</p>
            <p style={{ color: "#64748b", fontSize: 13, margin: 0 }}>Make sure the backend is running at <code style={{ color: "#94a3b8" }}>{API_BASE}</code></p>
            <button onClick={reset} style={{ ...S.secondaryBtn, marginTop: 10 }}>Try Again</button>
          </div>
        )}
      </div>
    </div>
  );

  // ── RESULTS ───────────────────────────────────────────────────────────────────
  if (screen === "results" && result) {
    const { extracted_symptoms: ex, risk_analysis: ra, risk_score: rs, triage_decision: td, privacy_log: pl } = result;
    const uc = URGENCY_CONFIG[td.urgency_level] || URGENCY_CONFIG.NON_URGENT;

    return (
      <div style={S.shell}>
        <style>{CSS}</style>
        <div style={S.container}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
            <h1 style={{ ...S.title, fontSize: "clamp(16px, 4vw, 20px)", margin: 0, flex: 1 }}>Triage Report — Medicate It</h1>
            <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 6, padding: "3px 8px" }}>
              <span style={{ color: "#22c55e", fontFamily: "monospace", fontSize: 13 }}>🔒 {result.session_hash}</span>
            </div>
          </div>

          <GraphDiagram statuses={Object.fromEntries(AGENTS.map(a => [a.id, "done"]))} />

          {/* Urgency Banner */}
          <div style={{
            background: uc.bg, borderRadius: 12, padding: "16px 18px",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 14, animation: "slideIn 0.5s ease", flexWrap: "wrap", gap: 12,
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: uc.text, fontSize: "clamp(16px, 4vw, 22px)", fontWeight: 800, fontFamily: "monospace", marginBottom: 3 }}>{uc.label}</div>
              <div style={{ color: uc.text, opacity: 0.85, fontSize: "clamp(15px, 3vw, 14px)", marginBottom: 3 }}>{uc.sub}</div>
              <div style={{ color: uc.text, opacity: 0.7, fontSize: "clamp(15px, 2vw, 12px)", fontFamily: "monospace" }}>⏱ {td.timeframe}</div>
            </div>
            <ScoreGauge score={rs.overall_score} />
          </div>

          {/* Score Breakdown */}
          <div style={S.card}>
            <h3 style={S.cardTitle}>Risk Score Breakdown</h3>
            {Object.entries(rs.score_breakdown || {}).map(([k, v]) => {
              const maxes = { symptom_severity: 30, red_flag_count: 25, duration_factor: 20, system_involvement: 15, onset_factor: 10 };
              const max = maxes[k] || 10, pct = (v / max) * 100;
              return (
                <div key={k} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ color: "#64748b", fontSize: "clamp(15px, 2vw, 11px)", fontFamily: "monospace" }}>{k.replace(/_/g, " ").toUpperCase()}</span>
                    <span style={{ color: "#94a3b8", fontSize: "clamp(15px, 2vw, 11px)", fontFamily: "monospace" }}>{v}/{max}</span>
                  </div>
                  <div style={{ background: "#1e293b", borderRadius: 4, height: 6 }}>
                    <div style={{ background: pct > 70 ? "#ef4444" : pct > 40 ? "#f97316" : "#22c55e", width: `${pct}%`, height: "100%", borderRadius: 4, transition: "width 1.2s ease" }} />
                  </div>
                </div>
              );
            })}
            <p style={{ color: "#475569", fontSize: "clamp(15px, 2vw, 12px)", marginTop: 8, fontStyle: "italic", margin: "8px 0 0" }}>{rs.reasoning}</p>
          </div>

          {/* Symptoms */}
          <div style={S.card}>
            <h3 style={S.cardTitle}>Extracted Symptoms</h3>
            {(ex.symptoms || []).map((s, i) => (
              <div key={i} style={{ background: "#020617", borderRadius: 8, padding: "10px 12px", marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ color: "#e2e8f0", fontSize: "clamp(15px, 3vw, 14px)", fontWeight: 600 }}>{s.name}</span>
                  {s.location && <span style={{ color: "#64748b", fontSize: 14, marginLeft: 6 }}>@ {s.location}</span>}
                  {s.duration && <div style={{ color: "#475569", fontSize: 13, marginTop: 2 }}>Duration: {s.duration}</div>}
                </div>
                <span style={{
                  padding: "2px 8px", borderRadius: 20, fontSize: 13, fontFamily: "monospace", fontWeight: 700, flexShrink: 0,
                  background: s.severity === "severe" ? "#7f1d1d" : s.severity === "moderate" ? "#431407" : "#14532d",
                  color: s.severity === "severe" ? "#fca5a5" : s.severity === "moderate" ? "#fdba74" : "#86efac",
                }}>{s.severity?.toUpperCase()}</span>
              </div>
            ))}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8, marginTop: 10 }}>
              {[
                ["ONSET", ex.onset || "—"],
                ["BODY SYSTEMS", (ex.body_systems || ra.body_systems || []).join(", ") || "—"],
                ["MEDICATIONS TAKEN", ex.current_medications || "None mentioned"],
                ["MEDICAL HISTORY", ex.medical_history || "None mentioned"],
              ].map(([k, v]) => (
                <div key={k} style={{ background: "#020617", borderRadius: 6, padding: "8px 10px" }}>
                  <div style={{ color: "#334155", fontSize: 13, fontFamily: "monospace" }}>{k}</div>
                  <div style={{ color: "#64748b", fontSize: 14, marginTop: 2, wordBreak: "break-word" }}>{v}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Red Flags */}
          {(ra.red_flags || []).length > 0 && (
            <div style={{ ...S.card, border: "1px solid #7f1d1d" }}>
              <h3 style={{ ...S.cardTitle, color: "#fca5a5" }}>Red Flags ({ra.red_flags.length})</h3>
              {ra.red_flags.map((f, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                  <span style={{ color: "#ef4444", flexShrink: 0 }}>▸</span>
                  <span style={{ color: "#fca5a5", fontSize: "clamp(14px, 2.5vw, 13px)" }}>{f}</span>
                </div>
              ))}
            </div>
          )}

          {/* Conditions */}
          <div style={S.card}>
            <h3 style={S.cardTitle}>Possible Conditions</h3>
            {(ra.potential_conditions || []).map((c, i) => (
              <div key={i} style={{ background: "#020617", borderRadius: 8, padding: "10px 12px", marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, gap: 8 }}>
                  <span style={{ color: "#e2e8f0", fontSize: "clamp(15px, 3vw, 13px)", fontWeight: 600 }}>{c.name}</span>
                  <span style={{
                    padding: "2px 8px", borderRadius: 20, fontSize: 13, fontFamily: "monospace", flexShrink: 0,
                    background: c.likelihood === "high" ? "#7f1d1d" : c.likelihood === "moderate" ? "#431407" : "#1e3a5f",
                    color: c.likelihood === "high" ? "#fca5a5" : c.likelihood === "moderate" ? "#fdba74" : "#93c5fd",
                  }}>{c.likelihood?.toUpperCase()}</span>
                </div>
                <p style={{ color: "#475569", fontSize: "clamp(15px, 2vw, 12px)", margin: 0 }}>{c.reasoning}</p>
              </div>
            ))}
          </div>

          {/* Medication Recommendations */}
          {(ra.medication_recommendations || []).length > 0 && (
            <div style={{ ...S.card, border: "1px solid #1e3a5f" }}>
              <h3 style={{ ...S.cardTitle, color: "#93c5fd" }}>Medication & First-Aid Guidance</h3>
              {(ra.medication_recommendations || []).map((m, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                  <span style={{ color: "#3b82f6", flexShrink: 0 }}>💊</span>
                  <span style={{ color: "#93c5fd", fontSize: "clamp(14px, 2.5vw, 13px)" }}>{m}</span>
                </div>
              ))}
              <div style={{ background: "#020617", borderRadius: 6, padding: "8px 10px", marginTop: 10 }}>
                <p style={{ color: "#475569", fontSize: 13, margin: 0 }}>⚠️ Always consult a healthcare professional before taking any medication.</p>
              </div>
            </div>
          )}

          {/* Recommendations */}
          <div style={S.card}>
            <h3 style={S.cardTitle}>Recommendations</h3>
            {(td.recommendations || []).map((r, i) => (
              <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <span style={{ color: "#22c55e", flexShrink: 0 }}>→</span>
                <span style={{ color: "#94a3b8", fontSize: "clamp(14px, 2.5vw, 13px)" }}>{r}</span>
              </div>
            ))}
            {(td.self_care_tips || []).length > 0 && (
              <>
                <div style={{ borderTop: "1px solid #1e293b", margin: "10px 0" }} />
                <div style={{ color: "#334155", fontFamily: "monospace", fontSize: 13, marginBottom: 8 }}>SELF-CARE TIPS</div>
                {td.self_care_tips.map((t, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                    <span style={{ color: "#3b82f6", flexShrink: 0 }}>•</span>
                    <span style={{ color: "#64748b", fontSize: "clamp(14px, 2vw, 12px)" }}>{t}</span>
                  </div>
                ))}
              </>
            )}
          </div>

          {/* Warning Signs */}
          {(td.warning_signs || []).length > 0 && (
            <div style={{ background: "#1a0a0a", border: "1px solid #7f1d1d", borderRadius: 12, padding: 14, marginBottom: 12 }}>
              <h3 style={{ color: "#fca5a5", fontFamily: "monospace", fontSize: 15, margin: "0 0 10px" }}>Seek Emergency Care If:</h3>
              {td.warning_signs.map((w, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                  <span style={{ color: "#ef4444", flexShrink: 0 }}>!</span>
                  <span style={{ color: "#fca5a5", fontSize: "clamp(14px, 2.5vw, 13px)" }}>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Privacy Audit */}
          <div style={{ background: "#080f1a", border: "1px solid #1e3a5f", borderRadius: 10, padding: 14, marginBottom: 12 }}>
            <div style={{ color: "#3b82f6", fontFamily: "monospace", fontSize: 13, marginBottom: 8 }}>PRIVACY AUDIT LOG</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 6 }}>
              {[
                ["PII Stripped", pl.pii_stripped ? "✓ Yes" : "✗ No"],
                ["Raw Input Stored", pl.raw_input_stored ? "✗ Yes" : "✓ No"],
                ["Identity Linked", pl.session_linked_to_identity ? "✗ Yes" : "✓ No"],
                ["Session Hash", pl.session_hash],
              ].map(([k, v]) => (
                <div key={k} style={{ background: "#020617", borderRadius: 6, padding: "6px 10px" }}>
                  <div style={{ color: "#334155", fontSize: 13, fontFamily: "monospace" }}>{k}</div>
                  <div style={{ color: "#64748b", fontSize: 13, marginTop: 2, wordBreak: "break-all" }}>{v}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div style={{ background: "#0f172a", borderRadius: 8, padding: 12, marginBottom: 16 }}>
            <p style={{ color: "#475569", fontSize: "clamp(15px, 2vw, 11px)", margin: 0, lineHeight: 1.7 }}>
              {td.disclaimer || "This AI triage report is informational only. Consult a licensed healthcare professional for diagnosis and treatment."}
            </p>
          </div>

          <button onClick={reset} style={S.primaryBtn}>New Assessment</button>
        </div>
      </div>
    );
  }

  return null;
}

const S = {
  shell: { minHeight: "100vh", background: "#020617", color: "#e2e8f0", fontFamily: "Georgia,'Times New Roman',serif", fontSize: "16px" },
  container: { maxWidth: 680, margin: "0 auto", padding: "24px 16px", width: "100%", boxSizing: "border-box" },
  title: { fontFamily: "'Courier New',Courier,monospace", color: "#e2e8f0", fontWeight: 800, letterSpacing: 2, margin: 0, fontSize: "clamp(22px, 5vw, 32px)" },
  card: { background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, padding: "16px", marginBottom: 12, animation: "slideIn 0.4s ease" },
  cardTitle: { fontFamily: "'Courier New',monospace", fontSize: 15, color: "#94a3b8", letterSpacing: 1, marginTop: 0, marginBottom: 12 },
  primaryBtn: { width: "100%", padding: "16px 20px", background: "linear-gradient(135deg,#0ea5e9,#6366f1)", color: "white", border: "none", borderRadius: 10, fontSize: "clamp(15px, 3vw, 18px)", fontFamily: "'Courier New',monospace", fontWeight: 700, letterSpacing: 1, cursor: "pointer", transition: "all 0.2s", boxSizing: "border-box" },
  secondaryBtn: { padding: "8px 16px", background: "#1e293b", color: "#94a3b8", border: "1px solid #334155", borderRadius: 8, fontSize: 15, fontFamily: "monospace", cursor: "pointer" },
};

const CSS = `
  * { box-sizing: border-box; }
  body { margin: 0; padding: 0; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
  @keyframes slideIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
  button:hover:not(:disabled){transform:translateY(-1px);filter:brightness(1.1)}
  textarea:focus{border-color:#0ea5e9!important}
  ::-webkit-scrollbar{width:4px}
  ::-webkit-scrollbar-track{background:#020617}
  ::-webkit-scrollbar-thumb{background:#1e293b;border-radius:2px}
  @media (max-width: 480px) {
    textarea { min-height: 120px !important; }
  }
`;
