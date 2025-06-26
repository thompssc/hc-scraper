"""
Restaurant data models for HappyCow scraping
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re

class Coordinates(BaseModel):
    """Geographic coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    @validator('latitude', 'longitude')
    def validate_coordinates(cls, v):
        if v is None:
            raise ValueError('Coordinates cannot be None')
        return round(v, 6)  # 6 decimal places for good precision

class Address(BaseModel):
    """Restaurant address information"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    full_address: Optional[str] = None

class ContactInfo(BaseModel):
    """Restaurant contact information"""
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None

class VeganInfo(BaseModel):
    """Vegan-specific information"""
    vegan_category: Optional[str] = None  # 'vegan', 'vegetarian', 'veg-friendly'
    has_vegan_options: bool = False
    is_fully_vegan: bool = False
    cross_contamination_notes: Optional[str] = None
    dietary_notes: List[str] = Field(default_factory=list)

class OperatingHours(BaseModel):
    """Restaurant operating hours"""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    special_notes: Optional[str] = None

class Restaurant(BaseModel):
    """Complete restaurant information from HappyCow"""
    
    # Basic Info
    happycow_id: Optional[str] = None
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    
    # Location
    address: Address = Field(default_factory=Address)
    coordinates: Optional[Coordinates] = None
    
    # Contact
    contact: ContactInfo = Field(default_factory=ContactInfo)
    
    # Vegan Info
    vegan_info: VeganInfo = Field(default_factory=VeganInfo)
    
    # Ratings & Reviews
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = Field(None, ge=0)
    
    # Operations
    hours: Optional[OperatingHours] = None
    price_range: Optional[str] = None  # '$', '$$', '$$$', '$$$$'
    
    # Features
    features: List[str] = Field(default_factory=list)  # delivery, takeout, etc.
    accessibility: List[str] = Field(default_factory=list)
    parking: Optional[str] = None
    
    # Status
    is_open: Optional[bool] = None
    is_new: bool = False
    is_top_rated: bool = False
    is_partner: bool = False
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.now)
    source_url: Optional[str] = None
    source_city: Optional[str] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Restaurant name cannot be empty')
        return v.strip()

class ScrapingResult(BaseModel):
    """Result of scraping a city"""
    city: str
    url: str
    restaurants: List[Restaurant]
    total_found: int
    successful_extractions: int
    failed_extractions: int
    scraped_at: datetime = Field(default_factory=datetime.now)
    errors: List[str] = Field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_found == 0:
            return 0.0
        return (self.successful_extractions / self.total_found) * 100

def extract_coordinates_from_maps_url(url: str) -> Optional[Coordinates]:
    """Extract coordinates from Google Maps URL"""
    if not url:
        return None
    
    # Pattern for Google Maps URLs with coordinates
    # https://www.google.com/maps?q=40.7128,-74.0060
    pattern = r'q=(-?\d+\.?\d*),(-?\d+\.?\d*)'
    match = re.search(pattern, url)
    
    if match:
        try:
            lat = float(match.group(1))
            lng = float(match.group(2))
            return Coordinates(latitude=lat, longitude=lng)
        except ValueError:
            return None
    
    return None

def parse_vegan_category(category_text: str) -> VeganInfo:
    """Parse vegan category from HappyCow text"""
    vegan_info = VeganInfo()
    
    if not category_text:
        return vegan_info
    
    category_lower = category_text.lower()
    
    if 'vegan' in category_lower and 'friendly' not in category_lower:
        vegan_info.vegan_category = 'vegan'
        vegan_info.is_fully_vegan = True
        vegan_info.has_vegan_options = True
    elif 'vegetarian' in category_lower:
        vegan_info.vegan_category = 'vegetarian'
        vegan_info.has_vegan_options = True
    elif 'veg-friendly' in category_lower or 'vegan-friendly' in category_lower:
        vegan_info.vegan_category = 'veg-friendly'
        vegan_info.has_vegan_options = True
    
    return vegan_info 