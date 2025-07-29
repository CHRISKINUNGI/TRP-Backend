import os
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

MLS_API_URL = os.getenv("MLS_API_URL")
MLS_AUTH_TOKEN = os.getenv("MLS_AUTH_TOKEN")
MLS_TOP_LIMIT = os.getenv("MLS_TOP_LIMIT", "12")

# Validate required environment variables
def is_placeholder_value(value):
    """Check if a value is a placeholder"""
    if not value:
        return True
    placeholder_patterns = ["your_", "placeholder", "example", "change_me", "replace_me"]
    return any(pattern in value.lower() for pattern in placeholder_patterns)

def is_valid_url(url):
    """Check if URL has proper protocol"""
    if not url:
        return False
    return url.startswith(('http://', 'https://'))

# Check MLS configuration
MLS_CONFIGURED = False
if MLS_API_URL and MLS_AUTH_TOKEN:
    if not is_placeholder_value(MLS_API_URL) and not is_placeholder_value(MLS_AUTH_TOKEN):
        if is_valid_url(MLS_API_URL):
            MLS_CONFIGURED = True
        else:
            print(f"Warning: MLS_API_URL is not a valid URL: {MLS_API_URL}")
    else:
        print("Warning: MLS API has placeholder values. Use mock endpoints for development.")
else:
    print("Warning: MLS_API_URL and/or MLS_AUTH_TOKEN not set")

async def fetch_mls_properties(limit: int = 12):
    """Fetch properties from MLS API with custom filter"""
    filter_str = (
        "PropertyType eq 'Residential Freehold' and "
        "RentalApplicationYN eq true and "
        "OriginatingSystemName eq 'Toronto Regional Real Estate Board'"
    )
    url = f"{MLS_API_URL}/Property?$top={limit}&$filter={filter_str}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {MLS_AUTH_TOKEN}",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json().get("value", [])
        except Exception as e:
            print(f"Error fetching MLS properties: {e}")
            return []

async def fetch_preferred_largest_media(listing_key: str):
    """Fetch preferred largest images for a specific property. If none, fallback to all largest."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{MLS_API_URL}/Media?$filter=ResourceRecordKey eq '{listing_key}'",
                headers={
                    "Authorization": f"Bearer {MLS_AUTH_TOKEN}",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            media_data = response.json().get("value", [])
            preferred = [item for item in media_data if item.get("PreferredPhotoYN") and item.get("ImageSizeDescription") == "Largest"]
            if preferred:
                return [item.get("MediaURL", "") for item in preferred if item.get("MediaURL")]
            # fallback to all largest
            largest = [item for item in media_data if item.get("ImageSizeDescription") == "Largest"]
            return [item.get("MediaURL", "") for item in largest if item.get("MediaURL")]
        except Exception as e:
            print(f"Error fetching media for {listing_key}: {e}")
            return []

async def fetch_largest_media(listing_key: str):
    """Fetch all largest images for a specific property"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{MLS_API_URL}/Media?$filter=ResourceRecordKey eq '{listing_key}'",
                headers={
                    "Authorization": f"Bearer {MLS_AUTH_TOKEN}",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            media_data = response.json().get("value", [])
            largest = [item for item in media_data if item.get("ImageSizeDescription") == "Largest"]
            return [item.get("MediaURL", "") for item in largest if item.get("MediaURL")]
        except Exception as e:
            print(f"Error fetching media for {listing_key}: {e}")
            return [] 