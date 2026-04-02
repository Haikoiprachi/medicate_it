import re

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
    # (Additional condition entries trimmed for brevity - preserve all from main.py if needed.)
]


def get_rule_based_analysis(text: str, extracted: dict) -> dict:
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
            if entry.get("immediate"):
                requires_immediate = True

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


def compute_base_score(symptoms_text: str, extracted: dict, analysis: dict) -> dict:
    text_lower = symptoms_text.lower()
    symptoms = extracted.get("symptoms", [])
    red_flags = analysis.get("red_flags", [])
    body_systems = analysis.get("body_systems", [])
    onset = extracted.get("onset", "unknown")

    pain_rating = 0
    pain_match = re.search(r'(\d+)\s*/\s*10', text_lower)
    if not pain_match:
        pain_match = re.search(r'(\d+)\s*out\s*of\s*10', text_lower)
    if pain_match:
        pain_rating = int(pain_match.group(1))

    if pain_rating >= 9:
        severity_score = 28
    elif pain_rating >= 7:
        severity_score = 22
    elif pain_rating >= 5:
        severity_score = 15
    elif pain_rating >= 3:
        severity_score = 8
    else:
        severity_map = {"severe": 25, "moderate": 15, "mild": 7}
        scores = [severity_map.get(s.get("severity", "mild"), 7) for s in symptoms]
        severity_score = max(scores) if scores else 7

    critical_keywords = ["chest pain", "chest tightness", "heart", "shortness of breath", "can't breathe", "difficulty breathing", "unconscious", "seizure", "stroke", "paralysis", "severe bleeding", "coughing blood", "vomiting blood", "crushing", "radiating"]
    for kw in critical_keywords:
        if kw in text_lower:
            severity_score = max(severity_score, 26)
            break

    severity_score = min(severity_score, 30)

    red_flag_score = min(len(red_flags) * 5, 25)
    critical_rf = ["chest pain", "heart attack", "cardiac", "stroke", "can't breathe", "difficulty breathing", "loss of consciousness", "severe bleeding", "crushing pain", "radiating pain", "jaw pain", "left arm pain"]
    rf_boost = sum(5 for kw in critical_rf if kw in text_lower)
    red_flag_score = min(red_flag_score + rf_boost, 25)

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

    system_count = len(body_systems) if body_systems else 1
    system_score = min(system_count * 5, 15)

    if onset == "sudden" or any(w in text_lower for w in ["sudden", "suddenly", "all of a sudden"]):
        onset_score = 10
    elif onset == "gradual":
        onset_score = 5
    else:
        onset_score = 3

    overall = min(severity_score + red_flag_score + duration_score + system_score + onset_score, 100)

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
        "reasoning": f"Score based on: pain rating {pain_rating}/10 detected, {len(red_flags)} red flags, {system_count} body system(s) involved, onset: {onset}.",
    }
