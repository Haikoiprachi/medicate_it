from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from authlib.integrations.httpx_client import AsyncOAuth2Client
import httpx
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

JWT_SECRET    = os.getenv("JWT_SECRET", "fallback_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY    = int(os.getenv("JWT_EXPIRY_HOURS", 24))

def hash_password(plain: str) -> str:
    safe = plain.encode("utf-8")[:72].decode("utf-8", "ignore")
    return pwd_context.hash(safe)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain[:72], hashed)
    except Exception:
        return False

def create_token(data: dict) -> str:
    payload = data.copy()
    payload.update({"exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY)})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
# Verify Google Token 
async def verify_google_token(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'https://oauth2.googleapis.com/tokeninfo?id_token={token}'
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        user_info = response.json()
        # ✅ Validate audience (VERY IMPORTANT)
        if user_info.get("aud") != os.getenv("GOOGLE_CLIENT_ID"):
            raise HTTPException(status_code=400, detail="Invalid audience")
        # ✅ Validate issuer
        if user_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise HTTPException(status_code=400, detail="Invalid issuer")

        return user_info
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)

def generate_id() -> str:
    return str(uuid.uuid4())