from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import AuditLog, DocumentRequirement


def create_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None,
    detail: str,
    actor: str = "demo.user@ledgerflow.dev",
) -> AuditLog:
    audit = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        actor=actor,
    )
    db.add(audit)
    return audit


def sync_requirement_statuses(db: Session) -> None:
    requirements = db.scalars(
        select(DocumentRequirement).options(selectinload(DocumentRequirement.documents))
    ).all()
    today = date.today()
    changed = False
    for requirement in requirements:
        statuses = {document.status for document in requirement.documents}
        if "approved" in statuses:
            next_status = "received"
        elif statuses & {"needs_review", "ready"}:
            next_status = "in_review"
        elif requirement.due_date < today:
            next_status = "late"
        else:
            next_status = "missing"

        if requirement.status != next_status:
            requirement.status = next_status
            changed = True
    if changed:
        db.flush()
