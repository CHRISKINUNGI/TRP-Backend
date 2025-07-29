import os
import httpx
from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from functools import lru_cache
import uuid

# Load environment variables with validation
SUPABASE_JWT_AUD = os.getenv("SUPABASE_JWT_AUD", "authenticated")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF")

# Check if Supabase is configured
SUPABASE_CONFIGURED = bool(SUPABASE_PROJECT_REF and SUPABASE_PROJECT_REF != "<your-project-ref>")

if SUPABASE_CONFIGURED:
    SUPABASE_JWT_ISS = os.getenv("SUPABASE_JWT_ISS", f"https://{SUPABASE_PROJECT_REF}.supabase.co/auth/v1")
    SUPABASE_JWKS_URL = f"{SUPABASE_JWT_ISS}/.well-known/jwks.json"
else:
    print("Warning: Supabase not configured. Auth will be bypassed in development.")
    SUPABASE_JWT_ISS = None
    SUPABASE_JWKS_URL = None

@lru_cache()
def get_jwks():
    if not SUPABASE_CONFIGURED:
        return []
    try:
        resp = httpx.get(SUPABASE_JWKS_URL, timeout=10.0)
        resp.raise_for_status()
        return resp.json()["keys"]
    except Exception as e:
        print(f"Warning: Failed to fetch JWKS: {str(e)}")
        return []

def get_public_key(token):
    jwks = get_jwks()
    if not jwks:
        return None
    try:
        unverified_header = jwt.get_unverified_header(token)
        for key in jwks:
            if key["kid"] == unverified_header["kid"]:
                return jwt.construct_rsa_public_key(key)
    except Exception as e:
        print(f"Warning: Error constructing public key: {e}")
    raise HTTPException(status_code=401, detail="Invalid token header")

async def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.split(" ", 1)[1]
    try:
        # For dev, decode without verification, but require sub to be a UUID
        payload = jwt.decode(
            token,
            key="",  # <-- required for python-jose
            options={"verify_signature": False, "verify_aud": False, "verify_iss": False},
        )
        # Ensure sub is a valid UUID
        uuid.UUID(payload["sub"])
        return payload
    except Exception as e:
        print(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or missing JWT. You must be logged in with a real Supabase user.") 