from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


PLASTIC_CATEGORIES = {"rigid_plastic", "flexible_plastic", "multilayer_plastic"}


class DeclarationIn(BaseModel):
    producer_id: str = Field(..., min_length=1, examples=["GREENPACK-001"])
    month: str = Field(..., examples=["2026-04"])
    declared_quantities_kg: Dict[str, float]

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m")
        except ValueError as exc:
            raise ValueError("month must use YYYY-MM format") from exc
        return value

    @field_validator("declared_quantities_kg")
    @classmethod
    def validate_quantities(cls, value: Dict[str, float]) -> Dict[str, float]:
        missing = PLASTIC_CATEGORIES - set(value)
        unknown = set(value) - PLASTIC_CATEGORIES
        if missing:
            raise ValueError(f"missing categories: {', '.join(sorted(missing))}")
        if unknown:
            raise ValueError(f"unknown categories: {', '.join(sorted(unknown))}")
        for category, amount in value.items():
            if amount < 0:
                raise ValueError(f"{category} cannot be negative")
        return value


class DeclarationRecord(DeclarationIn):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class CategoryReconciliation(BaseModel):
    category: str
    declared_kg: float
    procured_kg: float
    variance_kg: float
    variance_percent: float
    flagged: bool


class SummaryResponse(BaseModel):
    producer_id: str
    month: str
    tolerance_percent: float
    overall_status: str
    reconciliation: List[CategoryReconciliation]
    narrative: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, examples=["What should GreenPack do if EPR targets are missed?"])


class Citation(BaseModel):
    document: str
    section: str


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
