import { useState, useEffect, useRef } from "react";

const AGENT_PIPELINE = [
  { id: "extraction", label: "Symptom Extraction", icon: "🔬", color: "#00d4ff" },
  { id: "structuring", label: "Symptom Structuring", icon: "🗂️", color: "#7c3aed" },
  { id: "scoring", label: "Risk Scoring", icon: "📊", color: "#f59e0b" },
  { id: "decision", label: "Escalation Decision", icon: "⚖️", color: "#10b981" },
  { id: "response", label: "Response Generation", icon: "💬", color: "#ec4899" },
];

const SYMPTOM_DICTIONARY = {
  "chest pain": { term: "Chest Pain (Angina/Cardiac)", weight: 9 },
  "chest tightness": { term: "Chest Tightness", weight: 8 },
  "shortness of breath": { term: "Dyspnea", weight: 8 },
  "difficulty breathing": { term: "Dyspnea", weight: 8 },
  "headache": { term: "Cephalgia", weight: 3 },
  "severe headache": { term: "Severe Cephalgia", weight: 7 },
  "fever": { term: "Pyrexia", weight: 4 },
  "high fever": { term: "Hyperpyrexia", weight: 7 },
  "nausea": { term: "Nausea", weight: 3 },
  "vomiting": { term: "Emesis", weight: 4 },
  "dizziness": { term: "Vertigo/Dizziness", weight: 4 },
  "fainting": { term: "Syncope", weight: 8 },
  "stomach pain": { term: "Abdominal Pain", weight: 4 },
  "abdominal pain": { term: "Abdominal Pain", weight: 5 },
  "back pain": { term: "Dorsalgia", weight: 3 },
  "fatigue": { term: "Fatigue/Malaise", weight: 2 },
  "cough": { term: "Tussis", weight: 3 },
  "sore throat": { term: "Pharyngitis", weight: 2 },
  "rash": { term: "Dermatitis/Exanthem", weight: 4 },
  "swelling": { term: "Edema", weight: 5 },
  "numbness": { term: "Paresthesia/Numbness", weight: 6 },
  "weakness": { term: "Asthenia", weight: 5 },
  "confusion": { term: "Altered Mental Status", weight: 9 },
  "blurred vision": { term: "Visual Disturbance", weight: 6 },
  "palpitations": { term: "Cardiac Palpitations", weight: 6 },
};

function computeRiskScore(symptoms, severity, age, medicalHistory) {
  let score = 0;
  let maxWeight = 0;

  symptoms.forEach((s) => {
    const key = s.toLowerCase();
    const matched = Object.keys(SYMPTOM_DICTIONARY).find((k) => key.includes(k));
    if (matched) {
      score += SYMPTOM_DICTIONARY[matched].weight;
      maxWeight = Math.max(maxWeight, SYMPTOM_DICTIONARY[matched].weight);
    } else {
      score += 2;
    }
  });

  const severityBonus = { mild: 0, moderate: 5, severe: 12 };
  score += severityBonus[severity] || 0;

  const ageNum = parseInt(age);
  if (!isNaN(ageNum)) {
    if (ageNum < 5 || ageNum > 65) score += 5;
    else if (ageNum > 50) score += 2;
  }

  const highRiskConditions = ["diabetes", "heart disease", "hypertension", "asthma", "cancer", "copd"];
  if (medicalHistory) {
    highRiskConditions.forEach((c) => {
      if (medicalHistory.toLowerCase().includes(c)) score += 4;
    });
  }

  if (maxWeight >= 8) score = Math.max(score, 75);

  return Math.min(score * 2.5, 100);
}

function AgentNode({ agent, status, result, isActive }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "16px",
        padding: "16px",
        borderRadius: "12px",
        background: isActive
          ? `linear-gradient(135deg, ${agent.color}15, ${agent.color}08)`
          : status === "done"
          ? "#ffffff08"
          : "#ffffff04",
        border: `1px solid ${isActive ? agent.color + "60" : status === "done" ? "#ffffff15" : "#ffffff08"}`,
        transition: "all 0.4s ease",
        opacity: status === "pending" ? 0.4 : 1,
      }}
    >
      <div
        style={{
          width: "44px",
          height: "44px",
          borderRadius: "10px",
          background: status === "done"
            ? `linear-gradient(135deg, ${agent.color}40, ${agent.color}20)`
            : isActive
            ? `linear-gradient(135deg, ${agent.color}30, ${agent.color}15)`
            : "#ffffff08",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "20px",
          flexShrink: 0,
          boxShadow: isActive ? `0 0 20px ${agent.color}40` : "none",
          transition: "all 0.4s ease",
        }}
      >
        {isActive ? (
          <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⚙️</span>
        ) : (
          agent.icon
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
          <span style={{ color: agent.color, fontWeight: 700, fontSize: "13px", letterSpacing: "0.05em" }}>
            {agent.label.toUpperCase()}
          </span>
          {status === "done" && (
            <span style={{ color: "#10b981", fontSize: "12px" }}>✓ Complete</span>
          )}
          {isActive && (
            <span style={{ color: agent.color, fontSize: "12px", opacity: 0.8 }}>Processing...</span>
          )}
        </div>
        {result && (
          <div style={{ color: "#94a3b8", fontSize: "12px", lineHeight: "1.5", wordBreak: "break-word" }}>
            {result}
          </div>
        )}
      </div>
    </div>
  );
}

function RiskMeter({ score }) {
  const level = score < 35 ? "LOW" : score < 65 ? "MEDIUM" : "HIGH";
  const colors = { LOW: "#10b981", MEDIUM: "#f59e0b", HIGH: "#ef4444" };
  const color = colors[level];

  return (
    <div style={{ textAlign: "center", padding: "24px" }}>
      <div style={{ position: "relative", width: "160px", height: "80px", margin: "0 auto 16px" }}>
        <svg viewBox="0 0 200 100" style={{ width: "100%", height: "100%" }}>
          <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none" stroke="#ffffff10" strokeWidth="16" strokeLinecap="round" />
          <path
            d="M 20 90 A 80 80 0 0 1 180 90"
            fill="none"
            stroke={color}
            strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={`${(score / 100) * 251} 251`}
            style={{ transition: "stroke-dasharray 1s ease, stroke 0.5s ease", filter: `drop-shadow(0 0 8px ${color})` }}
          />
          <text x="100" y="85" textAnchor="middle" fill="white" fontSize="28" fontWeight="800" fontFamily="monospace">
            {Math.round(score)}
          </text>
        </svg>
      </div>
      <div
        style={{
          display: "inline-block",
          padding: "6px 20px",
          borderRadius: "999px",
          background: `${color}20`,
          border: `1px solid ${color}60`,
          color: color,
          fontWeight: 800,
          fontSize: "14px",
          letterSpacing: "0.1em",
        }}
      >
        {level} RISK
      </div>
    </div>
  );
}

export default function MedicalTriageSystem() {
  const [input, setInput] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [medHistory, setMedHistory] = useState("");
  const [agentStatuses, setAgentStatuses] = useState({});
  const [agentResults, setAgentResults] = useState({});
  const [activeAgent, setActiveAgent] = useState(null);
  const [finalOutput, setFinalOutput] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streamText, setStreamText] = useState("");
  const [phase, setPhase] = useState("idle"); // idle | processing | done
  const outputRef = useRef(null);

  useEffect(() => {
    if (finalOutput && outputRef.current) {
      outputRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [finalOutput]);

  const runTriage = async () => {
    if (!input.trim()) return;
    setLoading(true);
    setError(null);
    setFinalOutput(null);
    setStreamText("");
    setAgentStatuses({});
    setAgentResults({});
    setActiveAgent(null);
    setPhase("processing");

    try {
      const systemPrompt = `You are a multi-agent medical triage AI coordinator. You will analyze symptoms and produce a structured JSON response ONLY (no markdown, no backticks, pure JSON).

You must simulate 5 specialized agents:
1. Symptom Extraction Agent
2. Symptom Structuring Agent  
3. Risk Scoring Agent
4. Escalation Decision Agent
5. Response Generation Agent

Return ONLY this exact JSON structure:
{
  "extraction": {
    "symptoms": ["symptom1", "symptom2"],
    "severity": "mild|moderate|severe",
    "duration": "description of duration",
    "summary": "one sentence extraction summary"
  },
  "structuring": {
    "standardized_symptoms": ["Medical Term 1", "Medical Term 2"],
    "icd_hints": ["possible ICD category hints"],
    "summary": "one sentence structuring summary"
  },
  "scoring": {
    "base_score": 0-100,
    "age_factor": "low|neutral|elevated",
    "history_factor": "low|neutral|elevated",
    "severity_factor": "low|neutral|elevated",
    "summary": "one sentence scoring rationale"
  },
  "decision": {
    "level": "self-care|consult-doctor|emergency",
    "urgency": "1-10 urgency number",
    "rationale": "brief rationale",
    "summary": "one sentence decision summary"
  },
  "response": {
    "headline": "short headline for the patient",
    "explanation": "2-3 sentence friendly explanation of findings",
    "recommended_action": "specific action to take",
    "warning_signs": ["sign to watch for 1", "sign to watch for 2"],
    "disclaimer": "standard medical disclaimer"
  }
}`;

      const userMessage = `Patient Input:
Symptoms: ${input}
Age: ${age || "Not provided"}
Gender: ${gender || "Not provided"}
Medical History: ${medHistory || "None reported"}

Analyze and return the JSON triage report.`;

      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1500,
          system: systemPrompt,
          messages: [{ role: "user", content: userMessage }],
        }),
      });

      const data = await response.json();
      const rawText = data.content?.map((c) => c.text || "").join("") || "";

      let parsed;
      try {
        const clean = rawText.replace(/```json|```/g, "").trim();
        parsed = JSON.parse(clean);
      } catch {
        throw new Error("Failed to parse AI response.");
      }

      // Simulate sequential agent pipeline
      for (const agent of AGENT_PIPELINE) {
        setActiveAgent(agent.id);
        await new Promise((r) => setTimeout(r, 900));

        const agentData = parsed[agent.id];
        setAgentStatuses((prev) => ({ ...prev, [agent.id]: "done" }));
        setAgentResults((prev) => ({
          ...prev,
          [agent.id]: agentData?.summary || "Agent completed.",
        }));
        setActiveAgent(null);
        await new Promise((r) => setTimeout(r, 200));
      }

      // Compute local risk score too for the meter
      const localScore = computeRiskScore(
        parsed.extraction?.symptoms || [],
        parsed.extraction?.severity || "mild",
        age,
        medHistory
      );

      const aiScore = parsed.scoring?.base_score || localScore;
      const blendedScore = Math.round((aiScore + localScore) / 2);

      setFinalOutput({ ...parsed, blendedScore });
      setPhase("done");
    } catch (err) {
      setError(err.message || "An error occurred. Please try again.");
      setPhase("idle");
    } finally {
      setLoading(false);
      setActiveAgent(null);
    }
  };

  const reset = () => {
    setInput("");
    setAge("");
    setGender("");
    setMedHistory("");
    setAgentStatuses({});
    setAgentResults({});
    setActiveAgent(null);
    setFinalOutput(null);
    setStreamText("");
    setError(null);
    setPhase("idle");
  };

  const escalationConfig = {
    "self-care": { color: "#10b981", bg: "#10b98115", label: "SELF-CARE", icon: "🏠", text: "You can manage this at home with rest and over-the-counter remedies." },
    "consult-doctor": { color: "#f59e0b", bg: "#f59e0b15", label: "SEE A DOCTOR", icon: "🩺", text: "Schedule an appointment with your physician within 24-48 hours." },
    "emergency": { color: "#ef4444", bg: "#ef444415", label: "EMERGENCY", icon: "🚨", text: "Seek emergency medical attention immediately. Call 911 or go to the ER." },
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#040d1a",
      backgroundImage: "radial-gradient(ellipse at 20% 20%, #0a1f3a 0%, transparent 60%), radial-gradient(ellipse at 80% 80%, #0d0a2e 0%, transparent 60%)",
      fontFamily: "'DM Mono', 'Courier New', monospace",
      color: "#e2e8f0",
      padding: "0",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap');
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
        @keyframes glow { 0%,100% { box-shadow: 0 0 20px #00d4ff30; } 50% { box-shadow: 0 0 40px #00d4ff60; } }
        .fade-in { animation: fadeIn 0.5s ease forwards; }
        textarea:focus, input:focus, select:focus { outline: none !important; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #ffffff20; border-radius: 2px; }
      `}</style>

      {/* Header */}
      <div style={{
        borderBottom: "1px solid #ffffff0d",
        padding: "20px 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "#ffffff03",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{
            width: "36px", height: "36px", borderRadius: "8px",
            background: "linear-gradient(135deg, #00d4ff30, #7c3aed30)",
            border: "1px solid #00d4ff40",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: "18px"
          }}>⚕️</div>
          <div>
            <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: "16px", color: "#fff", letterSpacing: "0.02em" }}>
              MEDTRIAGE<span style={{ color: "#00d4ff" }}>.AI</span>
            </div>
            <div style={{ fontSize: "10px", color: "#64748b", letterSpacing: "0.15em" }}>MULTI-AGENT TRIAGE SYSTEM</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px", fontSize: "11px", color: "#475569" }}>
          {AGENT_PIPELINE.map(a => (
            <div key={a.id} style={{
              width: "8px", height: "8px", borderRadius: "50%",
              background: agentStatuses[a.id] === "done" ? a.color : activeAgent === a.id ? a.color : "#ffffff15",
              boxShadow: activeAgent === a.id ? `0 0 8px ${a.color}` : "none",
              transition: "all 0.3s ease"
            }} />
          ))}
        </div>
      </div>

      <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "32px 24px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>

        {/* Left Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

          {/* Input Panel */}
          <div style={{
            background: "#ffffff04",
            border: "1px solid #ffffff0d",
            borderRadius: "16px",
            padding: "24px",
          }}>
            <div style={{ marginBottom: "20px" }}>
              <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: "20px", marginBottom: "4px" }}>
                Symptom Input
              </div>
              <div style={{ fontSize: "12px", color: "#64748b" }}>Describe your symptoms in natural language</div>
            </div>

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Example: I've been having chest pain for the past 2 hours, along with shortness of breath and dizziness. The pain feels sharp and radiates to my left arm..."
              style={{
                width: "100%", minHeight: "120px", background: "#ffffff06",
                border: "1px solid #ffffff10", borderRadius: "10px",
                color: "#e2e8f0", fontSize: "13px", lineHeight: "1.6",
                padding: "14px", resize: "vertical", boxSizing: "border-box",
                fontFamily: "inherit", transition: "border-color 0.2s",
              }}
              onFocus={e => e.target.style.borderColor = "#00d4ff40"}
              onBlur={e => e.target.style.borderColor = "#ffffff10"}
              disabled={loading}
            />

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "12px" }}>
              <div>
                <div style={{ fontSize: "10px", color: "#64748b", marginBottom: "4px", letterSpacing: "0.1em" }}>AGE</div>
                <input
                  type="number" value={age} onChange={(e) => setAge(e.target.value)}
                  placeholder="e.g. 45"
                  style={{
                    width: "100%", background: "#ffffff06", border: "1px solid #ffffff10",
                    borderRadius: "8px", color: "#e2e8f0", fontSize: "13px",
                    padding: "10px 12px", boxSizing: "border-box", fontFamily: "inherit",
                  }}
                  disabled={loading}
                />
              </div>
              <div>
                <div style={{ fontSize: "10px", color: "#64748b", marginBottom: "4px", letterSpacing: "0.1em" }}>GENDER</div>
                <select
                  value={gender} onChange={(e) => setGender(e.target.value)}
                  style={{
                    width: "100%", background: "#0a1628", border: "1px solid #ffffff10",
                    borderRadius: "8px", color: gender ? "#e2e8f0" : "#475569", fontSize: "13px",
                    padding: "10px 12px", boxSizing: "border-box", fontFamily: "inherit",
                  }}
                  disabled={loading}
                >
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div style={{ marginTop: "12px" }}>
              <div style={{ fontSize: "10px", color: "#64748b", marginBottom: "4px", letterSpacing: "0.1em" }}>MEDICAL HISTORY</div>
              <input
                type="text" value={medHistory} onChange={(e) => setMedHistory(e.target.value)}
                placeholder="e.g. diabetes, hypertension, heart disease..."
                style={{
                  width: "100%", background: "#ffffff06", border: "1px solid #ffffff10",
                  borderRadius: "8px", color: "#e2e8f0", fontSize: "13px",
                  padding: "10px 12px", boxSizing: "border-box", fontFamily: "inherit",
                }}
                disabled={loading}
              />
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "16px" }}>
              <button
                onClick={runTriage}
                disabled={loading || !input.trim()}
                style={{
                  flex: 1, padding: "13px", borderRadius: "10px",
                  background: loading || !input.trim()
                    ? "#ffffff0a"
                    : "linear-gradient(135deg, #00d4ff, #0099cc)",
                  border: "none", color: loading || !input.trim() ? "#64748b" : "#000",
                  fontWeight: 700, fontSize: "13px", cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                  letterSpacing: "0.08em", fontFamily: "inherit",
                  transition: "all 0.2s ease",
                  animation: !loading && input.trim() ? "glow 2s infinite" : "none",
                }}
              >
                {loading ? "⚙️  ANALYZING..." : "▶  RUN TRIAGE"}
              </button>
              {phase !== "idle" && (
                <button
                  onClick={reset}
                  style={{
                    padding: "13px 16px", borderRadius: "10px",
                    background: "#ffffff08", border: "1px solid #ffffff10",
                    color: "#94a3b8", cursor: "pointer", fontSize: "13px",
                    fontFamily: "inherit",
                  }}
                >
                  ↺
                </button>
              )}
            </div>

            {error && (
              <div style={{
                marginTop: "12px", padding: "12px", borderRadius: "8px",
                background: "#ef444415", border: "1px solid #ef444430",
                color: "#ef4444", fontSize: "12px"
              }}>
                ⚠ {error}
              </div>
            )}
          </div>

          {/* Architecture Diagram */}
          <div style={{
            background: "#ffffff04", border: "1px solid #ffffff0d",
            borderRadius: "16px", padding: "20px"
          }}>
            <div style={{ fontSize: "10px", color: "#64748b", letterSpacing: "0.15em", marginBottom: "14px" }}>
              AGENT PIPELINE ARCHITECTURE
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              {[
                { label: "USER INPUT", color: "#64748b", icon: "👤" },
                ...AGENT_PIPELINE.map(a => ({ label: a.label.toUpperCase(), color: a.color, icon: a.icon })),
                { label: "FINAL OUTPUT", color: "#64748b", icon: "📋" }
              ].map((item, i, arr) => (
                <div key={i}>
                  <div style={{
                    display: "flex", alignItems: "center", gap: "8px",
                    padding: "7px 10px", borderRadius: "6px",
                    background: "#ffffff04", fontSize: "11px"
                  }}>
                    <span>{item.icon}</span>
                    <span style={{ color: item.color, fontWeight: 500 }}>{item.label}</span>
                  </div>
                  {i < arr.length - 1 && (
                    <div style={{ textAlign: "center", color: "#334155", fontSize: "10px", lineHeight: 1 }}>│</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

          {/* Agent Status Panel */}
          <div style={{
            background: "#ffffff04", border: "1px solid #ffffff0d",
            borderRadius: "16px", padding: "20px"
          }}>
            <div style={{ fontSize: "10px", color: "#64748b", letterSpacing: "0.15em", marginBottom: "14px" }}>
              AGENT STATUS
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {AGENT_PIPELINE.map((agent) => (
                <AgentNode
                  key={agent.id}
                  agent={agent}
                  status={agentStatuses[agent.id] || "pending"}
                  result={agentResults[agent.id]}
                  isActive={activeAgent === agent.id}
                />
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div style={{
            background: "#f59e0b08", border: "1px solid #f59e0b20",
            borderRadius: "10px", padding: "12px 14px",
            fontSize: "11px", color: "#78716c", lineHeight: "1.5"
          }}>
            ⚠ <strong style={{ color: "#f59e0b" }}>Medical Disclaimer:</strong> This AI tool is for informational purposes only and does not constitute medical advice. Always consult a qualified healthcare professional for diagnosis and treatment.
          </div>
        </div>
      </div>

      {/* Results Section */}
      {finalOutput && (
        <div ref={outputRef} className="fade-in" style={{
          maxWidth: "1100px", margin: "0 auto 48px",
          padding: "0 24px"
        }}>
          <div style={{
            background: "#ffffff04", border: "1px solid #ffffff0d",
            borderRadius: "20px", overflow: "hidden"
          }}>
            {/* Results Header */}
            <div style={{
              padding: "20px 28px",
              background: "linear-gradient(90deg, #ffffff06, transparent)",
              borderBottom: "1px solid #ffffff0d",
              display: "flex", alignItems: "center", justifyContent: "space-between"
            }}>
              <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: "18px" }}>
                Triage Report
              </div>
              <div style={{ fontSize: "11px", color: "#475569" }}>
                {new Date().toLocaleString()}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: "0" }}>

              {/* Risk Meter Sidebar */}
              <div style={{
                borderRight: "1px solid #ffffff0d",
                padding: "20px 10px",
                display: "flex", flexDirection: "column", alignItems: "center", gap: "16px"
              }}>
                <RiskMeter score={finalOutput.blendedScore} />

                <div style={{ width: "100%", padding: "0 12px" }}>
                  {[
                    { label: "Age Factor", val: finalOutput.scoring?.age_factor || "neutral" },
                    { label: "History", val: finalOutput.scoring?.history_factor || "neutral" },
                    { label: "Severity", val: finalOutput.scoring?.severity_factor || "neutral" },
                  ].map(f => {
                    const fc = { low: "#10b981", neutral: "#94a3b8", elevated: "#ef4444" };
                    return (
                      <div key={f.label} style={{
                        display: "flex", justifyContent: "space-between", alignItems: "center",
                        padding: "6px 0", borderBottom: "1px solid #ffffff06", fontSize: "11px"
                      }}>
                        <span style={{ color: "#64748b" }}>{f.label}</span>
                        <span style={{ color: fc[f.val] || "#94a3b8", fontWeight: 600 }}>{f.val?.toUpperCase()}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Main Results */}
              <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: "20px" }}>

                {/* Escalation Banner */}
                {finalOutput.decision && (() => {
                  const cfg = escalationConfig[finalOutput.decision.level] || escalationConfig["consult-doctor"];
                  return (
                    <div style={{
                      padding: "16px 20px", borderRadius: "12px",
                      background: cfg.bg, border: `1px solid ${cfg.color}40`,
                      display: "flex", alignItems: "center", gap: "14px"
                    }}>
                      <span style={{ fontSize: "28px" }}>{cfg.icon}</span>
                      <div>
                        <div style={{ color: cfg.color, fontWeight: 800, fontSize: "15px", marginBottom: "2px" }}>
                          {cfg.label}
                        </div>
                        <div style={{ color: "#94a3b8", fontSize: "12px" }}>{cfg.text}</div>
                      </div>
                      <div style={{
                        marginLeft: "auto", background: cfg.bg, border: `1px solid ${cfg.color}40`,
                        borderRadius: "8px", padding: "8px 14px", textAlign: "center"
                      }}>
                        <div style={{ color: cfg.color, fontWeight: 800, fontSize: "20px" }}>
                          {finalOutput.decision.urgency}/10
                        </div>
                        <div style={{ color: "#64748b", fontSize: "10px" }}>URGENCY</div>
                      </div>
                    </div>
                  );
                })()}

                {/* Response */}
                {finalOutput.response && (
                  <div>
                    <div style={{ color: "#fff", fontWeight: 700, fontSize: "15px", marginBottom: "8px" }}>
                      {finalOutput.response.headline}
                    </div>
                    <div style={{ color: "#94a3b8", fontSize: "13px", lineHeight: "1.7", marginBottom: "12px" }}>
                      {finalOutput.response.explanation}
                    </div>
                    <div style={{
                      padding: "12px 16px", borderRadius: "8px",
                      background: "#00d4ff0a", border: "1px solid #00d4ff20",
                      color: "#7dd3fc", fontSize: "12px"
                    }}>
                      <strong>Recommended Action:</strong> {finalOutput.response.recommended_action}
                    </div>
                  </div>
                )}

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  {/* Extracted Symptoms */}
                  <div>
                    <div style={{ fontSize: "10px", color: "#64748b", letterSpacing: "0.12em", marginBottom: "8px" }}>
                      EXTRACTED SYMPTOMS
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {(finalOutput.extraction?.symptoms || []).map((s, i) => (
                        <span key={i} style={{
                          padding: "4px 10px", borderRadius: "6px",
                          background: "#00d4ff0f", border: "1px solid #00d4ff25",
                          color: "#7dd3fc", fontSize: "11px"
                        }}>{s}</span>
                      ))}
                    </div>
                    <div style={{ marginTop: "10px", fontSize: "10px", color: "#64748b", letterSpacing: "0.12em", marginBottom: "6px" }}>
                      STANDARDIZED TERMS
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {(finalOutput.structuring?.standardized_symptoms || []).map((s, i) => (
                        <span key={i} style={{
                          padding: "4px 10px", borderRadius: "6px",
                          background: "#7c3aed0f", border: "1px solid #7c3aed25",
                          color: "#a78bfa", fontSize: "11px"
                        }}>{s}</span>
                      ))}
                    </div>
                  </div>

                  {/* Warning Signs */}
                  <div>
                    <div style={{ fontSize: "10px", color: "#64748b", letterSpacing: "0.12em", marginBottom: "8px" }}>
                      WARNING SIGNS TO WATCH
                    </div>
                    {(finalOutput.response?.warning_signs || []).map((w, i) => (
                      <div key={i} style={{
                        display: "flex", alignItems: "center", gap: "8px",
                        padding: "6px 0", borderBottom: "1px solid #ffffff06", fontSize: "12px"
                      }}>
                        <span style={{ color: "#ef4444", fontSize: "8px" }}>◆</span>
                        <span style={{ color: "#94a3b8" }}>{w}</span>
                      </div>
                    ))}
                    <div style={{ marginTop: "10px", fontSize: "10px", color: "#64748b", lineHeight: "1.5" }}>
                      {finalOutput.response?.disclaimer}
                    </div>
                  </div>
                </div>

                {/* Decision Rationale */}
                {finalOutput.decision?.rationale && (
                  <div style={{
                    padding: "12px 16px", borderRadius: "8px",
                    background: "#ffffff04", border: "1px solid #ffffff0d",
                    fontSize: "12px", color: "#64748b"
                  }}>
                    <strong style={{ color: "#94a3b8" }}>AI Reasoning:</strong> {finalOutput.decision.rationale}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
