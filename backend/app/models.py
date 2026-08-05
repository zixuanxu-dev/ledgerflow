from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    industry: Mapped[str] = mapped_column(String(120), default="Professional services")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    requirements: Mapped[list[DocumentRequirement]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(back_populates="client")


class DocumentRequirement(Base):
    __tablename__ = "document_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(32), default="missing", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    client: Mapped[Client] = relationship(back_populates="requirements")
    documents: Mapped[list[Document]] = relationship(back_populates="requirement")
    reminders: Mapped[list[Reminder]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_requirements.id"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    document_type: Mapped[str] = mapped_column(String(80), default="unknown", index=True)
    period: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="needs_review", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extracted_data: Mapped[str] = mapped_column(Text, default="{}")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[Client] = relationship(back_populates="documents")
    requirement: Mapped[DocumentRequirement | None] = relationship(back_populates="documents")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("document_requirements.id"), index=True
    )
    recipient: Mapped[str] = mapped_column(String(255))
    channel: Mapped[str] = mapped_column(String(32), default="email")
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    requirement: Mapped[DocumentRequirement] = relationship(back_populates="reminders")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor: Mapped[str] = mapped_column(String(120), default="demo.user@ledgerflow.dev")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
