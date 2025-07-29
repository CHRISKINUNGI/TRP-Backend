from pydantic import BaseModel
from typing import List

class Coordinates(BaseModel):
    lat: float
    lng: float

class Address(BaseModel):
    street: str
    city: str
    state: str
    zipCode: str
    country: str
    coordinates: Coordinates

class Property(BaseModel):
    id: str
    title: str
    description: str
    address: Address
    price: float
    bedrooms: int
    bathrooms: int
    squareFeet: int
    propertyType: str
    status: str
    images: List[str]
    amenities: List[str]
    createdAt: str
    updatedAt: str 