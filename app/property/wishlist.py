from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.auth.deps import get_current_user
import httpx
import os
import asyncio
from app.property.api import get_property_by_id

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables or .env file.")

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

# Helper to get Supabase REST endpoint
WISHLIST_ENDPOINT = f"{SUPABASE_URL}/rest/v1/wishlist"

# Add property to wishlist
@router.post("/{property_id}", status_code=201)
async def add_to_wishlist(property_id: str, user=Depends(get_current_user), request: Request = None):
    user_id = user["sub"]
    headers = {
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY
    auth_header = request.headers.get("Authorization") if request else None
    if auth_header:
        headers["Authorization"] = auth_header
    payload = {"user_id": user_id, "property_id": property_id}
    async with httpx.AsyncClient() as client:
        resp = await client.post(WISHLIST_ENDPOINT, json=payload, headers=headers)
        if resp.status_code not in (201, 200):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return {"ok": True}

# Remove property from wishlist
@router.delete("/{property_id}", status_code=204)
async def remove_from_wishlist(property_id: str, user=Depends(get_current_user), request: Request = None):
    user_id = user["sub"]
    headers = {}
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY
    auth_header = request.headers.get("Authorization") if request else None
    if auth_header:
        headers["Authorization"] = auth_header
    # Use query params to delete
    url = f"{WISHLIST_ENDPOINT}?user_id=eq.{user_id}&property_id=eq.{property_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.delete(url, headers=headers)
        if resp.status_code not in (204, 200):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return {"ok": True}

# List all wishlist properties for user
@router.get("/", status_code=200)
async def list_wishlist(user=Depends(get_current_user), request: Request = None):
    user_id = user["sub"]
    headers = {}
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY
    auth_header = request.headers.get("Authorization") if request else None
    if auth_header:
        headers["Authorization"] = auth_header
    url = f"{WISHLIST_ENDPOINT}?user_id=eq.{user_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        wishlist = resp.json()

    # For best performance, batch property_id lookups if possible
    # If not, parallelize using asyncio.gather
    property_ids = [entry["property_id"] for entry in wishlist]
    property_map = {}

    # Try to batch if you have a batch endpoint, else parallelize
    # We'll use the get_property_by_id logic in parallel
    async def fetch_property(property_id):
        # Reuse the get_property_by_id logic (no auth required for this call)
        return await get_property_by_id(property_id)

    property_objs = await asyncio.gather(*[fetch_property(pid) for pid in property_ids])
    for entry, prop in zip(wishlist, property_objs):
        entry["property"] = prop

    return wishlist 