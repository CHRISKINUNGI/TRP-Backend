import os
import asyncio
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
import httpx

# Import the existing schemas if available, otherwise we'll create simple response models
try:
    from schemas.property import PropertyResponse
except ImportError:
    from pydantic import BaseModel
    
    class PropertyResponse(BaseModel):
        id: str
        images: List[str] = []
        price: str = ""
        address: str = ""
        beds: int = 0
        baths: int = 0

router = APIRouter(tags=["properties"])

# Configuration constants
PROPERTY_TOP_LIMIT = int(os.getenv("PROPERTY_TOP_LIMIT", 24))
REQUEST_TIMEOUT = 30.0
CONCURRENCY_LIMIT = 4

# MLS Configuration
MLS_API_URL = os.getenv("MLS_API_URL")
MLS_AUTH_TOKEN = os.getenv("MLS_AUTH_TOKEN")
MLS_CONFIGURED = bool(MLS_API_URL and MLS_AUTH_TOKEN)

if not MLS_CONFIGURED:
    print("MLS not configured - using mock data mode")

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

async def fetch_largest_media(listing_key: str) -> List[str]:
    """Fetch largest media images for a property."""
    if not MLS_CONFIGURED:
        return []
    
    try:
        url = f"{MLS_API_URL}/Media?$filter=ResourceRecordKey eq '{listing_key}' and LargePhotoExists eq true&$orderby=Order"
        
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
            media_data = response.json().get("value", [])
            
            return [item.get("MediaURL", "") for item in media_data if item.get("MediaURL")]
    except Exception as e:
        print(f"Error fetching media for {listing_key}: {e}")
        return []

def transform_property(mls_property: dict, media_urls: List[str] = None) -> dict:
    """Transform MLS property data to our API format."""
    if media_urls is None:
        media_urls = []
    
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
        "id": mls_property.get("ListingKey", ""),
        "images": media_urls,
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

async def get_transformed_property(mls_property: dict) -> Optional[dict]:
    """Transform MLS property data with media URLs."""
    listing_key = mls_property.get("ListingKey")
    if not listing_key:
        return None
    
    async with semaphore:
        media_urls = await fetch_largest_media(listing_key)
    
    return transform_property(mls_property, media_urls)

@router.get("/", response_model=List[dict])
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

@router.get("/{property_id}")
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
        
        return transform_property(mls_property, images)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        return {"error": f"Error fetching property: {str(e)}"}

@router.get("/selected-fields", response_model=MLSAPIResponse, summary="Get Properties with Selected Fields")
async def get_properties_selected_fields(
    top_limit: Optional[int] = Query(None, description="Maximum number of results to return")
):
    """Get properties with only $select and $top filters (no $filter)."""
    try:
        top_limit = top_limit or int(settings.MLS_TOP_LIMIT)
        select_fields = settings.MLS_PPROPERTY_FILTER_FIELDS
        return await property_service.get_properties_with_selected_fields(
            top_limit=top_limit,
            select_fields=select_fields
        )
    except MLSAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.message, "external_detail": e.detail}
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        return {"error": f"Error fetching property: {str(e)}"}

@router.get("/get/{property_id}", response_model=PropertyDetail)
async def get_property(property_id: str):
    """Get specific property details"""
    try:
        select_fields = settings.MLS_PPROPERTY_FILTER_FIELDS
        return await property_service.get_property_by_id(property_id, select_fields)
    except MLSAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.message, "external_detail": e.detail}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/enhanced-search", response_model=MLSAPIResponse)
async def enhanced_search_properties(
    limit: int = Query(24, ge=1, le=50, description="Number of properties to return"),
    city: Optional[str] = Query(None, description="Filter by city"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    min_beds: Optional[int] = Query(None, description="Minimum bedrooms"),
    max_beds: Optional[int] = Query(None, description="Maximum bedrooms"),
    min_baths: Optional[int] = Query(None, description="Minimum bathrooms"),
    max_baths: Optional[int] = Query(None, description="Maximum bathrooms"),
    property_type: Optional[str] = Query(None, description="Property type")
):
    """Enhanced property search with comprehensive filtering options"""
    try:
        # Build enhanced filter string
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
        
        filter_string = ' and '.join(filters)
        select_fields = settings.MLS_PPROPERTY_FILTER_FIELDS
        
        return await property_service.search_properties_by_filters(
            filters=filter_string,
            top_limit=limit,
            select_fields=select_fields
        )
    except MLSAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.message, "external_detail": e.detail}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching properties: {str(e)}"
        )

@router.get("/media/{property_id}", response_model=MediaResponse, summary="Get Property Images with Selected Fields")
async def get_property_media_with_fields(property_id: str):
    """Get property media/images with selected fields filter"""
    try:
        select_fields = getattr(settings, 'MLS_PROPERTY_IMAGE_FILTER_FIELDS', 
            'ImageHeight,ImageSizeDescription,ImageWidth,MediaKey,MediaObjectID,MediaType,MediaURL,Order,ResourceRecordKey')
        return await property_service.get_property_media_with_fields(property_id, select_fields)
    except MLSAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.message, "external_detail": e.detail}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/media-simple/{property_id}", response_model=MediaResponse, summary="Get Property Images")
async def get_property_media_simple(property_id: str):
    """Get property media/images with minimal filters - just ResourceRecordKey filter"""
    try:
        return await property_service.get_property_media_simple(property_id)
    except MLSAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.message, "external_detail": e.detail}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) 