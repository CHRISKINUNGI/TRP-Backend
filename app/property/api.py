import os
import asyncio
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
import httpx

from .models import Property
from .clients import MLS_CONFIGURED
from .services import transform_property

if MLS_CONFIGURED:
    from .clients import (
        fetch_preferred_largest_media, 
        fetch_largest_media, 
        MLS_API_URL, 
        MLS_AUTH_TOKEN
    )
else:
    print("MLS not configured - using mock data mode")
    MLS_API_URL = None
    MLS_AUTH_TOKEN = None

router = APIRouter()

# Configuration constants
PROPERTY_TOP_LIMIT = int(os.getenv("PROPERTY_TOP_LIMIT", 24))
REQUEST_TIMEOUT = 30.0
CONCURRENCY_LIMIT = 4

# Semaphore for controlling concurrent requests
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

def build_filter_str(
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_beds: Optional[int] = None,
    max_beds: Optional[int] = None,
    min_baths: Optional[int] = None,
    max_baths: Optional[int] = None,
    property_type: Optional[str] = None
) -> Optional[str]:
    """Build OData filter string for MLS API queries."""
    filters = [
        "PropertyType eq 'Residential Freehold'",
        "RentalApplicationYN eq true",
        "OriginatingSystemName eq 'Toronto Regional Real Estate Board'"
    ]
    
    # Location filter
    if city:
        filters.append(f"contains(City, '{city}')")
    
    # Price filters
    if min_price is not None:
        filters.append(f"ListPrice ge {min_price}")
    if max_price is not None:
        filters.append(f"ListPrice le {max_price}")
    
    # Bedroom filters
    if min_beds is not None:
        filters.append(f"BedroomsTotal ge {min_beds}")
    if max_beds is not None:
        filters.append(f"BedroomsTotal le {max_beds}")
    
    # Bathroom filters
    if min_baths is not None:
        filters.append(f"BathroomsTotalInteger ge {min_baths}")
    if max_baths is not None:
        filters.append(f"BathroomsTotalInteger le {max_baths}")
    
    return ' and '.join(filters)

async def get_transformed_property(mls_property: dict) -> Optional[Property]:
    """Transform MLS property data with media URLs."""
    listing_key = mls_property.get("ListingKey")
    if not listing_key:
        return None
    
    async with semaphore:
        media_urls = await fetch_preferred_largest_media(listing_key)
    
    return transform_property(mls_property, media_urls)


async def fetch_mls_data(url: str) -> List[dict]:
    """Fetch data from MLS API with proper error handling."""
    if not MLS_CONFIGURED:
        raise HTTPException(
            status_code=503,
            detail="MLS API not configured."
        )
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {MLS_AUTH_TOKEN}",
                "Accept": "application/json"
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("value", [])

@router.get("/properties", response_model=List[Property])
async def get_properties(
    limit: int = Query(
        default=PROPERTY_TOP_LIMIT, 
        ge=1, 
        le=50, 
        description="Number of properties to return"
    ),
    city: Optional[str] = Query(None, description="Filter by city"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    min_beds: Optional[int] = Query(None, description="Minimum bedrooms"),
    max_beds: Optional[int] = Query(None, description="Maximum bedrooms"),
    min_baths: Optional[int] = Query(None, description="Minimum bathrooms"),
    max_baths: Optional[int] = Query(None, description="Maximum bathrooms"),
    property_type: Optional[str] = Query(None, description="Property type (ignored)")
):
    """Get list of properties with optional filtering."""
    try:
        filter_str = build_filter_str(
            city=city,
            min_price=min_price,
            max_price=max_price,
            min_beds=min_beds,
            max_beds=max_beds,
            min_baths=min_baths,
            max_baths=max_baths,
            property_type=property_type
        )
        
        url = f"{MLS_API_URL}/Property?$top={limit}"
        if filter_str:
            url += f"&$filter={filter_str}"
        
        mls_properties = await fetch_mls_data(url)
        if not mls_properties:
            return []
        
        # Transform properties concurrently
        tasks = [get_transformed_property(prop) for prop in mls_properties]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        return [result for result in results if result is not None]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching properties: {str(e)}"
        )

@router.get("/properties/{property_id}")
async def get_property_by_id(
    property_id: str = Path(..., description="MLS ListingKey")
):
    """Get detailed information for a specific property."""
    try:
        url = f"{MLS_API_URL}/Property?$filter=ListingKey eq '{property_id}'"
        mls_properties = await fetch_mls_data(url)
        
        if not mls_properties:
            return {"error": "Property not found"}
        
        mls_property = mls_properties[0]
        images = await fetch_largest_media(property_id)
        
        # Build formatted address
        address_parts = [
            mls_property.get("PropertyAddress", ""),
            mls_property.get("City", ""),
            mls_property.get("StateOrProvince", ""),
            mls_property.get("PostalCode", ""),
            mls_property.get("Country", "") or "CA"
        ]
        address_str = ", ".join(filter(None, address_parts))
        
        return {
            "id": mls_property.get("ListingKey", property_id),
            "images": images,
            "price": mls_property.get("ListPrice", ""),
            "address": address_str,
            "added": mls_property.get("ListingContractDate", ""),
            "beds": int(mls_property.get("BedroomsTotal", 0) or 0),
            "baths": int(mls_property.get("BathroomsTotalInteger", 0) or 0),
            "parking": int(mls_property.get("ParkingTotal", 0) or 0),
            "sqft": mls_property.get("LivingArea", ""),
            "location": mls_property.get("City", ""),
            "areaCode": mls_property.get("Area", ""),
            "propertyType": mls_property.get("PropertyType", ""),
            "availableDate": mls_property.get("AvailableDate", ""),
            "leaseTerms": mls_property.get("LeaseTerm", ""),
            "description": mls_property.get("PublicRemarks", "") or mls_property.get("PrivateRemarks", "") or ""
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        return {"error": f"Error fetching property: {str(e)}"}
