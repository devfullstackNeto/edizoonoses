from datetime import datetime
from pydantic import BaseModel, Field


class OccurrenceIn(BaseModel):
    type: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=3)
    address: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    territory: str = Field(min_length=2)
    status: str = "Pendente"
    priority: str = "Média"
    occurred_at: datetime | None = None
    assigned_to: str | None = None
    source: str = "manual"
    geocode_source: str = "manual"
    notes: str = ""
    tags: list[str] = []


class OccurrencePatch(BaseModel):
    type: str | None = None
    description: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    territory: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    source: str | None = None
    geocode_source: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
