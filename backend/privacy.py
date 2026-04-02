import re
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger("medtriage")

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
