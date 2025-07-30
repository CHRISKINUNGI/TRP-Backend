import os
import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from core.dependencies import get_current_user

router = APIRouter(tags=["cart"])

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
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
            return {"ok": True}
        elif resp.status_code == 409:
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

    # Validate user isolation
    for entry in cart_rows:
        if entry["user_id"] != user_id:
            raise HTTPException(status_code=500, detail="Data integrity error: cart contains items from other users")
    
    # Get property details for cart items
    property_ids = [entry["property_id"] for entry in cart_rows]
    # Note: This would need to integrate with the existing property service
    # For now, return the property IDs
    
    return {"cart": property_ids, "user_id": user_id, "count": len(property_ids)}
