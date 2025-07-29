from .models import Property, Address, Coordinates
from typing import List

def transform_property(mls_property: dict, media_urls: List[str]) -> Property:
    """Transform MLS property data to frontend schema"""
    try:
        # Safe extraction with defaults
        listing_key = mls_property.get("ListingKey", "")
        title = mls_property.get("PublicRemarks", "") or mls_property.get("ListingTitle", "") or "No title available"
        description = mls_property.get("PublicRemarks", "") or "No description available"
        
        # Address handling
        address_line = mls_property.get("PropertyAddress", "") or ""
        city = mls_property.get("City", "") or "Unknown"
        state = mls_property.get("StateOrProvince", "") or "Unknown"
        zip_code = mls_property.get("PostalCode", "") or "Unknown"
        country = mls_property.get("Country", "") or "CA"
        
        # Safe numeric conversions
        try:
            price = float(mls_property.get("ListPrice", 0)) or 0.0
        except (ValueError, TypeError):
            price = 0.0
            
        try:
            bedrooms = int(mls_property.get("BedroomsTotal", 0)) or 0
        except (ValueError, TypeError):
            bedrooms = 0
            
        try:
            bathrooms = int(mls_property.get("BathroomsTotalInteger", 0)) or 0
        except (ValueError, TypeError):
            bathrooms = 0
            
        try:
            square_feet = int(mls_property.get("LivingArea", 0)) or 0
        except (ValueError, TypeError):
            square_feet = 0
        
        # Property type mapping
        property_type_map = {
            "Residential": "house",
            "Condo": "apartment", 
            "Commercial": "commercial",
            "Land": "land",
            "Farm": "farm"
        }
        mls_property_type = mls_property.get("PropertyType", "Residential")
        property_type = property_type_map.get(mls_property_type, "house")
        
        # Status mapping
        status_map = {
            "Active": "available",
            "Pending": "pending",
            "Sold": "sold",
            "Expired": "expired"
        }
        mls_status = mls_property.get("MlsStatus", "Active")
        status = status_map.get(mls_status, "available")
        
        # Amenities (extract from features if available)
        amenities = []
        features = mls_property.get("Features", "")
        if features:
            amenities = [feature.strip() for feature in features.split(",") if feature.strip()]
        
        # Dates
        created_date = mls_property.get("ListingContractDate", "") or "2024-01-01"
        modified_date = mls_property.get("ModificationTimestamp", "") or "2024-01-01T00:00:00.000Z"
        
        return Property(
            id=listing_key,
            title=title[:200] + "..." if len(title) > 200 else title,
            description=description[:500] + "..." if len(description) > 500 else description,
            address=Address(
                street=address_line,
                city=city,
                state=state,
                zipCode=zip_code,
                country=country,
                coordinates=Coordinates(lat=0.0, lng=0.0)
            ),
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            squareFeet=square_feet,
            propertyType=property_type,
            status=status,
            images=media_urls,
            amenities=amenities,
            createdAt=created_date,
            updatedAt=modified_date
        )
    except Exception as e:
        print(f"Error transforming property {mls_property.get('ListingKey', 'unknown')}: {e}")
        # Return a minimal valid property
        return Property(
            id=mls_property.get("ListingKey", "unknown"),
            title="Error loading property",
            description="Error loading property details",
            address=Address(
                street="Unknown",
                city="Unknown", 
                state="Unknown",
                zipCode="Unknown",
                country="CA",
                coordinates=Coordinates(lat=0.0, lng=0.0)
            ),
            price=0.0,
            bedrooms=0,
            bathrooms=0,
            squareFeet=0,
            propertyType="house",
            status="available",
            images=[],
            amenities=[],
            createdAt="2024-01-01",
            updatedAt="2024-01-01T00:00:00.000Z"
        ) 