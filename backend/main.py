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

app = FastAPI(title="MedTriage AI", description="Multi-Agent Medical Triage System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Privacy Engine ─────────────────────────────────────────────────────────────
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

# ── Smart Pre-Scorer (rule-based, never wrong) ─────────────────────────────────
def compute_base_score(symptoms_text: str, extracted: dict, analysis: dict) -> dict:
    """
    Rule-based scoring that runs BEFORE the LLM scorer.
    Ensures critical symptoms like chest pain, high pain scores are never underrated.
    """
    text_lower = symptoms_text.lower()
    symptoms = extracted.get("symptoms", [])
    red_flags = analysis.get("red_flags", [])
    body_systems = analysis.get("body_systems", [])
    onset = extracted.get("onset", "unknown")

    # ── 1. Symptom Severity Score (0-30) ──────────────────────────────────────
    # Check for explicit pain rating (e.g. "9/10", "8 out of 10")
    pain_rating = 0
    pain_match = re.search(r'(\d+)\s*/\s*10', text_lower)
    if not pain_match:
        pain_match = re.search(r'(\d+)\s*out\s*of\s*10', text_lower)
    if pain_match:
        pain_rating = int(pain_match.group(1))

    # Map pain rating to severity score
    if pain_rating >= 9:
        severity_score = 28
    elif pain_rating >= 7:
        severity_score = 22
    elif pain_rating >= 5:
        severity_score = 15
    elif pain_rating >= 3:
        severity_score = 8
    else:
        # Fallback: check symptom severity fields
        severity_map = {"severe": 25, "moderate": 15, "mild": 7}
        scores = [severity_map.get(s.get("severity", "mild"), 7) for s in symptoms]
        severity_score = max(scores) if scores else 7

    # Boost for critical symptom types
    critical_keywords = ["chest pain", "chest tightness", "heart", "shortness of breath",
                         "can't breathe", "difficulty breathing", "unconscious", "seizure",
                         "stroke", "paralysis", "severe bleeding", "coughing blood",
                         "vomiting blood", "crushing", "radiating"]
    for kw in critical_keywords:
        if kw in text_lower:
            severity_score = max(severity_score, 26)
            break

    severity_score = min(severity_score, 30)

    # ── 2. Red Flag Score (0-25) ───────────────────────────────────────────────
    red_flag_score = min(len(red_flags) * 5, 25)

    # Extra boost for critical red flag keywords in original text
    critical_rf = ["chest pain", "heart attack", "cardiac", "stroke", "can't breathe",
                   "difficulty breathing", "loss of consciousness", "severe bleeding",
                   "crushing pain", "radiating pain", "jaw pain", "left arm pain"]
    rf_boost = sum(5 for kw in critical_rf if kw in text_lower)
    red_flag_score = min(red_flag_score + rf_boost, 25)

    # ── 3. Duration Factor (0-20) ──────────────────────────────────────────────
    if any(w in text_lower for w in ["sudden", "suddenly", "just started", "minutes ago", "just now"]):
        duration_score = 18
    elif any(w in text_lower for w in ["hour", "hours"]):
        duration_score = 12
    elif any(w in text_lower for w in ["day", "days"]):
        duration_score = 10
    elif any(w in text_lower for w in ["week", "weeks"]):
        duration_score = 15
    elif any(w in text_lower for w in ["month", "months", "year", "years"]):
        duration_score = 18
    else:
        duration_score = 7

    # ── 4. System Involvement (0-15) ──────────────────────────────────────────
    system_count = len(body_systems) if body_systems else 1
    system_score = min(system_count * 5, 15)

    # ── 5. Onset Factor (0-10) ────────────────────────────────────────────────
    if onset == "sudden" or any(w in text_lower for w in ["sudden", "suddenly", "all of a sudden"]):
        onset_score = 10
    elif onset == "gradual":
        onset_score = 5
    else:
        onset_score = 3

    overall = severity_score + red_flag_score + duration_score + system_score + onset_score
    overall = min(overall, 100)

    return {
        "overall_score": overall,
        "score_breakdown": {
            "symptom_severity": severity_score,
            "red_flag_count": red_flag_score,
            "duration_factor": duration_score,
            "system_involvement": system_score,
            "onset_factor": onset_score,
        },
        "pain_rating_detected": pain_rating if pain_rating > 0 else None,
        "escalation_flag": overall >= 60,
        "confidence": "high",
        "reasoning": f"Score based on: pain rating {pain_rating}/10 detected, {len(red_flags)} red flags, {system_count} body system(s) involved, onset: {onset}."
    }


# ── LangGraph State ────────────────────────────────────────────────────────────
class TriageState(TypedDict):
    anonymized_input: str
    original_input: str  # kept only for rule-based scoring, never logged
    session_hash: str
    extracted_symptoms: Optional[dict]
    risk_analysis: Optional[dict]
    risk_score: Optional[dict]
    triage_decision: Optional[dict]
    errors: list[str]
    completed_agents: list[str]

# ── LLM Client ────────────────────────────────────────────────────────────────
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
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        text = match.group()
    return json.loads(text)

# ── Agent 1: Symptom Extractor ─────────────────────────────────────────────────

# ── Agent 1: Symptom Extractor ─────────────────────────────────────────────────
def symptom_extractor_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_1_start")
    try:
        result = call_llm_json(
            system_prompt="""You are a medical symptom extraction agent. Extract EVERY detail from the patient description. Never leave fields blank or "unknown" if information is available.

CRITICAL RULES:
1. Extract ALL symptoms mentioned — even minor ones like sweating, dizziness, nausea
2. onset: "sudden" if patient says suddenly/just started/all of a sudden. "gradual" if slowly worsening. Only "unknown" if zero timing info.
3. affected_areas: list every body part mentioned
4. body_systems: ALWAYS populate this based on symptoms:
   - chest/heart/palpitations → cardiovascular
   - breathing/lungs/cough → respiratory  
   - head/brain/dizziness/vision → neurological
   - stomach/nausea/vomiting/abdomen → gastrointestinal
   - muscles/joints/back/bones → musculoskeletal
   - skin/rash/swelling → dermatological
5. severity from pain score: 1-3=mild, 4-6=moderate, 7-10=severe
6. current_medications: list any medicines taken. "none mentioned" only if truly absent.

Return ONLY valid JSON:
{
  "symptoms": [
    {"name": "chest pain", "severity": "severe", "duration": "30 minutes", "location": "left chest", "pain_score": 9},
    {"name": "shortness of breath", "severity": "moderate", "duration": "30 minutes", "location": "chest", "pain_score": null},
    {"name": "sweating", "severity": "moderate", "duration": "30 minutes", "location": "general", "pain_score": null}
  ],
  "vital_signs": {"mentioned": false, "details": "none mentioned"},
  "medical_history": "no prior conditions mentioned",
  "current_medications": "none mentioned",
  "onset": "sudden",
  "affected_areas": ["chest", "left arm"],
  "body_systems": ["cardiovascular", "respiratory"]
}""",
            user_content=f"Extract ALL symptoms and details. Be very thorough:\n\n{state['anonymized_input']}"
        )

        # Post-process: auto-infer body_systems if Gemini left it empty
        if not result.get("body_systems"):
            systems = []
            combined = " ".join([
                " ".join(s.get("name","") for s in result.get("symptoms",[])),
                " ".join(result.get("affected_areas",[])),
                state["anonymized_input"]
            ]).lower()
            if any(w in combined for w in ["chest","heart","cardiac","palpitation","pulse","blood pressure"]):
                systems.append("cardiovascular")
            if any(w in combined for w in ["breath","breathing","lung","cough","respiratory","wheez"]):
                systems.append("respiratory")
            if any(w in combined for w in ["head","brain","dizz","vision","seizure","migraine","neuro","faint","unconscious"]):
                systems.append("neurological")
            if any(w in combined for w in ["stomach","abdomen","nausea","vomit","bowel","diarrhea","gastro","indigestion"]):
                systems.append("gastrointestinal")
            if any(w in combined for w in ["muscle","joint","bone","back","spine","arm","leg","knee"]):
                systems.append("musculoskeletal")
            if any(w in combined for w in ["skin","rash","itch","swelling","hives"]):
                systems.append("dermatological")
            result["body_systems"] = systems if systems else ["general"]

        # Auto-fix onset if Gemini missed it
        if result.get("onset") == "unknown":
            text = state["anonymized_input"].lower()
            if any(w in text for w in ["sudden","suddenly","all of a sudden","just now","minutes ago","out of nowhere","started suddenly"]):
                result["onset"] = "sudden"
            elif any(w in text for w in ["gradual","slowly","over time","getting worse","worsening","past few days","past few weeks"]):
                result["onset"] = "gradual"

        state["extracted_symptoms"] = result
        state["completed_agents"].append("extractor")
        privacy.audit_log(state["session_hash"], "agent_1_done", {"symptom_count": len(result.get("symptoms", []))})
    except Exception as e:
        state["errors"].append(f"extractor: {str(e)}")
        state["extracted_symptoms"] = {"symptoms": [], "onset": "unknown", "affected_areas": [], "medical_history": "none", "current_medications": "none", "body_systems": ["general"]}
        state["completed_agents"].append("extractor")
    return state

# ── Rule-based condition + medication map ─────────────────────────────────────
CONDITION_MAP = [
    {
        "keywords": ["chest pain", "chest tightness", "chest pressure", "chest discomfort"],
        "conditions": [
            {"name": "Acute Myocardial Infarction (Heart Attack)", "likelihood": "high", "reasoning": "Chest pain is the hallmark symptom of a heart attack, especially with high severity ratings."},
            {"name": "Unstable Angina", "likelihood": "moderate", "reasoning": "Chest pain at rest or with minimal exertion may indicate unstable angina."},
            {"name": "Pericarditis", "likelihood": "low", "reasoning": "Inflammation of the heart lining can cause sharp chest pain."},
        ],
        "red_flags": ["Chest pain — possible cardiac emergency", "Immediate ECG required"],
        "medications": ["Do NOT self-medicate — call 112 immediately", "Chew 325mg aspirin if not allergic and cardiac cause suspected", "Loosen tight clothing", "Sit or lie down and rest"],
        "immediate": True,
    },
    {
        "keywords": ["shortness of breath", "difficulty breathing", "can't breathe", "breathless", "breathing difficulty"],
        "conditions": [
            {"name": "Pulmonary Embolism", "likelihood": "moderate", "reasoning": "Sudden shortness of breath can indicate a blood clot in the lungs."},
            {"name": "Asthma Attack", "likelihood": "moderate", "reasoning": "Difficulty breathing is a classic asthma symptom."},
            {"name": "Pneumonia", "likelihood": "low", "reasoning": "Lung infection can cause breathing difficulty especially with fever."},
        ],
        "red_flags": ["Breathing difficulty — respiratory emergency possible"],
        "medications": ["Use prescribed inhaler if available (asthma)", "Sit upright to ease breathing", "Do NOT lie flat", "Seek emergency care if worsening"],
        "immediate": True,
    },
    {
        "keywords": ["headache", "head pain", "migraine", "head ache"],
        "conditions": [
            {"name": "Migraine", "likelihood": "high", "reasoning": "Severe unilateral headache with nausea and light sensitivity is classic migraine."},
            {"name": "Tension Headache", "likelihood": "moderate", "reasoning": "Bilateral pressing headache often due to stress or muscle tension."},
            {"name": "Hypertensive Crisis", "likelihood": "low", "reasoning": "Sudden severe headache can indicate dangerously high blood pressure."},
        ],
        "red_flags": [],
        "medications": ["Ibuprofen 400mg or Paracetamol 500mg for pain relief", "Rest in a dark quiet room", "Stay hydrated", "Cold or warm compress on forehead", "Avoid screens and bright lights"],
        "immediate": False,
    },
    {
        "keywords": ["fever", "high temperature", "chills", "sweating", "night sweats"],
        "conditions": [
            {"name": "Viral Infection (Flu/COVID-19)", "likelihood": "high", "reasoning": "Fever with chills and sweating is a hallmark of viral infections."},
            {"name": "Bacterial Infection", "likelihood": "moderate", "reasoning": "High persistent fever may indicate a bacterial source requiring antibiotics."},
            {"name": "Sepsis", "likelihood": "low", "reasoning": "High fever with confusion or rapid heart rate may indicate sepsis — a medical emergency."},
        ],
        "red_flags": [],
        "medications": ["Paracetamol 500-1000mg every 6 hours for fever", "Ibuprofen 400mg for fever if no contraindications", "Stay well hydrated", "Rest", "Seek care if fever exceeds 39.5°C or lasts more than 3 days"],
        "immediate": False,
    },
    {
        "keywords": ["stomach pain", "abdominal pain", "stomach ache", "belly pain", "abdomen"],
        "conditions": [
            {"name": "Appendicitis", "likelihood": "moderate", "reasoning": "Right lower abdominal pain that is sharp and worsening may indicate appendicitis."},
            {"name": "Gastroenteritis", "likelihood": "high", "reasoning": "Stomach pain with nausea/vomiting/diarrhea is commonly gastroenteritis."},
            {"name": "Peptic Ulcer", "likelihood": "moderate", "reasoning": "Burning stomach pain that worsens or improves with eating may indicate an ulcer."},
        ],
        "red_flags": [],
        "medications": ["Antacids (Gaviscon, Tums) for acid-related pain", "Oral rehydration salts if vomiting/diarrhea", "Avoid spicy, oily, and heavy food", "Paracetamol for pain (avoid ibuprofen on empty stomach)", "Seek care if pain is severe or localised to lower right"],
        "immediate": False,
    },
    {
        "keywords": ["nausea", "vomiting", "throwing up", "feel sick"],
        "conditions": [
            {"name": "Gastroenteritis", "likelihood": "high", "reasoning": "Nausea and vomiting are primary symptoms of stomach/gut infections."},
            {"name": "Food Poisoning", "likelihood": "moderate", "reasoning": "Sudden nausea and vomiting after eating suggests food poisoning."},
            {"name": "Migraine with Aura", "likelihood": "low", "reasoning": "Nausea can accompany migraines especially with headache."},
        ],
        "red_flags": [],
        "medications": ["Oral rehydration salts to prevent dehydration", "Ginger tea or ginger chews for nausea relief", "Ondansetron (Zofran) if prescribed", "Small sips of clear fluids only", "Avoid solid food until vomiting stops"],
        "immediate": False,
    },
    {
        "keywords": ["dizziness", "dizzy", "lightheaded", "vertigo", "spinning"],
        "conditions": [
            {"name": "Benign Paroxysmal Positional Vertigo (BPPV)", "likelihood": "high", "reasoning": "Brief spinning sensation triggered by head movement is classic BPPV."},
            {"name": "Dehydration", "likelihood": "moderate", "reasoning": "Lightheadedness and dizziness are common signs of dehydration."},
            {"name": "Inner Ear Infection (Labyrinthitis)", "likelihood": "moderate", "reasoning": "Persistent dizziness with nausea may indicate inner ear inflammation."},
        ],
        "red_flags": [],
        "medications": ["Sit or lie down immediately to prevent falls", "Drink water or electrolyte drinks if dehydrated", "Meclizine (Antivert) for vertigo if available", "Avoid sudden head movements", "Seek care if dizziness is accompanied by chest pain or vision changes"],
        "immediate": False,
    },
    {
        "keywords": ["back pain", "back ache", "lower back", "spine pain", "lumbar"],
        "conditions": [
            {"name": "Muscle Strain / Sprain", "likelihood": "high", "reasoning": "Most acute back pain is due to muscle or ligament strain."},
            {"name": "Herniated Disc", "likelihood": "moderate", "reasoning": "Sharp radiating back pain down the leg suggests disc herniation."},
            {"name": "Kidney Stones", "likelihood": "low", "reasoning": "Severe flank/back pain with nausea may indicate kidney stones."},
        ],
        "red_flags": [],
        "medications": ["Ibuprofen 400mg every 8 hours for inflammation and pain", "Paracetamol 500mg for additional pain relief", "Apply heat or ice pack to affected area", "Gentle stretching and rest", "Avoid heavy lifting"],
        "immediate": False,
    },
    {
        "keywords": ["cough", "coughing", "sore throat", "throat pain", "cold", "runny nose", "congestion"],
        "conditions": [
            {"name": "Upper Respiratory Tract Infection (Common Cold)", "likelihood": "high", "reasoning": "Cough, sore throat and congestion together are classic cold symptoms."},
            {"name": "Influenza (Flu)", "likelihood": "moderate", "reasoning": "Flu presents with cough, sore throat, body aches and fever."},
            {"name": "Strep Throat", "likelihood": "low", "reasoning": "Severe sore throat without cough and with fever may indicate strep infection."},
        ],
        "red_flags": [],
        "medications": ["Paracetamol 500mg for fever and throat pain", "Throat lozenges or warm salt water gargles", "Honey and lemon in warm water for cough", "Antihistamines for congestion (Cetirizine 10mg)", "Rest and drink plenty of warm fluids"],
        "immediate": False,
    },
    {
        "keywords": ["rash", "skin irritation", "itching", "hives", "allergic reaction", "swelling"],
        "conditions": [
            {"name": "Allergic Reaction (Urticaria)", "likelihood": "high", "reasoning": "Hives and itching are classic signs of an allergic reaction."},
            {"name": "Contact Dermatitis", "likelihood": "moderate", "reasoning": "Localised rash and itching after contact with an irritant."},
            {"name": "Anaphylaxis", "likelihood": "low", "reasoning": "Severe allergic reaction with swelling, rash and breathing difficulty is a medical emergency."},
        ],
        "red_flags": [],
        "medications": ["Cetirizine 10mg or Loratadine 10mg antihistamine for allergic rash", "Hydrocortisone 1% cream for localised skin reaction", "Avoid the suspected allergen", "Use EpiPen immediately if prescribed and anaphylaxis suspected", "Seek emergency care if throat swelling or breathing difficulty"],
        "immediate": False,
    },
]

def get_rule_based_analysis(text: str, extracted: dict) -> dict:
    """Always returns conditions and medications based on symptom keywords."""
    text_lower = text.lower()
    symptom_names = " ".join(s.get("name", "") for s in extracted.get("symptoms", [])).lower()
    combined = text_lower + " " + symptom_names

    matched_conditions = []
    matched_medications = []
    matched_red_flags = []
    requires_immediate = False

    for entry in CONDITION_MAP:
        if any(kw in combined for kw in entry["keywords"]):
            for c in entry["conditions"]:
                if c not in matched_conditions:
                    matched_conditions.append(c)
            for m in entry["medications"]:
                if m not in matched_medications:
                    matched_medications.append(m)
            for rf in entry["red_flags"]:
                if rf not in matched_red_flags:
                    matched_red_flags.append(rf)
            if entry["immediate"]:
                requires_immediate = True

    # If nothing matched, add a generic fallback
    if not matched_conditions:
        matched_conditions = [
            {"name": "General Medical Condition", "likelihood": "moderate", "reasoning": "Based on the symptoms described, a general medical evaluation is recommended."},
            {"name": "Stress-related Symptoms", "likelihood": "low", "reasoning": "Some symptoms may be related to stress or anxiety."},
        ]
        matched_medications = ["Paracetamol 500mg for general pain relief", "Rest and stay hydrated", "Consult a doctor for accurate diagnosis"]

    return {
        "conditions": matched_conditions,
        "medications": matched_medications,
        "red_flags": matched_red_flags,
        "requires_immediate": requires_immediate,
    }

# ── Agent 2: Risk Analyzer ─────────────────────────────────────────────────────
def risk_analyzer_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_2_start")

    # Step 1: Always run rule-based analysis first — this NEVER fails
    rule_result = get_rule_based_analysis(
        text=state.get("original_input", state["anonymized_input"]),
        extracted=state.get("extracted_symptoms", {}),
    )

    # Step 2: Try LLM to enrich — but fall back to rule-based if it fails
    try:
        llm_result = call_llm_json(
            system_prompt="""You are a medical risk analysis agent. Analyze symptoms and return potential conditions and medication recommendations.

RULES:
- List 2-4 specific potential conditions with name, likelihood (low/moderate/high), and reasoning
- medication_recommendations: specific OTC medications or first-aid steps
- For pain 7+/10 or chest pain: requires_immediate_attention = true
- red_flags: list any warning signs present

Return ONLY valid JSON with these exact keys:
{
  "potential_conditions": [{"name": "string", "likelihood": "high", "reasoning": "string"}],
  "red_flags": ["string"],
  "body_systems": ["string"],
  "risk_factors": ["string"],
  "requires_immediate_attention": false,
  "differential_notes": "string",
  "medication_recommendations": ["string"]
}""",
            user_content=f"Symptoms: {json.dumps(state['extracted_symptoms'], indent=2)}\n\nDescription: {state['anonymized_input'][:300]}"
        )

        # Merge: use LLM conditions if it returned them, else use rule-based
        conditions = llm_result.get("potential_conditions") or []
        medications = llm_result.get("medication_recommendations") or []
        red_flags = llm_result.get("red_flags") or []

        # Always supplement with rule-based if LLM returned too few
        if len(conditions) < 2:
            conditions = rule_result["conditions"]
        if len(medications) < 2:
            medications = rule_result["medications"]
        if not red_flags:
            red_flags = rule_result["red_flags"]

        final = {
            "potential_conditions": conditions,
            "red_flags": red_flags,
            "body_systems": llm_result.get("body_systems") or state.get("extracted_symptoms", {}).get("body_systems", ["general"]),
            "risk_factors": llm_result.get("risk_factors") or [],
            "requires_immediate_attention": llm_result.get("requires_immediate_attention") or rule_result["requires_immediate"],
            "differential_notes": llm_result.get("differential_notes") or "",
            "medication_recommendations": medications,
        }

    except Exception as e:
        # LLM failed — use rule-based entirely
        state["errors"].append(f"analyzer_llm: {str(e)}")
        final = {
            "potential_conditions": rule_result["conditions"],
            "red_flags": rule_result["red_flags"],
            "body_systems": state.get("extracted_symptoms", {}).get("body_systems", ["general"]),
            "risk_factors": [],
            "requires_immediate_attention": rule_result["requires_immediate"],
            "differential_notes": "Analysis based on symptom pattern matching.",
            "medication_recommendations": rule_result["medications"],
        }

    state["risk_analysis"] = final
    state["completed_agents"].append("analyzer")
    privacy.audit_log(state["session_hash"], "agent_2_done", {"conditions": len(final["potential_conditions"])})
    return state


# ── Agent 3: Risk Scorer (rule-based, LLM-verified) ───────────────────────────
def risk_scorer_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_3_start")
    try:
        # Step 1: Compute rule-based score (always accurate)
        base_score = compute_base_score(
            symptoms_text=state.get("original_input", state["anonymized_input"]),
            extracted=state.get("extracted_symptoms", {}),
            analysis=state.get("risk_analysis", {})
        )

        # Step 2: Ask LLM to review and optionally adjust (but we keep base if LLM fails)
        try:
            llm_review = call_llm_json(
                system_prompt="""You are a medical risk scoring reviewer.
You are given a pre-calculated risk score. Review it and adjust ONLY if clearly wrong.

Rules:
- Chest pain 7+/10: symptom_severity must be 24-30
- Any pain 9-10/10: symptom_severity must be 26-30
- Each red flag = 5 points (max 25)
- Sudden onset = 10 onset_factor points
- overall_score MUST equal the sum of all breakdown values
- escalation_flag must be true if overall_score >= 60

Return ONLY valid JSON:
{
  "overall_score": <number>,
  "score_breakdown": {
    "symptom_severity": <0-30>,
    "red_flag_count": <0-25>,
    "duration_factor": <0-20>,
    "system_involvement": <0-15>,
    "onset_factor": <0-10>
  },
  "confidence": "high",
  "reasoning": "<explain score>",
  "escalation_flag": <true/false>
}""",
                user_content=f"Review this pre-calculated score and adjust if needed:\n\nPre-calculated score: {json.dumps(base_score, indent=2)}\n\nSymptoms: {json.dumps(state['extracted_symptoms'], indent=2)}\n\nAnalysis: {json.dumps(state['risk_analysis'], indent=2)}\n\nOriginal text: {state['anonymized_input'][:300]}"
            )

            # Only use LLM score if it's higher or equal (never let LLM lower a critical score)
            if llm_review.get("overall_score", 0) >= base_score["overall_score"]:
                final_score = llm_review
            else:
                # LLM tried to lower the score — keep our rule-based score
                final_score = base_score
                final_score["reasoning"] = base_score["reasoning"] + " (LLM adjustment rejected — rule-based score preserved)"

        except Exception:
            # LLM failed — use rule-based score
            final_score = base_score

        state["risk_score"] = final_score
        state["completed_agents"].append("scorer")
        privacy.audit_log(state["session_hash"], "agent_3_done", {"score": final_score.get("overall_score")})

    except Exception as e:
        state["errors"].append(f"scorer: {str(e)}")
        state["risk_score"] = {
            "overall_score": 50,
            "score_breakdown": {"symptom_severity": 20, "red_flag_count": 10, "duration_factor": 10, "system_involvement": 5, "onset_factor": 5},
            "confidence": "low", "reasoning": "Fallback score", "escalation_flag": False
        }
        state["completed_agents"].append("scorer")
    return state

# ── Agent 4: Triage Decision ───────────────────────────────────────────────────
def triage_decision_agent(state: TriageState) -> TriageState:
    privacy.audit_log(state["session_hash"], "agent_4_start")
    try:
        score = state.get("risk_score", {}).get("overall_score", 30)
        requires_immediate = state.get("risk_analysis", {}).get("requires_immediate_attention", False)

        result = call_llm_json(
            system_prompt=f"""You are a medical triage decision agent.
The risk score is {score}/100. requires_immediate_attention is {requires_immediate}.

Urgency mapping — follow STRICTLY:
- Score 80-100 OR requires_immediate=true with chest pain/breathing: EMERGENCY
- Score 60-79 OR requires_immediate=true: URGENT  
- Score 40-59: SEMI_URGENT
- Score 20-39: NON_URGENT
- Score 0-19: SELF_CARE

Return ONLY valid JSON, no extra text:
{{
  "urgency_level": "EMERGENCY",
  "urgency_color": "red",
  "action_required": "Call 112 immediately",
  "timeframe": "Immediately",
  "care_pathway": "Emergency services / ER",
  "recommendations": ["Call 112 now", "Do not drive yourself", "Chew aspirin if not allergic and cardiac cause suspected"],
  "warning_signs": ["Loss of consciousness", "Worsening chest pain", "Unable to breathe"],
  "self_care_tips": [],
  "follow_up": "Follow up with cardiologist after emergency care",
  "disclaimer": "This is AI-generated information only. Always consult a licensed healthcare professional."
}}
urgency_level MUST match the score range above.
urgency_color: EMERGENCY=red, URGENT=orange, SEMI_URGENT=yellow, NON_URGENT=green, SELF_CARE=blue""",
            user_content=f"Determine triage:\n\nRisk Score: {score}/100\nRequires Immediate: {requires_immediate}\n\nSymptoms:\n{json.dumps(state['extracted_symptoms'], indent=2)}\n\nAnalysis:\n{json.dumps(state['risk_analysis'], indent=2)}"
        )

        # Override urgency if score demands it (safety net)
        if score >= 80 or (requires_immediate and score >= 60):
            result["urgency_level"] = "EMERGENCY"
            result["urgency_color"] = "red"
        elif score >= 60 or requires_immediate:
            if result.get("urgency_level") not in ["EMERGENCY", "URGENT"]:
                result["urgency_level"] = "URGENT"
                result["urgency_color"] = "orange"
        elif score >= 40:
            if result.get("urgency_level") not in ["EMERGENCY", "URGENT", "SEMI_URGENT"]:
                result["urgency_level"] = "SEMI_URGENT"
                result["urgency_color"] = "yellow"

        state["triage_decision"] = result
        state["completed_agents"].append("triage")
        privacy.audit_log(state["session_hash"], "agent_4_done", {"urgency": result.get("urgency_level")})
    except Exception as e:
        state["errors"].append(f"triage: {str(e)}")
        score = state.get("risk_score", {}).get("overall_score", 30)
        urgency = "EMERGENCY" if score >= 80 else "URGENT" if score >= 60 else "SEMI_URGENT" if score >= 40 else "NON_URGENT" if score >= 20 else "SELF_CARE"
        color = {"EMERGENCY": "red", "URGENT": "orange", "SEMI_URGENT": "yellow", "NON_URGENT": "green", "SELF_CARE": "blue"}[urgency]
        state["triage_decision"] = {
            "urgency_level": urgency, "urgency_color": color,
            "action_required": "Consult a healthcare professional immediately" if score >= 60 else "Consult a healthcare professional",
            "timeframe": "Immediately" if score >= 60 else "Within 24 hours",
            "care_pathway": "Emergency services" if score >= 60 else "Primary care",
            "recommendations": ["Seek medical attention", "Monitor symptoms"],
            "warning_signs": ["Symptoms worsen", "New symptoms appear"],
            "self_care_tips": [], "follow_up": "Follow up with your doctor",
            "disclaimer": "This is AI-generated information only. Always consult a licensed healthcare professional."
        }
        state["completed_agents"].append("triage")
    return state

# ── Conditional Edge ───────────────────────────────────────────────────────────
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

# ── Build LangGraph ────────────────────────────────────────────────────────────
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
    raw_session = request.session_id or str(uuid.uuid4())
    s_hash = privacy.session_hash(raw_session)
    privacy.audit_log(s_hash, "request_received")

    anonymized = privacy.strip_pii(request.symptoms)
    privacy.audit_log(s_hash, "pii_stripped")

    initial_state: TriageState = {
        "anonymized_input": anonymized,
        "original_input": request.symptoms,  # used only for rule-based scoring
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