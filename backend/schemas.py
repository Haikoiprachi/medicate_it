from typing import Optional
from pydantic import BaseModel, field_validator


class PatientLocation(BaseModel):
    lat: float
    lon: float


class TriageRequest(BaseModel):
    symptoms: str
    session_id: str = ""
    patient_location: Optional[PatientLocation] = None

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
    notification: Optional[dict] = None
    privacy_log: dict


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str
    phone: str = ""
    specialization: str = ""
    hospital: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ["patient", "doctor"]:
            raise ValueError("Role must be patient or doctor")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str


class AuthResponse(BaseModel):
    token: str
    role: str
    name: str
    email: str
    message: str


class GoogleLoginRequest(BaseModel):
    token: str
