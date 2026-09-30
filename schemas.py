from typing import Literal

from pydantic import BaseModel, Field, field_validator


Currency = Literal["USD", "INR", "EUR", "GBP"]


class RequestedItem(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    quantity: int = Field(default=1, ge=1, le=20)


class RoomInput(BaseModel):
    room_type: str = Field(min_length=2, max_length=40)
    items: list[RequestedItem] = Field(min_length=1, max_length=8)


class HomeInput(BaseModel):
    budget: float = Field(gt=0, le=100_000_000)
    currency: Currency = "USD"
    style: str = Field(default="Warm modern", min_length=2, max_length=50)
    rooms: list[RoomInput] = Field(min_length=1, max_length=6)


class PartyInput(BaseModel):
    budget: float = Field(gt=0, le=100_000_000)
    currency: Currency = "USD"
    event_type: str = Field(min_length=2, max_length=40)
    guests: int = Field(ge=1, le=10_000)
    city: str = Field(min_length=2, max_length=80)
    venue: str = Field(default="Flexible", max_length=80)
    food_style: str = Field(default="Mixed menu", max_length=60)


class JewelryInput(BaseModel):
    budget: float = Field(gt=0, le=100_000_000)
    currency: Currency = "USD"
    occasion: str = Field(min_length=2, max_length=60)
    style: str = Field(min_length=2, max_length=60)
    outfit_colors: str = Field(default="", max_length=120)


class Allocation(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    amount: float = Field(ge=0)
    rationale: str = Field(min_length=1, max_length=240)


class SuggestedItem(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    price: float = Field(ge=0)
    quantity: int = Field(default=1, ge=1, le=100)
    platform: Literal["Amazon", "Flipkart", "IKEA", "Swiggy", "Zomato", "OYO"]
    reason: str = Field(min_length=1, max_length=240)


class RecommendationPlan(BaseModel):
    summary: str = Field(min_length=5, max_length=500)
    allocations: list[Allocation] = Field(min_length=1, max_length=12)
    recommendations: list[SuggestedItem] = Field(min_length=1, max_length=20)
    insights: list[str] = Field(default_factory=list, max_length=8)


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_must_look_valid(cls, value: str) -> str:
        email = value.strip().lower()
        if email.count("@") != 1 or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return email

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return value.strip()