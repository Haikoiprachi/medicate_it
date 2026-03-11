"""
MedTriage AI — FastAPI + LangGraph Backend
Multi-Agent Medical Triage System with Privacy Protection
"""

import os
import re
import uuid
import hashlib
import logging
import json
from datetime import datetime
from typing import TypedDict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("medtriage")

app = FastAPI(title="MedTriage AI", description="Multi-Agent Medical Triage System", version="1.0.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-ID"],
)

class PrivacyEngine:
    PII_PATTERNS = [
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
        (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL]"),
        (r"\b(mr|mrs|ms|dr|prof)\.?\s+[a-z]+(\s+[a-z]+)?\b", "[NAME]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
        (r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "[DATE]"),
        (r"\b[A-Z]{2}\d{6,9}\b", "[ID]"),
        (r"\b\d{5}(-\d{4})?\b", "[ZIP]"),
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
        entry = {"ts": datetime.utcnow().isoformat(), "session": session_hash, "stage": stage, **(meta or {})}
        logger.info("AUDIT | %s", entry)

privacy = PrivacyEngine()

class TriageState(TypedDict):
    anonymized_input: str
    session_hash: str
    extracted_symptoms: Optional[dict]
    risk_analysis: Optional[dict]
    risk_score: Optional[dict]
    triage_decision: Optional[dict]
    errors: list[str]
    completed_agents: list[str]

def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env")
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0)

def call_llm_json(system_prompt: str, user_content: str) -> dict:
    llm = get_llm()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
    response = llm.invoke(messages)
    text = response.content.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)

def symptom_extractor_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_1_start")
    try:
        result = call_llm_json(
            system_prompt="""You are a medical symptom extraction agent.
Return ONLY valid JSON with this exact schema, no extra text:
{
  "symptoms": [{"name": "string", "severity": "mild", "duration": "string", "location": "string"}],
  "vital_signs": {"mentioned": false, "details": "none"},
  "medical_history": "none",
  "current_medications": "none",
  "onset": "unknown",
  "affected_areas": ["string"]
}""",
            user_content=f"Extract symptoms from:\n\n{state['anonymized_input']}"
        )
        state["extracted_symptoms"] = result
        state["completed_agents"].append("extractor")
        privacy.audit_log(state["session_hash"], "agent_1_done", {"symptom_count": len(result.get("symptoms", []))})
    except Exception as e:
        state["errors"].append(f"extractor: {str(e)}")
        state["extracted_symptoms"] = {"symptoms": [], "onset": "unknown", "affected_areas": []}
        state["completed_agents"].append("extractor")
    return state

def risk_analyzer_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_2_start")
    try:
        result = call_llm_json(
            system_prompt="""You are a medical risk analysis agent.
Return ONLY valid JSON, no extra text:
{
  "potential_conditions": [{"name": "string", "likelihood": "low", "reasoning": "string"}],
  "red_flags": ["string"],
  "body_systems": ["string"],
  "risk_factors": ["string"],
  "requires_immediate_attention": false,
  "differential_notes": "string"
}""",
            user_content=f"Analyze these symptoms:\n\n{json.dumps(state['extracted_symptoms'], indent=2)}"
        )
        state["risk_analysis"] = result
        state["completed_agents"].append("analyzer")
        privacy.audit_log(state["session_hash"], "agent_2_done")
    except Exception as e:
        state["errors"].append(f"analyzer: {str(e)}")
        state["risk_analysis"] = {"potential_conditions": [], "red_flags": [], "body_systems": [], "risk_factors": [], "requires_immediate_attention": False, "differential_notes": ""}
        state["completed_agents"].append("analyzer")
    return state

def risk_scorer_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_3_start")
    try:
        result = call_llm_json(
            system_prompt="""You are a medical risk scoring agent.
Return ONLY valid JSON, no extra text:
{
  "overall_score": 30,
  "score_breakdown": {
    "symptom_severity": 10,
    "red_flag_count": 5,
    "duration_factor": 8,
    "system_involvement": 5,
    "onset_factor": 2
  },
  "confidence": "medium",
  "reasoning": "string",
  "escalation_flag": false
}
Replace numbers with actual calculated values based on severity. overall_score = sum of breakdown.""",
            user_content=f"Score this case:\n\nSymptoms:\n{json.dumps(state['extracted_symptoms'], indent=2)}\n\nAnalysis:\n{json.dumps(state['risk_analysis'], indent=2)}"
        )
        state["risk_score"] = result
        state["completed_agents"].append("scorer")
        privacy.audit_log(state["session_hash"], "agent_3_done", {"score": result.get("overall_score")})
    except Exception as e:
        state["errors"].append(f"scorer: {str(e)}")
        state["risk_score"] = {"overall_score": 30, "score_breakdown": {"symptom_severity": 10, "red_flag_count": 5, "duration_factor": 8, "system_involvement": 5, "onset_factor": 2}, "confidence": "low", "reasoning": "Score estimation", "escalation_flag": False}
        state["completed_agents"].append("scorer")
    return state

def triage_decision_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_4_start")
    try:
        result = call_llm_json(
            system_prompt="""You are a medical triage decision agent.
Return ONLY valid JSON, no extra text:
{
  "urgency_level": "NON_URGENT",
  "urgency_color": "green",
  "action_required": "string",
  "timeframe": "string",
  "care_pathway": "string",
  "recommendations": ["string"],
  "warning_signs": ["string"],
  "self_care_tips": ["string"],
  "follow_up": "string",
  "disclaimer": "This is AI-generated information only. Always consult a healthcare professional."
}
urgency_level must be one of: EMERGENCY, URGENT, SEMI_URGENT, NON_URGENT, SELF_CARE""",
            user_content=f"Triage this case:\n\nSymptoms: {json.dumps(state['extracted_symptoms'], indent=2)}\n\nAnalysis: {json.dumps(state['risk_analysis'], indent=2)}\n\nScore: {json.dumps(state['risk_score'], indent=2)}"
        )
        state["triage_decision"] = result
        state["completed_agents"].append("triage")
        privacy.audit_log(state["session_hash"], "agent_4_done", {"urgency": result.get("urgency_level")})
    except Exception as e:
        state["errors"].append(f"triage: {str(e)}")
        state["triage_decision"] = {"urgency_level": "NON_URGENT", "urgency_color": "green", "action_required": "Consult a doctor", "timeframe": "Within a few days", "care_pathway": "Primary care", "recommendations": ["See a doctor"], "warning_signs": [], "self_care_tips": [], "follow_up": "Monitor symptoms", "disclaimer": "This is AI-generated information only."}
        state["completed_agents"].append("triage")
    return state

def should_escalate(state: TriageState) -> str:
    analysis = state.get("risk_analysis") or {}
    score = state.get("risk_score") or {}
    if analysis.get("requires_immediate_attention") or score.get("escalation_flag"):
        return "escalate"
    return "normal"

def escalation_node(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "escalation_triggered")
    if state.get("risk_score"):
        state["risk_score"]["escalation_override"] = True
    return state

def build_triage_graph():
    graph = StateGraph(TriageState)
    graph.add_node("extractor", symptom_extractor_agent)
    graph.add_node("analyzer", risk_analyzer_agent)
    graph.add_node("scorer", risk_scorer_agent)
    graph.add_node("escalation", escalation_node)
    graph.add_node("triage", triage_decision_agent)
    graph.set_entry_point("extractor")
    graph.add_edge("extractor", "analyzer")
    graph.add_edge("analyzer", "scorer")
    graph.add_conditional_edges("scorer", should_escalate, {"escalate": "escalation", "normal": "triage"})
    graph.add_edge("escalation", "triage")
    graph.add_edge("triage", END)
    return graph.compile()

triage_graph = build_triage_graph()

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

@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedTriage AI", "version": "1.0.0"}

@app.post("/api/triage", response_model=TriageResponse)
async def run_triage(request: TriageRequest, req: Request):
    raw_session = request.session_id or str(uuid.uuid4())
    s_hash = privacy.session_hash(raw_session)
    privacy.audit_log(s_hash, "request_received")
    anonymized = privacy.strip_pii(request.symptoms)
    privacy.audit_log(s_hash, "pii_stripped")

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

    try:
        final_state = await triage_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error("Graph execution failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Triage pipeline failed: {str(e)}")

    privacy.audit_log(s_hash, "pipeline_complete", {"agents_completed": len(final_state["completed_agents"])})

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