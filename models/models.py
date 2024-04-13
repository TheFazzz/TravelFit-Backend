from typing import List, Optional
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    

class ReturnIdResponse(BaseModel):
    id: int

class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    password: str

class GymCreateRequest(BaseModel):
    gym_name: str
    gym_description: str
    address1: str
    address2: Optional[str] = None
    city: str
    state: str
    zipcode: str
    amenities: Optional[List[str]] = Field(default_factory=list)
    hours_of_operation: Optional[dict] = None

class GymUpdateRequest(BaseModel):
    gym_name: Optional[str] = None
    gym_description: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    amenities: Optional[List[str]] = Field(default_factory=list)
    hours_of_operation: Optional[dict] = None

class PassOptionCreateRequest(BaseModel):
    pass_name: str
    price: Decimal = Field(default=0, max_digits=5, decimal_places=2)
    duration: int
    description: Optional[str] = None 

    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

class PassOptionResponse(BaseModel):
    id: int
    gym_id: int
    pass_name: str
    price: Decimal
    duration: int
    description: str  

class Coordinate(BaseModel):
    latitude: float
    longitude: float

class GymCityResponse(BaseModel):
    id: int
    gym_name: str
    coordinate: Coordinate

class UserLocation(BaseModel):
    latitude: float
    longitude: float
    radius_in_meters: float = 2000  # Default radius of 2000 meters or user specify

class UpdateUserInfo(BaseModel):
    firstName: Optional[str]
    lastName: Optional[str]
    email: Optional[str]

class ScannedQrCodeData(BaseModel):
    pass_id: int
    user_id: int
    gym_id: int
    pass_name: str
    duration: int
