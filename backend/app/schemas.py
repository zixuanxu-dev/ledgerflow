from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    industry: str = Field(default="Professional services", max_length=120)


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    industry: str
    status: str
    created_at: datetime
    requirement_count: int = 0
    completion_rate: int = 0


class RequirementCreate(BaseModel):
    client_id: int
    period: str
    document_type: str = Field(min_length=2, max_length=80)
    due_date: date

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        if len(value) != 7 or value[4] != "-":
            raise ValueError("Period must use YYYY-MM format")
        year, month = value.split("-", maxsplit=1)
        if not year.isdigit() or not month.isdigit() or not 1 <= int(month) <= 12:
            raise ValueError("Period must use YYYY-MM format")
        return value


class RequirementOut(BaseModel):
    id: int
    client_id: int
    client_name: str
    client_email: str
    period: str
    document_type: str
    due_date: date
    status: str
    reminder_count: int
    latest_document_id: int | None = None


class DocumentOut(BaseModel):
    id: int
    client_id: int
    client_name: str
    requirement_id: int | None
    original_filename: str
    content_type: str
    size_bytes: int
    document_type: str
    period: str | None
    status: str
    confidence: float
    extracted_data: dict[str, Any]
    review_notes: str
    created_at: datetime
    reviewed_at: datetime | None


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    notes: str = Field(default="", max_length=1000)


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requirement_id: int
    recipient: str
    channel: str
    message: str
    status: str
    sent_at: datetime


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: int | None
    actor: str
    detail: str
    created_at: datetime


class DashboardOut(BaseModel):
    clients: int
    requirements: int
    completion_rate: int
    received: int
    missing: int
    late: int
    in_review: int
    review_queue: int
    reminders_sent: int
    period_label: str
    recent_documents: list[DocumentOut]
    recent_activity: list[AuditOut]
