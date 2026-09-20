from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Ingredient(BaseModel):
    name: str
    raw: str
    amount: Decimal | None = None
    unit: str | None = None


class Recipe(BaseModel):
    id: UUID
    title: str
    category: str
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    servings: Decimal | None = None
    source_url: str | None = None
    content_hash: str
    ingredient_status: Literal['complete', 'partial', 'unparsed']
    raw_text: str


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    diners: int = Field(ge=1, le=12)
    days: int = Field(default=7, ge=1, le=7)
    meal_slots: list[Literal['breakfast', 'lunch', 'dinner']] = Field(
        default_factory=lambda: ['dinner'], min_length=1, max_length=3)
    tastes: list[str] = Field(default_factory=list, max_length=20)
    allergens: list[str] = Field(default_factory=list, max_length=30)
    excluded_ingredients: list[str] = Field(default_factory=list, max_length=50)
    pantry: list[str] = Field(default_factory=list, max_length=100)
    allow_repeats: bool = False

    @field_validator('meal_slots')
    @classmethod
    def unique_slots(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('餐次不能重复')
        return value
