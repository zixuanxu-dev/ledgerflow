from __future__ import annotations

import hashlib
import json
from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AuditLog, Client, Document, DocumentRequirement, Reminder
from .lifecycle import sync_requirement_statuses


def _shift_month(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_month = divmod(month_index, 12)
    month = zero_month + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def seed_demo_data(db: Session) -> None:
    existing = db.scalar(select(func.count(Client.id))) or 0
    if existing:
        return

    clients = [
        Client(name="Northstar Design Co.", email="finance@northstar.example", industry="Design"),
        Client(name="Harbor & Finch", email="ops@harborfinch.example", industry="Consulting"),
        Client(
            name="Atlas Field Labs",
            email="accounts@atlasfield.example",
            industry="Engineering",
        ),
        Client(
            name="Morrow Coffee Group",
            email="admin@morrowcoffee.example",
            industry="Hospitality",
        ),
    ]
    db.add_all(clients)
    db.flush()

    today = date.today()
    current_period = today.strftime("%Y-%m")
    previous_period = _shift_month(today, -1).strftime("%Y-%m")
    requirements = [
        DocumentRequirement(
            client_id=clients[0].id,
            period=previous_period,
            document_type="invoice",
            due_date=today - timedelta(days=4),
        ),
        DocumentRequirement(
            client_id=clients[0].id,
            period=current_period,
            document_type="bank_statement",
            due_date=today + timedelta(days=5),
        ),
        DocumentRequirement(
            client_id=clients[1].id,
            period=previous_period,
            document_type="invoice",
            due_date=today - timedelta(days=2),
        ),
        DocumentRequirement(
            client_id=clients[1].id,
            period=current_period,
            document_type="expense_report",
            due_date=today + timedelta(days=8),
        ),
        DocumentRequirement(
            client_id=clients[2].id,
            period=current_period,
            document_type="contract",
            due_date=today + timedelta(days=12),
        ),
        DocumentRequirement(
            client_id=clients[2].id,
            period=previous_period,
            document_type="bank_statement",
            due_date=today - timedelta(days=6),
        ),
        DocumentRequirement(
            client_id=clients[3].id,
            period=current_period,
            document_type="invoice",
            due_date=today + timedelta(days=3),
        ),
        DocumentRequirement(
            client_id=clients[3].id,
            period=previous_period,
            document_type="tax_document",
            due_date=today - timedelta(days=8),
        ),
    ]
    db.add_all(requirements)
    db.flush()

    approved_text = "Invoice Number NS-1048 Total Amount $8,240.00 USD"
    review_text = "Bank Statement Account ****1842 Ending Balance $18,942.50 USD"
    documents = [
        Document(
            client_id=clients[0].id,
            requirement_id=requirements[0].id,
            original_filename=f"northstar_invoice_{previous_period}.pdf",
            stored_filename="demo-northstar-invoice.pdf",
            content_type="application/pdf",
            size_bytes=148_224,
            sha256=hashlib.sha256(approved_text.encode()).hexdigest(),
            document_type="invoice",
            period=previous_period,
            status="approved",
            confidence=0.94,
            extracted_text=approved_text,
            extracted_data=json.dumps(
                {
                    "document_type": "invoice",
                    "period": previous_period,
                    "fields": {
                        "document_number": "NS-1048",
                        "total_amount": "$8,240.00",
                        "currency": "USD",
                    },
                    "warnings": [],
                    "extraction_method": "deterministic",
                }
            ),
            review_notes="Verified against the source document.",
        ),
        Document(
            client_id=clients[2].id,
            requirement_id=requirements[5].id,
            original_filename=f"atlas_statement_{previous_period}.pdf",
            stored_filename="demo-atlas-statement.pdf",
            content_type="application/pdf",
            size_bytes=231_904,
            sha256=hashlib.sha256(review_text.encode()).hexdigest(),
            document_type="bank_statement",
            period=previous_period,
            status="needs_review",
            confidence=0.68,
            extracted_text=review_text,
            extracted_data=json.dumps(
                {
                    "document_type": "bank_statement",
                    "period": previous_period,
                    "fields": {
                        "account_last4": "1842",
                        "total_amount": "$18,942.50",
                        "currency": "USD",
                    },
                    "warnings": ["Statement period needs confirmation."],
                    "extraction_method": "deterministic",
                }
            ),
        ),
    ]
    db.add_all(documents)

    db.add(
        Reminder(
            requirement_id=requirements[2].id,
            recipient=clients[1].email,
            channel="email",
            message="Your monthly invoice pack is overdue. Please upload the missing document.",
            status="sent",
        )
    )
    db.add_all(
        [
            AuditLog(
                action="workspace.created",
                entity_type="workspace",
                entity_id=None,
                detail="LedgerFlow demo workspace initialized.",
            ),
            AuditLog(
                action="document.approved",
                entity_type="document",
                entity_id=1,
                detail="Northstar invoice was verified and matched automatically.",
            ),
            AuditLog(
                action="reminder.sent",
                entity_type="requirement",
                entity_id=requirements[2].id,
                detail="Overdue invoice reminder sent to Harbor & Finch.",
            ),
        ]
    )
    sync_requirement_statuses(db)
    db.commit()
