from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import get_db
from .models import AuditLog, Client, Document, DocumentRequirement, Reminder
from .schemas import (
    AuditOut,
    ClientCreate,
    ClientOut,
    DashboardOut,
    DocumentOut,
    ReminderOut,
    RequirementCreate,
    RequirementOut,
    ReviewRequest,
)
from .services.document_parser import DOCUMENT_TYPES, analyze_document, validate_extension
from .services.lifecycle import create_audit, sync_requirement_statuses

router = APIRouter(prefix="/api")


def _parse_json(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return {"warnings": ["Stored extraction data could not be decoded."]}


def _document_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        client_id=document.client_id,
        client_name=document.client.name,
        requirement_id=document.requirement_id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        document_type=document.document_type,
        period=document.period,
        status=document.status,
        confidence=document.confidence,
        extracted_data=_parse_json(document.extracted_data),
        review_notes=document.review_notes,
        created_at=document.created_at,
        reviewed_at=document.reviewed_at,
    )


def _requirement_out(requirement: DocumentRequirement) -> RequirementOut:
    latest = max(requirement.documents, key=lambda item: item.created_at, default=None)
    return RequirementOut(
        id=requirement.id,
        client_id=requirement.client_id,
        client_name=requirement.client.name,
        client_email=requirement.client.email,
        period=requirement.period,
        document_type=requirement.document_type,
        due_date=requirement.due_date,
        status=requirement.status,
        reminder_count=len(requirement.reminders),
        latest_document_id=latest.id if latest else None,
    )


def _get_requirement(db: Session, requirement_id: int) -> DocumentRequirement:
    requirement = db.scalar(
        select(DocumentRequirement)
        .where(DocumentRequirement.id == requirement_id)
        .options(
            selectinload(DocumentRequirement.client),
            selectinload(DocumentRequirement.documents),
            selectinload(DocumentRequirement.reminders),
        )
    )
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ledgerflow-api"}


@router.get("/meta/document-types")
def document_types() -> dict[str, str]:
    return DOCUMENT_TYPES


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    sync_requirement_statuses(db)
    db.commit()

    counts = {
        key: db.scalar(
            select(func.count(DocumentRequirement.id)).where(DocumentRequirement.status == key)
        )
        or 0
        for key in ("received", "missing", "late", "in_review")
    }
    requirement_total = sum(counts.values())
    completion_rate = (
        round(counts["received"] / requirement_total * 100) if requirement_total else 0
    )

    recent_documents = db.scalars(
        select(Document)
        .options(selectinload(Document.client))
        .order_by(Document.created_at.desc())
        .limit(5)
    ).all()
    recent_activity = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(6)
    ).all()

    return DashboardOut(
        clients=db.scalar(select(func.count(Client.id))) or 0,
        requirements=requirement_total,
        completion_rate=completion_rate,
        received=counts["received"],
        missing=counts["missing"],
        late=counts["late"],
        in_review=counts["in_review"],
        review_queue=db.scalar(
            select(func.count(Document.id)).where(Document.status.in_(["needs_review", "ready"]))
        )
        or 0,
        reminders_sent=db.scalar(select(func.count(Reminder.id))) or 0,
        period_label=date.today().strftime("%B %Y"),
        recent_documents=[_document_out(document) for document in recent_documents],
        recent_activity=[AuditOut.model_validate(item) for item in recent_activity],
    )


@router.get("/clients", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db)) -> list[ClientOut]:
    sync_requirement_statuses(db)
    clients = db.scalars(
        select(Client).options(selectinload(Client.requirements)).order_by(Client.name)
    ).all()
    result: list[ClientOut] = []
    for client in clients:
        requirement_count = len(client.requirements)
        received = sum(1 for requirement in client.requirements if requirement.status == "received")
        result.append(
            ClientOut(
                id=client.id,
                name=client.name,
                email=client.email,
                industry=client.industry,
                status=client.status,
                created_at=client.created_at,
                requirement_count=requirement_count,
                completion_rate=round(received / requirement_count * 100)
                if requirement_count
                else 0,
            )
        )
    return result


@router.post("/clients", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)) -> ClientOut:
    client = Client(
        name=payload.name.strip(),
        email=str(payload.email),
        industry=payload.industry.strip(),
    )
    db.add(client)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A client with this email already exists"
        ) from exc
    create_audit(db, "client.created", "client", client.id, f"Added client {client.name}.")
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.get("/requirements", response_model=list[RequirementOut])
def list_requirements(db: Session = Depends(get_db)) -> list[RequirementOut]:
    sync_requirement_statuses(db)
    db.commit()
    requirements = db.scalars(
        select(DocumentRequirement)
        .options(
            selectinload(DocumentRequirement.client),
            selectinload(DocumentRequirement.documents),
            selectinload(DocumentRequirement.reminders),
        )
        .order_by(DocumentRequirement.due_date, DocumentRequirement.id)
    ).all()
    return [_requirement_out(requirement) for requirement in requirements]


@router.post(
    "/requirements", response_model=RequirementOut, status_code=status.HTTP_201_CREATED
)
def create_requirement(
    payload: RequirementCreate, db: Session = Depends(get_db)
) -> RequirementOut:
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if payload.document_type not in DOCUMENT_TYPES or payload.document_type == "unknown":
        raise HTTPException(status_code=422, detail="Unsupported document type")

    duplicate = db.scalar(
        select(DocumentRequirement).where(
            DocumentRequirement.client_id == payload.client_id,
            DocumentRequirement.period == payload.period,
            DocumentRequirement.document_type == payload.document_type,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="This requirement already exists")

    requirement = DocumentRequirement(
        client_id=payload.client_id,
        period=payload.period,
        document_type=payload.document_type,
        due_date=payload.due_date,
    )
    db.add(requirement)
    db.flush()
    create_audit(
        db,
        "requirement.created",
        "requirement",
        requirement.id,
        f"Requested {DOCUMENT_TYPES[payload.document_type]} for {client.name}, {payload.period}.",
    )
    sync_requirement_statuses(db)
    db.commit()
    return _requirement_out(_get_requirement(db, requirement.id))


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    documents = db.scalars(
        select(Document)
        .options(selectinload(Document.client))
        .order_by(Document.created_at.desc(), Document.id.desc())
    ).all()
    return [_document_out(document) for document in documents]


@router.post("/documents/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    client_id: int = Form(...),
    requirement_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentOut:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    original_filename = Path(file.filename or "").name
    if not original_filename:
        raise HTTPException(status_code=422, detail="A filename is required")
    try:
        extension = validate_extension(original_filename)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB upload limit")
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty")

    digest = hashlib.sha256(content).hexdigest()
    duplicate = db.scalar(
        select(Document).where(Document.client_id == client_id, Document.sha256 == digest)
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate document detected (document #{duplicate.id})",
        )

    try:
        analysis = analyze_document(original_filename, content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Document parsing failed: {exc}") from exc

    requirement: DocumentRequirement | None = None
    if requirement_id is not None:
        requirement = _get_requirement(db, requirement_id)
        if requirement.client_id != client_id:
            raise HTTPException(status_code=409, detail="Requirement belongs to a different client")
    elif analysis.period and analysis.document_type != "unknown":
        requirement = db.scalar(
            select(DocumentRequirement).where(
                DocumentRequirement.client_id == client_id,
                DocumentRequirement.period == analysis.period,
                DocumentRequirement.document_type == analysis.document_type,
            )
        )

    parsed_data = analysis.data.copy()
    document_type = analysis.document_type
    period = analysis.period
    confidence = analysis.confidence
    if requirement:
        if document_type == "unknown":
            document_type = requirement.document_type
            confidence = min(0.98, confidence + 0.25)
        if period is None:
            period = requirement.period
            confidence = min(0.98, confidence + 0.2)
        parsed_data["document_type"] = document_type
        parsed_data["period"] = period
        parsed_data["matched_requirement_id"] = requirement.id

    stored_filename = f"{uuid4().hex}{extension}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = settings.upload_dir / stored_filename
    stored_path.write_bytes(content)

    document = Document(
        client_id=client_id,
        requirement_id=requirement.id if requirement else None,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=digest,
        document_type=document_type,
        period=period,
        status="ready" if confidence >= 0.8 else "needs_review",
        confidence=confidence,
        extracted_text=analysis.text,
        extracted_data=json.dumps(parsed_data, ensure_ascii=False),
    )
    db.add(document)
    try:
        db.flush()
        create_audit(
            db,
            "document.uploaded",
            "document",
            document.id,
            f"Uploaded {original_filename} for {client.name}; confidence {confidence:.0%}.",
        )
        sync_requirement_statuses(db)
        db.commit()
    except Exception:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise

    saved = db.scalar(
        select(Document)
        .where(Document.id == document.id)
        .options(selectinload(Document.client))
    )
    assert saved is not None
    return _document_out(saved)


@router.post("/documents/{document_id}/review", response_model=DocumentOut)
def review_document(
    document_id: int, payload: ReviewRequest, db: Session = Depends(get_db)
) -> DocumentOut:
    document = db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.client))
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    document.status = "approved" if payload.decision == "approve" else "rejected"
    document.review_notes = payload.notes.strip()
    document.reviewed_at = datetime.now(UTC)
    create_audit(
        db,
        f"document.{document.status}",
        "document",
        document.id,
        f"{document.original_filename} was {document.status} by a reviewer.",
    )
    sync_requirement_statuses(db)
    db.commit()
    db.refresh(document)
    return _document_out(document)


@router.post("/requirements/{requirement_id}/remind", response_model=ReminderOut)
def send_reminder(requirement_id: int, db: Session = Depends(get_db)) -> ReminderOut:
    sync_requirement_statuses(db)
    requirement = _get_requirement(db, requirement_id)
    if requirement.status == "received":
        raise HTTPException(status_code=409, detail="This requirement is already complete")

    # Repeated clicks and client retries should not send another reminder within 24 hours.
    latest_reminder = max(requirement.reminders, key=lambda item: item.sent_at, default=None)
    if latest_reminder:
        sent_at = latest_reminder.sent_at
        if sent_at.tzinfo is None:  # SQLite stores timezone-aware values without an offset.
            sent_at = sent_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - sent_at < timedelta(hours=24):
            return ReminderOut.model_validate(latest_reminder)

    label = DOCUMENT_TYPES.get(requirement.document_type, requirement.document_type)
    message = (
        f"Hello {requirement.client.name}, your {label.lower()} for {requirement.period} "
        f"is still {requirement.status.replace('_', ' ')}. Please upload it by "
        f"{requirement.due_date.isoformat()}."
    )
    reminder = Reminder(
        requirement_id=requirement.id,
        recipient=requirement.client.email,
        channel="email",
        message=message,
        status="sent",
    )
    db.add(reminder)
    db.flush()
    create_audit(
        db,
        "reminder.sent",
        "requirement",
        requirement.id,
        f"Reminder sent to {requirement.client.name} for {label}, {requirement.period}.",
    )
    db.commit()
    db.refresh(reminder)
    return ReminderOut.model_validate(reminder)


@router.get("/audit", response_model=list[AuditOut])
def list_audit(db: Session = Depends(get_db)) -> list[AuditOut]:
    entries = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [AuditOut.model_validate(entry) for entry in entries]


@router.get("/export/requirements.csv")
def export_requirements(db: Session = Depends(get_db)) -> StreamingResponse:
    sync_requirement_statuses(db)
    requirements = db.scalars(
        select(DocumentRequirement)
        .options(
            selectinload(DocumentRequirement.client),
            selectinload(DocumentRequirement.reminders),
        )
        .order_by(DocumentRequirement.due_date)
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["client", "email", "period", "document_type", "due_date", "status", "reminders"]
    )
    for requirement in requirements:
        writer.writerow(
            [
                requirement.client.name,
                requirement.client.email,
                requirement.period,
                requirement.document_type,
                requirement.due_date.isoformat(),
                requirement.status,
                len(requirement.reminders),
            ]
        )

    response = StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = 'attachment; filename="ledgerflow-requirements.csv"'
    return response
