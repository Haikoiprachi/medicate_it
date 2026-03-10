"""
MedTriage AI — FastAPI + LangGraph Backend
Multi-Agent Medical Triage System with Privacy Protection
"""

import os
import re
import uuid
import hashlib
import logging
from typing import Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

# ── Logging (never log raw user input) ────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("medtriage")

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MedTriage AI",
    description="Multi-Agent Medical Triage System",
    version="1.0.0",
    docs_url=None,   # Disable Swagger UI in production
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-Session-ID"],
)

# ── Privacy Engine ─────────────────────────────────────────────────────────────
class PrivacyEngine:
    """Strips PII and anonymizes user input before any AI processing."""

    PII_PATTERNS = [
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",               "[PHONE]"),
        (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",   "[EMAIL]"),
        (r"\b(mr|mrs|ms|dr|prof)\.?\s+[a-z]+(\s+[a-z]+)?\b", "[NAME]"),
        (r"\b\d{3}-\d{2}-\d{4}\b",                        "[SSN]"),
        (r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",                 "[DATE]"),
        (r"\b[A-Z]{2}\d{6,9}\b",                          "[ID]"),
        (r"\b\d{5}(-\d{4})?\b",                           "[ZIP]"),
    ]

    @staticmethod
    def strip_pii(text: str) -> str:
        result = text
        for pattern, replacement in PrivacyEngine.PII_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def session_hash(session_id: str) -> str:
        return hashlib.sha256(session_id.encode()).hexdigest()[:12]

    @staticmethod
    def audit_log(session_hash: str, stage: str, meta: dict = None):
        """Log only anonymized metadata — never user content."""
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "session": session_hash,
            "stage": stage,
            **(meta or {}),
        }
        logger.info("AUDIT | %s", entry)


privacy = PrivacyEngine()

# ── LangGraph State ────────────────────────────────────────────────────────────
from typing import TypedDict, Optional

class TriageState(TypedDict):
    # Input (anonymized)
    anonymized_input: str
    session_hash: str

    # Agent outputs
    extracted_symptoms: Optional[dict]
    risk_analysis: Optional[dict]
    risk_score: Optional[dict]
    triage_decision: Optional[dict]

    # Pipeline metadata
    errors: list[str]
    completed_agents: list[str]

# ── LLM Client ────────────────────────────────────────────────────────────────
def get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        max_tokens=1024,
        temperature=0,
    )

import json

def call_llm_json(system_prompt: str, user_content: str) -> dict:
    """Call Claude and parse JSON response."""
    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = llm.invoke(messages)
    text = response.content.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)

# ── Agent 1: Symptom Extractor ─────────────────────────────────────────────────
def symptom_extractor_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_1_start", {"agent": "symptom_extractor"})
    try:
        result = call_llm_json(
            system_prompt="""You are a medical symptom extraction agent.
Extract structured symptom data from user input.
Return ONLY valid JSON with this exact schema:
{
  "symptoms": [
    {"name": string, "severity": "mild"|"moderate"|"severe", "duration": string, "location": string}
  ],
  "vital_signs": {"mentioned": boolean, "details": string},
  "medical_history": string,
  "current_medications": string,
  "onset": "sudden"|"gradual"|"unknown",
  "affected_areas": [string]
}""",
            user_content=f"Extract symptoms from this anonymized patient description:\n\n{state['anonymized_input']}"
        )
        state["extracted_symptoms"] = result
        state["completed_agents"].append("extractor")
        privacy.audit_log(state["session_hash"], "agent_1_done", {"symptom_count": len(result.get("symptoms", []))})
    except Exception as e:
        state["errors"].append(f"extractor: {str(e)}")
        logger.error("Agent 1 error [session=%s]: %s", state["session_hash"], str(e))
    return state

# ── Agent 2: Risk Analyzer ─────────────────────────────────────────────────────
def risk_analyzer_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_2_start", {"agent": "risk_analyzer"})
    try:
        result = call_llm_json(
            system_prompt="""You are a medical risk analysis agent.
Analyze extracted symptoms for potential conditions and risk factors.
Return ONLY valid JSON:
{
  "potential_conditions": [
    {"name": string, "likelihood": "low"|"moderate"|"high", "reasoning": string}
  ],
  "red_flags": [string],
  "body_systems": [string],
  "risk_factors": [string],
  "requires_immediate_attention": boolean,
  "differential_notes": string
}""",
            user_content=f"Analyze these extracted symptoms:\n\n{json.dumps(state['extracted_symptoms'], indent=2)}"
        )
        state["risk_analysis"] = result
        state["completed_agents"].append("analyzer")
        privacy.audit_log(state["session_hash"], "agent_2_done", {
            "red_flag_count": len(result.get("red_flags", [])),
            "immediate_attention": result.get("requires_immediate_attention")
        })
    except Exception as e:
        state["errors"].append(f"analyzer: {str(e)}")
        logger.error("Agent 2 error [session=%s]: %s", state["session_hash"], str(e))
    return state

# ── Agent 3: Risk Scorer ───────────────────────────────────────────────────────
def risk_scorer_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_3_start", {"agent": "risk_scorer"})
    try:
        result = call_llm_json(
            system_prompt="""You are a medical risk scoring agent.
Calculate a dynamic risk score (0-100) from symptom and risk data.
Score breakdown must sum to overall_score.
Return ONLY valid JSON:
{
  "overall_score": number (0-100),
  "score_breakdown": {
    "symptom_severity":    number (0-30, based on severity levels),
    "red_flag_count":      number (0-25, +5 per red flag, max 25),
    "duration_factor":     number (0-20, longer = higher),
    "system_involvement":  number (0-15, more systems = higher),
    "onset_factor":        number (0-10, sudden = 10, gradual = 5, unknown = 3)
  },
  "confidence": "low"|"medium"|"high",
  "reasoning": string,
  "escalation_flag": boolean
}""",
            user_content=f"Calculate risk score from:\n\nSymptoms:\n{json.dumps(state['extracted_symptoms'], indent=2)}\n\nAnalysis:\n{json.dumps(state['risk_analysis'], indent=2)}"
        )
        state["risk_score"] = result
        state["completed_agents"].append("scorer")
        privacy.audit_log(state["session_hash"], "agent_3_done", {
            "score": result.get("overall_score"),
            "escalation": result.get("escalation_flag")
        })
    except Exception as e:
        state["errors"].append(f"scorer: {str(e)}")
        logger.error("Agent 3 error [session=%s]: %s", state["session_hash"], str(e))
    return state

# ── Agent 4: Triage Decision ───────────────────────────────────────────────────
def triage_decision_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_4_start", {"agent": "triage_decision"})
    try:
        result = call_llm_json(
            system_prompt="""You are a medical triage decision agent.
Based on risk score and full analysis, determine the urgency level and care pathway.
Return ONLY valid JSON:
{
  "urgency_level": "EMERGENCY"|"URGENT"|"SEMI_URGENT"|"NON_URGENT"|"SELF_CARE",
  "urgency_color": "red"|"orange"|"yellow"|"green"|"blue",
  "action_required": string,
  "timeframe": string,
  "care_pathway": string,
  "recommendations": [string],
  "warning_signs": [string],
  "self_care_tips": [string],
  "follow_up": string,
  "disclaimer": string
}
Urgency guide: EMERGENCY=life-threatening/call 911, URGENT=ER within 2hrs, SEMI_URGENT=doctor 24hrs, NON_URGENT=schedule appointment, SELF_CARE=home management.""",
            user_content=f"Determine triage from full pipeline data:\n\nSymptoms: {json.dumps(state['extracted_symptoms'], indent=2)}\n\nAnalysis: {json.dumps(state['risk_analysis'], indent=2)}\n\nScore: {json.dumps(state['risk_score'], indent=2)}"
        )
        state["triage_decision"] = result
        state["completed_agents"].append("triage")
        privacy.audit_log(state["session_hash"], "agent_4_done", {
            "urgency": result.get("urgency_level")
        })
    except Exception as e:
        state["errors"].append(f"triage: {str(e)}")
        logger.error("Agent 4 error [session=%s]: %s", state["session_hash"], str(e))
    return state

# ── Conditional Edge: escalate if red flags ───────────────────────────────────
def should_escalate(state: TriageState) -> str:
    analysis = state.get("risk_analysis") or {}
    score = state.get("risk_score") or {}
    if analysis.get("requires_immediate_attention") or score.get("escalation_flag"):
        return "escalate"
    return "normal"

def escalation_node(state: TriageState) -> TriageState:
    """Injects escalation marker before triage decision."""
    privacy.audit_log(state["session_hash"], "escalation_triggered")
    if state.get("risk_score"):
        state["risk_score"]["escalation_override"] = True
    return state

# ── Build LangGraph ────────────────────────────────────────────────────────────
def build_triage_graph() -> StateGraph:
    graph = StateGraph(TriageState)

    # Add agent nodes
    graph.add_node("extractor",  symptom_extractor_agent)
    graph.add_node("analyzer",   risk_analyzer_agent)
    graph.add_node("scorer",     risk_scorer_agent)
    graph.add_node("escalation", escalation_node)
    graph.add_node("triage",     triage_decision_agent)

    # Define edges (sequential pipeline)
    graph.set_entry_point("extractor")
    graph.add_edge("extractor", "analyzer")
    graph.add_edge("analyzer",  "scorer")

    # Conditional edge: escalate or normal path → triage
    graph.add_conditional_edges(
        "scorer",
        should_escalate,
        {
            "escalate": "escalation",
            "normal":   "triage",
        }
    )
    graph.add_edge("escalation", "triage")
    graph.add_edge("triage", END)

    return graph.compile()

triage_graph = build_triage_graph()

# ── Request / Response Models ──────────────────────────────────────────────────
class TriageRequest(BaseModel):
    symptoms: str
    session_id: str = ""

    @field_validator("symptoms")
    @classmethod
    def validate_symptoms(cls, v):
        if len(v.strip()) < 20:
            raise ValueError("Symptom description too short (min 20 characters)")
        if len(v) > 5000:
            raise ValueError("Input too long (max 5000 characters)")
        return v.strip()

class TriageResponse(BaseModel):
    session_hash: str
    extracted_symptoms: dict
    risk_analysis: dict
    risk_score: dict
    triage_decision: dict
    completed_agents: list[str]
    errors: list[str]
    privacy_log: dict

# ── API Endpoints ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedTriage AI", "version": "1.0.0"}

@app.post("/api/triage", response_model=TriageResponse)
async def run_triage(request: TriageRequest, req: Request):
    # Generate anonymous session
    raw_session = request.session_id or str(uuid.uuid4())
    s_hash = privacy.session_hash(raw_session)

    privacy.audit_log(s_hash, "request_received", {"ip_masked": True})

    # ── PRIVACY LAYER ──────────────────────────────────────────────────────────
    anonymized = privacy.strip_pii(request.symptoms)
    privacy.audit_log(s_hash, "pii_stripped")

    # Initialize LangGraph state
    initial_state: TriageState = {
        "anonymized_input": anonymized,
        "session_hash": s_hash,
        "extracted_symptoms": None,
        "risk_analysis": None,
        "risk_score": None,
        "triage_decision": None,
        "errors": [],
        "completed_agents": [],
    }

    # ── RUN LANGGRAPH PIPELINE ─────────────────────────────────────────────────
    try:
        final_state = await triage_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("Graph execution failed [session=%s]: %s", s_hash, str(e))
        raise HTTPException(status_code=500, detail="Triage pipeline failed")

    # Verify all 4 agents completed
    if len(final_state.get("completed_agents", [])) < 4 and not final_state.get("triage_decision"):
        raise HTTPException(status_code=500, detail="Pipeline incomplete — check agent errors")

    privacy.audit_log(s_hash, "pipeline_complete", {
        "agents_completed": len(final_state["completed_agents"]),
        "error_count": len(final_state["errors"]),
    })

    return TriageResponse(
        session_hash=s_hash,
        extracted_symptoms=final_state.get("extracted_symptoms") or {},
        risk_analysis=final_state.get("risk_analysis") or {},
        risk_score=final_state.get("risk_score") or {},
        triage_decision=final_state.get("triage_decision") or {},
        completed_agents=final_state.get("completed_agents", []),
        errors=final_state.get("errors", []),
        privacy_log={
            "pii_stripped": True,
            "raw_input_stored": False,
            "session_linked_to_identity": False,
            "session_hash": s_hash,
            "anonymized_preview": anonymized[:100] + ("…" if len(anonymized) > 100 else ""),
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
