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

router = APIRouter(prefix="/cart", tags=["cart"])

# Helper to get Supabase REST endpoint
CART_ENDPOINT = f"{SUPABASE_URL}/rest/v1/cart"

# Add property to cart
@router.post("/{property_id}", status_code=201)
async def add_to_cart(property_id: str, user=Depends(get_current_user), request: Request = None):
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
        resp = await client.post(CART_ENDPOINT, headers=headers, json=payload)
        if resp.status_code in (201, 200):
            return resp.json()
        # Gracefully handle unique constraint violation
        if resp.status_code == 409 or ("duplicate key" in resp.text or "already exists" in resp.text or "unique constraint" in resp.text):
            return {"ok": True, "message": "Already in cart"}
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

# Remove property from cart
@router.delete("/{property_id}", status_code=204)
async def remove_from_cart(property_id: str, user=Depends(get_current_user), request: Request = None):
    user_id = user["sub"]
    headers = {}
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY
    auth_header = request.headers.get("Authorization") if request else None
    if auth_header:
        headers["Authorization"] = auth_header
    # Use query params to delete
    url = f"{CART_ENDPOINT}?user_id=eq.{user_id}&property_id=eq.{property_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.delete(url, headers=headers)
        if resp.status_code not in (204, 200):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return {"ok": True}

# List all cart properties for user
@router.get("/", status_code=200)
async def list_cart(user=Depends(get_current_user), request: Request = None):
    user_id = user["sub"]
    
    headers = {}
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY
    auth_header = request.headers.get("Authorization") if request else None
    if auth_header:
        headers["Authorization"] = auth_header
    url = f"{CART_ENDPOINT}?user_id=eq.{user_id}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        cart_rows = resp.json()

    # Validate that all returned entries belong to the current user
    for entry in cart_rows:
        if entry.get("user_id") != user_id:
            raise HTTPException(status_code=500, detail="Data integrity error: cart contains items from other users")

    # Fetch all property objects in parallel
    property_ids = [entry["property_id"] for entry in cart_rows]
    
    async def fetch_property(property_id):
        return await get_property_by_id(property_id)
    property_objs = await asyncio.gather(*[fetch_property(pid) for pid in property_ids])
    # Only include non-null properties
    cart = [prop for prop in property_objs if prop]
    
    return {"cart": cart, "user_id": user_id, "debug_info": {"raw_entries": len(cart_rows), "valid_properties": len(cart)}} 